"""
Mitglieder Synchronisation
- Google Sheets → Supabase
- Supabase → HubSpot
- Supabase → MeinVerein CSV Export
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
        
        # Credentials aus Secrets
        if "google_oauth_token" not in st.secrets:
            return {"success": False, "imported": 0, "error": "Google OAuth Token nicht konfiguriert."}
        
        token_info = dict(st.secrets["google_oauth_token"])
        creds = Credentials(
            token=token_info.get("token"),
            refresh_token=token_info.get("refresh_token"),
            token_uri=token_info.get("token_uri"),
            client_id=token_info.get("client_id"),
            client_secret=token_info.get("client_secret")
        )
        
        service = build('sheets', 'v4', credentials=creds)
        
        # Daten aus Sheet laden
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range='A:Z'  # Alle Spalten
        ).execute()
        
        rows = result.get('values', [])
        
        if len(rows) <= 1:
            return {"success": True, "imported": 0, "error": None}
        
        # Header-Zeile
        headers = rows[0]
        
        # Mapping der Spalten (anpassen je nach Google Form)
        column_map = {
            "Anrede": "anrede",
            "Vorname": "vorname",
            "Nachname": "nachname",
            "E-Mail-Adresse": "email",
            "Telefon / Mobil": "telefon",
            "Straße und Hausnummer": "strasse",
            "Postleitzahl": "plz",
            "Ort": "ort",
            "IBAN": "iban",
            "Kontoinhaber": "kontoinhaber",
            "Ich beantrage die Mitgliedschaft als": "mitgliedsart_raw",
            "Zahlungsweise": "zahlungsweise_raw",
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
                
                # Beitrag berechnen
                beitrag = 25.00
                if mitgliedsart == "juristisch":
                    zahlungsweise = "jaehrlich"  # Juristische Personen nur jährlich
                
                # Neues Mitglied anlegen
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
                    "mitgliedsart": mitgliedsart,
                    "zahlungsweise": zahlungsweise,
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
        
        synced = 0
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        
        for m in mitglieder:
            try:
                # Anrede für HubSpot (Liebe/Lieber)
                anrede_hs = "Lieber" if m.get("anrede") == "Herr" else "Liebe"
                
                # Kontakt-Daten für HubSpot
                contact_data = {
                    "properties": {
                        "email": m["email"],
                        "firstname": m["vorname"],
                        "lastname": m["nachname"],
                        "phone": m.get("telefon", ""),
                        "address": m.get("strasse", ""),
                        "zip": m.get("plz", ""),
                        "city": m.get("ort", ""),
                        "salutation": anrede_hs,
                        # Custom Properties (falls vorhanden in HubSpot)
                        # "mitgliedsnummer": m.get("mandatsreferenz", ""),
                        # "mitglied_seit": m.get("genehmigt_am", "")[:10] if m.get("genehmigt_am") else ""
                    }
                }
                
                # Prüfen ob Kontakt bereits existiert
                search_url = "https://api.hubapi.com/crm/v3/objects/contacts/search"
                search_body = {
                    "filterGroups": [{
                        "filters": [{
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": m["email"]
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
        
        # MeinVerein Spalten (exakt wie in der Vorlage)
        columns = [
            "Mitgliedsnr.", "Anrede", "Titel", "Vorname", "Nachname",
            "Telefon", "Mobil", "E-Mail", "Strasse & Hausnr.", "PLZ", "Ort", "Land",
            "Geburtstag", "Mitglied seit", "Ebene 1", "Ebene 2", "Ebene 3",
            "Ehrenmitglied", "Status", "Mitglied bis",
            "Beitrag (Bezeichnung)", "Beitrag (Typ)", "Beitrag (Betrag)", 
            "Beitrag (Zeitraum)", "Beitrag (Fälligkeit)", "Notizen",
            "Geschlecht", "Familienstand", "Zahlungsart", "IBAN", "Kontoinhaber",
            "SEPA-Mandat erteilt", "Mandatsreferenz", "Art des Mandats",
            "Art der nächsten Lastschrift", "Mandat erteilt am", "Letzte Verwendung",
            "Individuelles Feld 1", "Individuelles Feld 2", "Individuelles Feld 3",
            "Individuelles Feld 4", "Individuelles Feld 5"
        ]
        
        rows = []
        member_ids = []
        
        for m in mitglieder:
            # Mandatsdatum formatieren
            mandatsdatum = m.get("mandatsdatum", "")
            if mandatsdatum:
                try:
                    dt = datetime.fromisoformat(mandatsdatum.replace("Z", "+00:00")) if "T" in mandatsdatum else datetime.strptime(mandatsdatum, "%Y-%m-%d")
                    mandatsdatum = dt.strftime("%d.%m.%Y")
                except:
                    mandatsdatum = datetime.now().strftime("%d.%m.%Y")
            else:
                mandatsdatum = datetime.now().strftime("%d.%m.%Y")
            
            # Genehmigungsdatum
            genehmigt_am = m.get("genehmigt_am", "")
            if genehmigt_am:
                try:
                    dt = datetime.fromisoformat(genehmigt_am.replace("Z", "+00:00"))
                    mitglied_seit = dt.strftime("%d.%m.%Y")
                except:
                    mitglied_seit = datetime.now().strftime("%d.%m.%Y")
            else:
                mitglied_seit = datetime.now().strftime("%d.%m.%Y")
            
            # Geschlecht aus Anrede
            anrede = m.get("anrede", "Herr")
            geschlecht = "männlich" if anrede == "Herr" else "weiblich" if anrede == "Frau" else "divers"
            
            # Beitrag
            beitrag = m.get("beitrag_monatlich", 25.00)
            zahlungsweise = m.get("zahlungsweise", "monatlich")
            if zahlungsweise == "jaehrlich":
                beitrag_betrag = beitrag * 12
                beitrag_zeitraum = "jährlich"
            else:
                beitrag_betrag = beitrag
                beitrag_zeitraum = "monatlich"
            
            row = {
                "Mitgliedsnr.": m.get("mandatsreferenz", ""),
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
                "Mitglied seit": mitglied_seit,
                "Ebene 1": "",
                "Ebene 2": "",
                "Ebene 3": "",
                "Ehrenmitglied": "Nein",
                "Status": "Aktiv",
                "Mitglied bis": "",
                "Beitrag (Bezeichnung)": "Mitgliedsbeitrag",
                "Beitrag (Typ)": "Fördermitglied",
                "Beitrag (Betrag)": f"{beitrag_betrag:.2f}".replace(".", ","),
                "Beitrag (Zeitraum)": beitrag_zeitraum,
                "Beitrag (Fälligkeit)": "01",
                "Notizen": m.get("notizen", ""),
                "Geschlecht": geschlecht,
                "Familienstand": "",
                "Zahlungsart": "Lastschrift",
                "IBAN": m.get("iban", "").replace(" ", ""),
                "Kontoinhaber": m.get("kontoinhaber", ""),
                "SEPA-Mandat erteilt": "Ja",
                "Mandatsreferenz": m.get("mandatsreferenz", ""),
                "Art des Mandats": "Wiederkehrende Zahlung",
                "Art der nächsten Lastschrift": "Folgelastschrift",
                "Mandat erteilt am": mandatsdatum,
                "Letzte Verwendung": "",
                "Individuelles Feld 1": "",
                "Individuelles Feld 2": "",
                "Individuelles Feld 3": "",
                "Individuelles Feld 4": "",
                "Individuelles Feld 5": ""
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


def import_wiso_excel(file_data):
    """
    Importiert Bestandsmitglieder aus Wiso-Excel-Export.
    Returns: {"success": bool, "imported": int, "error": str}
    """
    try:
        import pandas as pd
        
        # Excel lesen
        df = pd.read_excel(io.BytesIO(file_data))
        
        supabase = get_supabase()
        imported = 0
        
        # Spalten-Mapping (anpassen je nach Wiso-Export)
        # Typische Wiso-Spalten: Anrede, Vorname, Nachname, E-Mail, Straße, PLZ, Ort, IBAN, etc.
        
        for _, row in df.iterrows():
            try:
                # E-Mail extrahieren (verschiedene mögliche Spaltennamen)
                email = None
                for col in ["E-Mail", "Email", "e-mail", "EMail", "E-Mail-Adresse"]:
                    if col in df.columns and pd.notna(row.get(col)):
                        email = str(row[col]).strip().lower()
                        break
                
                if not email:
                    continue
                
                # Prüfen ob bereits existiert
                existing = supabase.table("mitglieder").select("id").eq("email", email).execute()
                if existing.data:
                    continue
                
                # Daten extrahieren
                def get_col(possible_names, default=""):
                    for name in possible_names:
                        if name in df.columns and pd.notna(row.get(name)):
                            return str(row[name]).strip()
                    return default
                
                neues_mitglied = {
                    "anrede": get_col(["Anrede", "Titel"], "Herr"),
                    "vorname": get_col(["Vorname", "First Name"]),
                    "nachname": get_col(["Nachname", "Name", "Last Name"]),
                    "email": email,
                    "telefon": get_col(["Telefon", "Tel", "Phone", "Mobil"]),
                    "strasse": get_col(["Straße", "Strasse", "Adresse", "Street"]),
                    "plz": get_col(["PLZ", "Postleitzahl", "ZIP"]),
                    "ort": get_col(["Ort", "Stadt", "City"]),
                    "iban": get_col(["IBAN"]).replace(" ", "").upper(),
                    "kontoinhaber": get_col(["Kontoinhaber", "Kontoinh."], ""),
                    "mitgliedsart": "natuerlich",
                    "zahlungsweise": "monatlich",
                    "beitrag_monatlich": 25.00,
                    "status": "genehmigt",  # Bestandsmitglieder sind bereits genehmigt
                    "quelle": "wiso_import",
                    "genehmigt_am": datetime.now().isoformat(),
                    "mandatsreferenz": f"UV-IMPORT-{imported+1:04d}"
                }
                
                # Nur anlegen wenn Mindestdaten vorhanden
                if neues_mitglied["vorname"] and neues_mitglied["nachname"]:
                    supabase.table("mitglieder").insert(neues_mitglied).execute()
                    imported += 1
                    
            except Exception as e:
                continue
        
        return {"success": True, "imported": imported, "error": None}
        
    except Exception as e:
        return {"success": False, "imported": 0, "error": str(e)}
