"""
Mitglieder Synchronisation V2
- Google Sheets → Supabase
- Supabase → HubSpot
- Supabase → MeinVerein XLSX Export

Änderungen V2:
- Instagramname Feld
- Zahlungsart: lastschrift / rechnung
- MeinVerein Export mit individuellen Feldern
"""

import streamlit as st
import requests
from datetime import datetime
import json
import csv
import io

from utils.supabase_client import get_supabase


def get_mitglieder_stats():
    """Holt Statistiken für das Dashboard."""
    supabase = get_supabase()
    
    stats = {
        "neu": 0,
        "pending": 0,
        "genehmigt": 0,
        "abgelehnt": 0,
        "sync_pending": 0
    }
    
    try:
        # Status-Counts
        for status in ["neu", "pending", "genehmigt", "abgelehnt"]:
            response = supabase.table("mitglieder").select("id", count="exact").eq("status", status).execute()
            stats[status] = response.count if response.count else 0
        
        # Sync ausstehend (genehmigt aber nicht vollständig synchronisiert)
        response = supabase.table("mitglieder").select("id", count="exact").eq("status", "genehmigt").or_("sync_hubspot.eq.false,sync_meinverein.eq.false").execute()
        stats["sync_pending"] = response.count if response.count else 0
        
    except Exception as e:
        st.error(f"Fehler beim Laden der Statistiken: {e}")
    
    return stats


def sync_from_google_sheet():
    """
    Importiert neue Einträge aus dem verknüpften Google Sheet.
    Returns: {"success": bool, "imported": int, "error": str}
    """
    try:
        # Sheet-ID aus Config laden
        sheet_id = st.secrets.get("google_sheet_mitglieder_id")
        
        if not sheet_id:
            return {"success": False, "imported": 0, "error": "Google Sheet ID nicht konfiguriert. Bitte in Secrets 'google_sheet_mitglieder_id' hinzufügen."}
        
        # Google Sheets API aufrufen
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        
        # Token aus Secrets holen
        token_data = st.secrets.get("google_oauth_token", {})
        if not token_data:
            return {"success": False, "imported": 0, "error": "Google OAuth Token nicht konfiguriert."}
        
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret")
        )
        
        # Sheet-Daten lesen (Formularantworten Tab)
        sheets_service = build('sheets', 'v4', credentials=creds)
        
        # Erst alle Tabs holen um den richtigen zu finden
        sheet_meta = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
        sheets = sheet_meta.get('sheets', [])
        
        # Tab mit "Formular" oder "Form" im Namen finden, sonst ersten Tab
        tab_name = None
        for s in sheets:
            title = s['properties']['title']
            if 'formular' in title.lower() or 'form' in title.lower() or 'antwort' in title.lower():
                tab_name = title
                break
        
        if not tab_name and sheets:
            tab_name = sheets[0]['properties']['title']
        
        # Range mit Tab-Name
        range_str = f"'{tab_name}'!A:Z" if tab_name else "A:Z"
        
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_str
        ).execute()
        
        rows = result.get('values', [])
        
        if len(rows) <= 1:
            return {"success": True, "imported": 0, "error": None}
        
        # Header-Zeile
        headers = rows[0]
        
        # Mapping der Spalten (anpassen je nach Google Form V2)
        column_map = {
            "Anrede": "anrede",
            "Vorname": "vorname",
            "Nachname": "nachname",
            "E-Mail": "email",
            "Telefon": "telefon",
            "Instagram": "instagramname",
            "Straße": "strasse",
            "Postleitzahl": "plz",
            "Ort": "ort",
            "IBAN": "iban",
            "Kontoinhaber": "kontoinhaber",
            "Mitgliedschaft als": "mitgliedsart_raw",
            "Zahlungsweise": "zahlungsweise_raw",
            "Zahlungsart": "zahlungsart_raw",
            "Firmenname": "firmenname",
            "Zeitstempel": "timestamp"
        }
        
        # Index der Spalten finden
        header_indices = {}
        for i, h in enumerate(headers):
            for form_name, db_name in column_map.items():
                if form_name.lower() in h.lower():
                    header_indices[db_name] = i
                    break
        
        supabase = get_supabase()
        imported = 0
        
        # Zeilen verarbeiten (ohne Header)
        for row in rows[1:]:
            try:
                # E-Mail extrahieren
                email_idx = header_indices.get("email", 3)
                if email_idx >= len(row):
                    continue
                    
                email = row[email_idx].strip().lower() if email_idx < len(row) else None
                
                if not email:
                    continue
                
                # Prüfen ob bereits existiert
                existing = supabase.table("mitglieder").select("id").eq("email", email).execute()
                if existing.data:
                    continue  # Bereits vorhanden
                
                # Daten extrahieren
                def get_val(key, default=""):
                    idx = header_indices.get(key)
                    if idx is not None and idx < len(row):
                        return row[idx].strip() if row[idx] else default
                    return default
                
                # Mitgliedsart parsen
                mitgliedsart_raw = get_val("mitgliedsart_raw", "")
                mitgliedsart = "juristisch" if "juristisch" in mitgliedsart_raw.lower() or "gmbh" in mitgliedsart_raw.lower() else "natuerlich"
                
                # Zahlungsweise parsen
                zahlungsweise_raw = get_val("zahlungsweise_raw", "")
                zahlungsweise = "jaehrlich" if "jährlich" in zahlungsweise_raw.lower() or "jahr" in zahlungsweise_raw.lower() else "monatlich"
                
                # Zahlungsart parsen (Lastschrift oder Rechnung)
                zahlungsart_raw = get_val("zahlungsart_raw", "")
                zahlungsart = "rechnung" if "rechnung" in zahlungsart_raw.lower() else "lastschrift"
                
                # Beitrag berechnen
                beitrag = 25.00
                if mitgliedsart == "juristisch":
                    zahlungsweise = "jaehrlich"  # Juristische Personen nur jährlich
                
                # IBAN und Kontoinhaber nur wenn Lastschrift
                iban_val = get_val("iban").replace(" ", "").upper() if zahlungsart == "lastschrift" else ""
                kontoinhaber_val = get_val("kontoinhaber") if zahlungsart == "lastschrift" else ""
                
                # Neues Mitglied anlegen
                neues_mitglied = {
                    "anrede": get_val("anrede", "Herr"),
                    "vorname": get_val("vorname"),
                    "nachname": get_val("nachname"),
                    "email": email,
                    "telefon": get_val("telefon"),
                    "instagramname": get_val("instagramname"),
                    "firmenname": get_val("firmenname"),
                    "strasse": get_val("strasse"),
                    "plz": get_val("plz"),
                    "ort": get_val("ort"),
                    "iban": iban_val,
                    "kontoinhaber": kontoinhaber_val,
                    "mitgliedsart": mitgliedsart,
                    "zahlungsweise": zahlungsweise,
                    "zahlungsart": zahlungsart,
                    "beitrag_monatlich": beitrag,
                    "status": "neu",
                    "quelle": "google_forms"
                }
                
                supabase.table("mitglieder").insert(neues_mitglied).execute()
                imported += 1
                
            except Exception as e:
                continue  # Zeile überspringen bei Fehler
        
        return {"success": True, "imported": imported, "error": None}
        
    except Exception as e:
        return {"success": False, "imported": 0, "error": str(e)}


def sync_to_hubspot():
    """
    Synchronisiert genehmigte Mitglieder zu HubSpot.
    Returns: {"success": bool, "synced": int, "error": str}
    """
    try:
        api_token = st.secrets.get("hubspot", {}).get("api_token")
        
        if not api_token:
            return {"success": False, "synced": 0, "error": "HubSpot API Token nicht konfiguriert."}
        
        supabase = get_supabase()
        
        # Nicht synchronisierte, genehmigte Mitglieder laden
        response = supabase.table("mitglieder").select("*").eq("status", "genehmigt").eq("sync_hubspot", False).execute()
        
        mitglieder = response.data if response.data else []
        
        if not mitglieder:
            return {"success": True, "synced": 0, "error": None}
        
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        synced = 0
        
        for m in mitglieder:
            try:
                # Anrede konvertieren für HubSpot
                anrede = m.get("anrede", "Herr")
                if anrede == "Herr":
                    salutation = "Lieber"
                elif anrede == "Frau":
                    salutation = "Liebe"
                else:
                    salutation = "Hallo"
                
                # Kontakt-Daten für HubSpot
                contact_data = {
                    "properties": {
                        "email": m.get("email", ""),
                        "firstname": m.get("vorname", ""),
                        "lastname": m.get("nachname", ""),
                        "phone": m.get("telefon", ""),
                        "address": m.get("strasse", ""),
                        "zip": m.get("plz", ""),
                        "city": m.get("ort", ""),
                        "salutation": salutation
                    }
                }
                
                # Prüfen ob Kontakt existiert
                search_url = "https://api.hubapi.com/crm/v3/objects/contacts/search"
                search_body = {
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": m.get("email", "")
                        }]
                    }]
                }
                
                search_response = requests.post(search_url, headers=headers, json=search_body)
                search_result = search_response.json()
                
                if search_result.get("total", 0) > 0:
                    # Kontakt existiert - Update
                    contact_id = search_result["results"][0]["id"]
                    update_url = f"https://api.hubapi.com/crm/v3/objects/contacts/{contact_id}"
                    requests.patch(update_url, headers=headers, json=contact_data)
                    hubspot_id = contact_id
                else:
                    # Neuen Kontakt erstellen
                    create_url = "https://api.hubapi.com/crm/v3/objects/contacts"
                    create_response = requests.post(create_url, headers=headers, json=contact_data)
                    
                    if create_response.status_code in [200, 201]:
                        hubspot_id = create_response.json().get("id")
                    else:
                        continue  # Fehler, nächstes Mitglied
                
                # In Supabase als synchronisiert markieren
                supabase.table("mitglieder").update({
                    "sync_hubspot": True,
                    "hubspot_contact_id": hubspot_id,
                    "sync_hubspot_datum": datetime.now().isoformat()
                }).eq("id", m["id"]).execute()
                
                synced += 1
                
            except Exception as e:
                continue  # Nächstes Mitglied bei Fehler
        
        return {"success": True, "synced": synced, "error": None}
        
    except Exception as e:
        return {"success": False, "synced": 0, "error": str(e)}


def export_meinverein_csv():
    """
    Exportiert nicht synchronisierte Mitglieder als XLSX für MeinVerein.
    Returns: {"success": bool, "xlsx_data": bytes, "member_ids": list, "error": str}
    """
    try:
        import pandas as pd
        from io import BytesIO
        
        supabase = get_supabase()
        
        # Nicht exportierte, genehmigte Mitglieder laden
        response = supabase.table("mitglieder").select("*").eq("status", "genehmigt").eq("sync_meinverein", False).execute()
        
        mitglieder = response.data if response.data else []
        
        if not mitglieder:
            return {"success": False, "xlsx_data": None, "member_ids": [], "error": "Keine Mitglieder zum Exportieren."}
        
        # MeinVerein Spalten (OHNE individuelle Felder - MeinVerein akzeptiert sie nicht beim Import)
        columns = [
            "Mitgliedsnr.", "Anrede", "Titel", "Vorname", "Nachname",
            "Telefon", "Mobil", "E-Mail", "Strasse & Hausnr.", "PLZ", "Ort", "Land",
            "Geburtstag", "Mitglied seit", "Ebene 1", "Ebene 2", "Ebene 3",
            "Ehrenmitglied", "Status", "Mitglied bis",
            "Beitrag (Bezeichnung)", "Beitrag (Typ)", "Beitrag (Betrag)", 
            "Beitrag (Zeitraum)", "Beitrag (Fälligkeit)", "Notizen",
            "Geschlecht", "Familienstand", "Zahlungsart", "IBAN", "Kontoinhaber",
            "SEPA-Mandat erteilt", "Mandatsreferenz", "Art des Mandats",
            "Art der nächsten Lastschrift", "Mandat erteilt am", "Letzte Verwendung"
        ]
        
        rows = []
        member_ids = []
        
        for m in mitglieder:
            # Mandatsdatum formatieren (als Datum-Objekt für Excel)
            mandatsdatum_obj = None
            mandatsdatum = m.get("mandatsdatum", "")
            if mandatsdatum:
                try:
                    if "T" in mandatsdatum:
                        mandatsdatum_obj = datetime.fromisoformat(mandatsdatum.replace("Z", "+00:00")).date()
                    else:
                        mandatsdatum_obj = datetime.strptime(mandatsdatum, "%Y-%m-%d").date()
                except:
                    mandatsdatum_obj = datetime.now().date()
            else:
                mandatsdatum_obj = datetime.now().date()
            
            # Genehmigungsdatum (Mitglied seit)
            mitglied_seit_obj = None
            genehmigt_am = m.get("genehmigt_am", "")
            if genehmigt_am:
                try:
                    mitglied_seit_obj = datetime.fromisoformat(genehmigt_am.replace("Z", "+00:00")).date()
                except:
                    mitglied_seit_obj = datetime.now().date()
            else:
                mitglied_seit_obj = datetime.now().date()
            
            # Geschlecht aus Anrede
            anrede = m.get("anrede", "Herr")
            geschlecht = "männlich" if anrede == "Herr" else "weiblich" if anrede == "Frau" else "divers"
            
            # Beitrag
            beitrag = m.get("beitrag_monatlich", 25.00)
            zahlungsweise = m.get("zahlungsweise", "monatlich")
            mitgliedsart = m.get("mitgliedsart", "natuerlich")
            zahlungsart = m.get("zahlungsart", "lastschrift")
            
            if zahlungsweise == "jaehrlich":
                beitrag_betrag = beitrag * 12
                beitrag_zeitraum = "jährlich"
            else:
                beitrag_betrag = beitrag
                beitrag_zeitraum = "monatlich"
            
            # Beitragstyp für MeinVerein - leer lassen, muss manuell gesetzt werden
            beitrag_typ = ""
            
            # Zahlungsart für MeinVerein (Lastschrift oder per Rechnung)
            zahlungsart_mv = "Lastschrift" if zahlungsart == "lastschrift" else "per Rechnung"
            
            # SEPA nur wenn Lastschrift und IBAN vorhanden
            sepa_erteilt = "ja" if zahlungsart == "lastschrift" and m.get("iban") else "nein"
            
            row = {
                "Mitgliedsnr.": "",  # Leer lassen - MeinVerein vergibt automatisch
                "Anrede": anrede,
                "Titel": "",
                "Vorname": m.get("vorname", ""),
                "Nachname": m.get("nachname", ""),
                "Telefon": "",
                "Mobil": m.get("telefon", ""),
                "E-Mail": m.get("email", ""),
                "Strasse & Hausnr.": m.get("strasse", ""),
                "PLZ": m.get("plz", ""),
                "Ort": m.get("ort", ""),
                "Land": "Deutschland",
                "Geburtstag": "",
                "Mitglied seit": mitglied_seit_obj,
                "Ebene 1": "",
                "Ebene 2": "",
                "Ebene 3": "",
                "Ehrenmitglied": "Nein",
                "Status": "Aktiv",
                "Mitglied bis": "",
                "Beitrag (Bezeichnung)": "",
                "Beitrag (Typ)": beitrag_typ,
                "Beitrag (Betrag)": "",
                "Beitrag (Zeitraum)": "",
                "Beitrag (Fälligkeit)": "",
                "Notizen": m.get("notizen", ""),
                "Geschlecht": geschlecht,
                "Familienstand": "",
                "Zahlungsart": zahlungsart_mv,
                "IBAN": m.get("iban", "").replace(" ", "") if m.get("iban") else "",
                "Kontoinhaber": m.get("kontoinhaber", "") if m.get("kontoinhaber") else "",
                "SEPA-Mandat erteilt": sepa_erteilt,
                "Mandatsreferenz": m.get("mandatsreferenz", "") if sepa_erteilt == "ja" else "",
                "Art des Mandats": "Einmalig" if sepa_erteilt == "ja" else "",
                "Art der nächsten Lastschrift": "Erste Lastschrift" if sepa_erteilt == "ja" else "",
                "Mandat erteilt am": mandatsdatum_obj if sepa_erteilt == "ja" else "",
                "Letzte Verwendung": ""
            }
            
            rows.append(row)
            member_ids.append(m["id"])
        
        # DataFrame erstellen
        df = pd.DataFrame(rows, columns=columns)
        
        # XLSX erstellen
        output = BytesIO()
        df.to_excel(output, index=False, engine='openpyxl')
        xlsx_data = output.getvalue()
        output.close()
        
        return {
            "success": True, 
            "xlsx_data": xlsx_data, 
            "member_ids": member_ids,
            "error": None
        }
        
    except Exception as e:
        return {"success": False, "xlsx_data": None, "member_ids": [], "error": str(e)}


def mark_meinverein_exported(member_ids):
    """Markiert Mitglieder als zu MeinVerein exportiert."""
    try:
        supabase = get_supabase()
        
        for member_id in member_ids:
            supabase.table("mitglieder").update({
                "sync_meinverein": True,
                "sync_meinverein_datum": datetime.now().isoformat()
            }).eq("id", member_id).execute()
        
        return {"success": True, "error": None}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def import_wiso_excel(file_data):
    """
    Importiert Bestandsmitglieder aus Wiso-Excel-Export.
    Returns: {"success": bool, "imported": int, "error": str}
    """
    try:
        import pandas as pd
        
        # Excel lesen
        df = pd.read_excel(file_data)
        
        # Spalten-Mapping (flexibel für verschiedene Spaltennamen)
        column_variants = {
            "email": ["E-Mail", "Email", "e-mail", "EMail", "E-Mail-Adresse", "email"],
            "vorname": ["Vorname", "First Name", "vorname"],
            "nachname": ["Nachname", "Name", "Last Name", "nachname"],
            "anrede": ["Anrede", "Salutation", "anrede"],
            "strasse": ["Straße", "Strasse", "Adresse", "Street", "strasse", "Strasse & Hausnr."],
            "plz": ["PLZ", "Postleitzahl", "ZIP", "plz"],
            "ort": ["Ort", "Stadt", "City", "ort"],
            "telefon": ["Telefon", "Phone", "Mobil", "telefon"],
            "iban": ["IBAN", "iban"],
            "kontoinhaber": ["Kontoinhaber", "Account Holder", "kontoinhaber"],
        }
        
        # Tatsächliche Spaltennamen finden
        column_map = {}
        for db_col, variants in column_variants.items():
            for variant in variants:
                if variant in df.columns:
                    column_map[db_col] = variant
                    break
        
        if "email" not in column_map:
            return {"success": False, "imported": 0, "error": "E-Mail-Spalte nicht gefunden."}
        
        supabase = get_supabase()
        imported = 0
        import_counter = 1
        
        for _, row in df.iterrows():
            try:
                email = str(row[column_map["email"]]).strip().lower()
                
                if not email or email == "nan" or "@" not in email:
                    continue
                
                # Prüfen ob bereits existiert
                existing = supabase.table("mitglieder").select("id").eq("email", email).execute()
                if existing.data:
                    continue
                
                def get_val(key, default=""):
                    if key in column_map and column_map[key] in row:
                        val = row[column_map[key]]
                        return str(val).strip() if pd.notna(val) else default
                    return default
                
                # Mandatsreferenz für Import generieren
                mandatsreferenz = f"UV-IMPORT-{import_counter:04d}"
                import_counter += 1
                
                neues_mitglied = {
                    "anrede": get_val("anrede", "Herr"),
                    "vorname": get_val("vorname"),
                    "nachname": get_val("nachname"),
                    "email": email,
                    "telefon": get_val("telefon"),
                    "strasse": get_val("strasse"),
                    "plz": get_val("plz"),
                    "ort": get_val("ort"),
                    "iban": get_val("iban").replace(" ", "").upper(),
                    "kontoinhaber": get_val("kontoinhaber"),
                    "mitgliedsart": "natuerlich",
                    "zahlungsweise": "monatlich",
                    "zahlungsart": "lastschrift",
                    "beitrag_monatlich": 25.00,
                    "status": "genehmigt",  # Bestandsmitglieder sind bereits aktiv
                    "quelle": "wiso_import",
                    "mandatsreferenz": mandatsreferenz,
                    "mandatsdatum": datetime.now().strftime("%Y-%m-%d"),
                    "genehmigt_am": datetime.now().isoformat()
                }
                
                supabase.table("mitglieder").insert(neues_mitglied).execute()
                imported += 1
                
            except Exception as e:
                continue
        
        return {"success": True, "imported": imported, "error": None}
        
    except Exception as e:
        return {"success": False, "imported": 0, "error": str(e)}


def generate_mandatsreferenz():
    """Generiert eine eindeutige Mandatsreferenz."""
    import secrets
    year = datetime.now().year
    random_part = secrets.token_hex(4).upper()
    return f"UV-{year}-{random_part}"


def approve_mitglied(mitglied_id):
    """
    Genehmigt ein Mitglied und generiert Mandatsreferenz.
    Returns: {"success": bool, "error": str}
    """
    try:
        supabase = get_supabase()
        
        # Mitglied laden
        response = supabase.table("mitglieder").select("*").eq("id", mitglied_id).execute()
        
        if not response.data:
            return {"success": False, "error": "Mitglied nicht gefunden."}
        
        mitglied = response.data[0]
        
        # Mandatsreferenz generieren (nur wenn Lastschrift und noch keine vorhanden)
        mandatsreferenz = mitglied.get("mandatsreferenz")
        mandatsdatum = mitglied.get("mandatsdatum")
        
        if mitglied.get("zahlungsart", "lastschrift") == "lastschrift" and not mandatsreferenz:
            mandatsreferenz = generate_mandatsreferenz()
            mandatsdatum = datetime.now().strftime("%Y-%m-%d")
        
        # Update
        update_data = {
            "status": "genehmigt",
            "genehmigt_am": datetime.now().isoformat()
        }
        
        if mandatsreferenz:
            update_data["mandatsreferenz"] = mandatsreferenz
        if mandatsdatum:
            update_data["mandatsdatum"] = mandatsdatum
        
        supabase.table("mitglieder").update(update_data).eq("id", mitglied_id).execute()
        
        return {"success": True, "error": None}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def reject_mitglied(mitglied_id, grund=""):
    """
    Lehnt ein Mitglied ab.
    Returns: {"success": bool, "error": str}
    """
    try:
        supabase = get_supabase()
        
        supabase.table("mitglieder").update({
            "status": "abgelehnt",
            "notizen": grund
        }).eq("id", mitglied_id).execute()
        
        return {"success": True, "error": None}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def set_pending(mitglied_id):
    """Setzt Mitglied auf 'in Prüfung'."""
    try:
        supabase = get_supabase()
        
        supabase.table("mitglieder").update({
            "status": "pending"
        }).eq("id", mitglied_id).execute()
        
        return {"success": True, "error": None}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_mitglieder_by_status(status):
    """Lädt Mitglieder nach Status."""
    try:
        supabase = get_supabase()
        
        response = supabase.table("mitglieder").select("*").eq("status", status).order("created_at", desc=True).execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
        return []


def get_all_mitglieder():
    """Lädt alle Mitglieder."""
    try:
        supabase = get_supabase()
        
        response = supabase.table("mitglieder").select("*").order("created_at", desc=True).execute()
        
        return response.data if response.data else []
        
    except Exception as e:
        st.error(f"Fehler beim Laden: {e}")
        return []


def create_mitglied_manual(data):
    """
    Legt ein Mitglied manuell an.
    Returns: {"success": bool, "error": str}
    """
    try:
        supabase = get_supabase()
        
        # Pflichtfelder prüfen
        if not data.get("email"):
            return {"success": False, "error": "E-Mail ist erforderlich."}
        
        # Prüfen ob bereits existiert
        existing = supabase.table("mitglieder").select("id").eq("email", data["email"].lower()).execute()
        if existing.data:
            return {"success": False, "error": "Diese E-Mail-Adresse existiert bereits."}
        
        # Mandatsreferenz generieren falls genehmigt und Lastschrift
        if data.get("status") == "genehmigt" and data.get("zahlungsart", "lastschrift") == "lastschrift":
            data["mandatsreferenz"] = generate_mandatsreferenz()
            data["mandatsdatum"] = datetime.now().strftime("%Y-%m-%d")
            data["genehmigt_am"] = datetime.now().isoformat()
        
        # E-Mail normalisieren
        data["email"] = data["email"].lower().strip()
        
        supabase.table("mitglieder").insert(data).execute()
        
        return {"success": True, "error": None}
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_sync_history():
    """Gibt die letzten Sync-Ereignisse zurück."""
    try:
        supabase = get_supabase()
        
        # Letzte HubSpot-Syncs
        hubspot_syncs = supabase.table("mitglieder").select(
            "vorname", "nachname", "sync_hubspot_datum"
        ).eq("sync_hubspot", True).order("sync_hubspot_datum", desc=True).limit(5).execute()
        
        # Letzte MeinVerein-Exports
        meinverein_exports = supabase.table("mitglieder").select(
            "vorname", "nachname", "sync_meinverein_datum"
        ).eq("sync_meinverein", True).order("sync_meinverein_datum", desc=True).limit(5).execute()
        
        return {
            "hubspot": hubspot_syncs.data if hubspot_syncs.data else [],
            "meinverein": meinverein_exports.data if meinverein_exports.data else []
        }
        
    except Exception as e:
        return {"hubspot": [], "meinverein": []}


def get_pending_sync_counts():
    """Gibt die Anzahl ausstehender Syncs zurück."""
    try:
        supabase = get_supabase()
        
        # HubSpot ausstehend
        hubspot = supabase.table("mitglieder").select("id", count="exact").eq("status", "genehmigt").eq("sync_hubspot", False).execute()
        
        # MeinVerein ausstehend
        meinverein = supabase.table("mitglieder").select("id", count="exact").eq("status", "genehmigt").eq("sync_meinverein", False).execute()
        
        return {
            "hubspot": hubspot.count if hubspot.count else 0,
            "meinverein": meinverein.count if meinverein.count else 0
        }
        
    except Exception as e:
        return {"hubspot": 0, "meinverein": 0}
