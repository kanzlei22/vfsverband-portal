"""
Supabase Client und Hilfsfunktionen
"""

import streamlit as st
from supabase import create_client, Client

# API Version für Kompatibilitätsprüfung
EXPECTED_API_VERSION = "1.0"


def get_supabase() -> Client:
    """Gibt den Supabase Client zurück."""
    if "supabase" not in st.session_state:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        st.session_state.supabase = create_client(url, key)
    return st.session_state.supabase


def check_maintenance():
    """Prüft ob Wartungsmodus aktiv ist."""
    try:
        supabase = get_supabase()
        result = supabase.table("system_status").select("*").eq("id", 1).single().execute()
        
        if result.data:
            status = result.data
            
            # API-Version prüfen
            api_version = status.get("api_version", "1.0")
            if api_version != EXPECTED_API_VERSION:
                return True, f"Bitte aktualisiere die App. (API: {api_version} erwartet: {EXPECTED_API_VERSION})"
            
            # Wartungsmodus prüfen
            if status.get("is_maintenance"):
                return True, status.get("maintenance_message", "Wartungsarbeiten")
        
        return False, None
        
    except Exception as e:
        # Bei Verbindungsfehler → Wartungsmodus anzeigen
        return True, f"Verbindungsfehler: {str(e)}"


def get_kunde_by_email(email: str):
    """Sucht Kunden anhand der E-Mail."""
    try:
        supabase = get_supabase()
        result = supabase.table("kunden").select("*").eq("email", email.lower()).eq("is_active", True).single().execute()
        return result.data
    except:
        return None


def update_kunde_data(kunde_id: str, sheet_data: dict):
    """Aktualisiert die Stammdaten eines Kunden."""
    try:
        supabase = get_supabase()
        result = supabase.table("kunden").update({
            "sheet_data": sheet_data
        }).eq("id", kunde_id).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def get_kategorien():
    """Gibt alle Kategorien zurück."""
    try:
        supabase = get_supabase()
        result = supabase.table("kategorien").select("*").order("sortierung").execute()
        return result.data or []
    except:
        return []


def get_vorlagen(kategorie: str = None):
    """Gibt Vorlagen zurück, optional nach Kategorie gefiltert."""
    try:
        supabase = get_supabase()
        query = supabase.table("vorlagen").select("*").eq("is_active", True)
        
        if kategorie:
            query = query.eq("kategorie", kategorie)
        
        result = query.order("sortierung").execute()
        return result.data or []
    except:
        return []


def get_vorlage_by_id(vorlage_id: str):
    """Gibt eine einzelne Vorlage zurück."""
    try:
        supabase = get_supabase()
        result = supabase.table("vorlagen").select("*").eq("id", vorlage_id).single().execute()
        return result.data
    except:
        return None


def save_dokument(kunde_id: str, vorlage_id: str, name: str, pdf_url: str = None, pdf_bytes: bytes = None):
    """Speichert ein generiertes Dokument. Optional mit PDF in Storage."""
    try:
        supabase = get_supabase()
        
        # PDF in Storage hochladen wenn vorhanden
        if pdf_bytes:
            try:
                import time
                
                # Dateinamen für Storage bereinigen (keine Umlaute/Sonderzeichen)
                safe_name = name
                # Umlaute ersetzen
                replacements = {
                    'ä': 'ae', 'ö': 'oe', 'ü': 'ue', 'ß': 'ss',
                    'Ä': 'Ae', 'Ö': 'Oe', 'Ü': 'Ue',
                    ' ': '_', '|': '-', '/': '-', '\\': '-',
                    ':': '-', '*': '', '?': '', '"': '', '<': '', '>': ''
                }
                for old, new in replacements.items():
                    safe_name = safe_name.replace(old, new)
                
                timestamp = int(time.time())
                path = f"{kunde_id}/{timestamp}_{safe_name}"
                
                # Upload zu Supabase Storage
                result = supabase.storage.from_("dokumente").upload(
                    path,
                    pdf_bytes,
                    file_options={"content-type": "application/pdf"}
                )
                
                # Public URL generieren
                pdf_url = supabase.storage.from_("dokumente").get_public_url(path)
                
            except Exception as e:
                import streamlit as st
                st.warning(f"⚠️ PDF konnte nicht in Cloud gespeichert werden: {e}")
                # Weiter ohne URL - Dokument wird trotzdem in DB gespeichert
        
        result = supabase.table("dokumente").insert({
            "kunde_id": kunde_id,
            "vorlage_id": vorlage_id,
            "name": name,
            "pdf_url": pdf_url
        }).execute()
        return result.data[0] if result.data else None
    except Exception as e:
        import streamlit as st
        st.error(f"Fehler beim Speichern: {e}")
        return None


def get_meine_dokumente(kunde_id: str):
    """Gibt alle Dokumente eines Kunden zurück."""
    try:
        supabase = get_supabase()
        result = supabase.table("dokumente").select(
            "*, vorlagen(name, kategorie)"
        ).eq("kunde_id", kunde_id).order("created_at", desc=True).execute()
        return result.data or []
    except:
        return []


def delete_dokument(dokument_id: str):
    """Löscht ein Dokument."""
    try:
        supabase = get_supabase()
        supabase.table("dokumente").delete().eq("id", dokument_id).execute()
        return True, None
    except Exception as e:
        return False, str(e)


def rename_dokument(dokument_id: str, new_name: str):
    """Benennt ein Dokument um."""
    try:
        supabase = get_supabase()
        supabase.table("dokumente").update({"name": new_name}).eq("id", dokument_id).execute()
        return True, None
    except Exception as e:
        return False, str(e)
