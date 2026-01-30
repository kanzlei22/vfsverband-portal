"""
PDF-Generierung aus Google Docs Vorlagen
Nutzt Service Account für Cloud-Deployment
"""

import re
import os
from datetime import datetime
import streamlit as st
import io

# Google API
try:
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    GOOGLE_API_AVAILABLE = True
except ImportError:
    GOOGLE_API_AVAILABLE = False


SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]


def get_google_creds():
    """
    Holt Google API Credentials.
    Priorität: 1. OAuth Token aus Secrets, 2. token.json Datei, 3. Service Account
    """
    if not GOOGLE_API_AVAILABLE:
        raise Exception("Google API Libraries nicht installiert")
    
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    
    # Option 1: OAuth Token aus Streamlit Secrets (für Cloud Deployment)
    if "google_oauth_token" in st.secrets:
        try:
            token_info = dict(st.secrets["google_oauth_token"])
            creds = Credentials(
                token=token_info.get("token"),
                refresh_token=token_info.get("refresh_token"),
                token_uri=token_info.get("token_uri"),
                client_id=token_info.get("client_id"),
                client_secret=token_info.get("client_secret"),
                scopes=SCOPES
            )
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            return creds
        except Exception as e:
            pass  # Fallback zu anderen Optionen
    
    # Option 2: Token.json Datei (für lokale Entwicklung)
    token_path = "config/token.json"
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(token_path, 'w') as f:
                    f.write(creds.to_json())
            return creds
        except Exception as e:
            pass  # Fallback zu Service Account
    
    # Option 3: Service Account (Fallback)
    try:
        if "google_service_account" in st.secrets:
            service_account_info = dict(st.secrets["google_service_account"])
            creds = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=SCOPES
            )
            return creds
        else:
            raise Exception("Keine Google Credentials konfiguriert (OAuth Token, token.json oder Service Account)")
    except Exception as e:
        raise Exception(f"Google Auth: {str(e)}")


def extract_placeholder_key(field_name: str) -> str:
    """Extrahiert den Platzhalter-Key aus einem Feldnamen."""
    match = re.search(r'\[([^\]]+)\]', field_name)
    if match:
        return match.group(1).strip()
    return field_name.replace(' ', '_').lower().strip()


def format_value(value) -> str:
    """Formatiert Werte für die Dokumentenausgabe."""
    if not value:
        return ""
    val_str = str(value).strip()
    match_de = re.match(r'^(\d{1,2}\.\d{1,2}\.\d{4})\s+\d{1,2}:\d{2}(:\d{2})?$', val_str)
    if match_de:
        return match_de.group(1)
    match_iso = re.match(r'^(\d{4})-(\d{2})-(\d{2})', val_str)
    if match_iso:
        return f"{match_iso.group(3)}.{match_iso.group(2)}.{match_iso.group(1)}"
    return val_str


def generate_pdf_from_template(template_id: str, sheet_data: dict, output_name: str):
    """
    Generiert ein PDF aus einer Google Docs Vorlage.
    Returns: (pdf_bytes, error_message)
    """
    try:
        creds = get_google_creds()
        drive_service = build("drive", "v3", credentials=creds)
        docs_service = build("docs", "v1", credentials=creds)
        
        # 1. Template kopieren (in User-Ordner um Quota-Problem zu vermeiden)
        copy_metadata = {"name": f"TEMP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"}
        
        # Zielordner aus Secrets (optional)
        if "temp_folder_id" in st.secrets:
            copy_metadata["parents"] = [st.secrets["temp_folder_id"]]
        copied_file = drive_service.files().copy(fileId=template_id, body=copy_metadata).execute()
        temp_doc_id = copied_file.get("id")
        
        try:
            # 2. MAPPING: Forms-Felder → Platzhalter
            # Die Felder aus Google Forms haben andere Namen als die Platzhalter
            FIELD_MAPPING = {
                # Vereinsdaten
                "Vereinsname (Ihre Idee)": "vereinsname",
                "Sitz des Vereins": "sitz",
                "Anschrift des Vereins": "verein_anschrift",
                "Vereinszweck (Ihre Grundidee)": "zweck",
                
                # Gründung
                "Gründungsort": "gründungsort",
                "Gründungsdatum": "gründungsdatum",
                "Gründungszeit": "gründungszeit_beginn",
                
                # Gründer
                "Name Gründer": "verein_gründer",
                "Anschrift Gründer": "verein_gründer_anschrift",
                "Geburtsdatum Gründer": "verein_gründer_geburtsdatum",
                "Geburtsort Gründer": "verein_gründer_geburtsort",
                "Ihr Name": "verein_gründer",  # Fallback
                
                # Mitglieder
                "Name Mitglied 2": "verein_mitglied2",
                "Anschrift Mitglied 2": "verein_mitglied2_anschrift",
                "Name Mitglied 3": "verein_mitglied3",
                "Anschrift Mitglied 3": "verein_mitglied3_anschrift",
                "Name Mitglied 4": "verein_mitglied4",
                "Anschrift Mitglied 4": "verein_mitglied4_anschrift",
                "Name Mitglied 5": "verein_mitglied5",
                "Anschrift Mitglied 5": "verein_mitglied5_anschrift",
                "Name Mitglied 6": "verein_mitglied6",
                "Anschrift Mitglied 6": "verein_mitglied6_anschrift",
                "Name Mitglied 7": "verein_mitglied7",
                "Anschrift Mitglied 7": "verein_mitglied7_anschrift",
                
                # Protokoll
                "Protokollführer": "verein_protokollführer",
                
                # Gericht
                "Amtsgericht": "verein_gericht",
                "Amtsgericht Anschrift": "verein_gericht_anschrift",
                
                # Notar
                "Notar": "verein_notar",
                "Notar Anschrift 1": "verein_notar_anschrift1",
                "Notar Anschrift 2": "verein_notar_anschrift2",
                
                # KI-Felder (werden direkt durchgereicht, hier nur zur Sicherheit)
                "claim": "claim",
                "Vorbemerkung": "Vorbemerkung",
                "verwirklichung": "verwirklichung",
                "gründungsprotokoll_idee": "gründungsprotokoll_idee",
                "gericht_anschreiben_zweck": "verein_gericht_idee",
            }
            
            # 3. Master-Data aufbauen mit Mapping
            master_data = {}
            
            for key, value in sheet_data.items():
                if not value:
                    continue
                    
                # Original-Key behalten
                master_data[str(key)] = value
                
                # Gemappten Key hinzufügen
                if key in FIELD_MAPPING:
                    mapped_key = FIELD_MAPPING[key]
                    master_data[mapped_key] = value
                
                # Auch lowercase Version
                master_data[str(key).lower()] = value
            
            # 4. Platzhalter ersetzen
            requests = []
            for key, value in master_data.items():
                val_str = format_value(value)
                
                # Verschiedene Platzhalter-Formate
                placeholders = [
                    f"{{{{{key}}}}}",      # {{key}}
                    f"{{{{{key.lower()}}}}}",  # {{key}} lowercase
                    f"[{key}]",             # [key]
                ]
                
                for placeholder in placeholders:
                    requests.append({
                        "replaceAllText": {
                            "containsText": {"text": placeholder, "matchCase": False},
                            "replaceText": val_str
                        }
                    })
            
            if requests:
                docs_service.documents().batchUpdate(
                    documentId=temp_doc_id,
                    body={"requests": requests}
                ).execute()
            
            # 5. Als PDF exportieren
            pdf_request = drive_service.files().export_media(
                fileId=temp_doc_id,
                mimeType="application/pdf"
            )
            
            pdf_buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(pdf_buffer, pdf_request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            
            return pdf_buffer.getvalue(), None
            
        finally:
            try:
                drive_service.files().delete(fileId=temp_doc_id).execute()
            except:
                pass
        
    except Exception as e:
        return None, str(e)


def upload_pdf_to_drive(pdf_bytes: bytes, filename: str, folder_id: str = None):
    """Lädt PDF nach Google Drive hoch."""
    return None, "Nicht implementiert"
