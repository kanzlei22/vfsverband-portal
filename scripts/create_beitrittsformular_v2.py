#!/usr/bin/env python3
"""
Script zum Erstellen des Google Forms für Vereinsbeitritt V2
UnternehmerVernetzt Deutschland e.V.

Änderungen V2:
- Instagramname abfragen
- Zahlungsart: Lastschrift ODER Rechnung
- IBAN/SEPA nicht mehr Pflicht
- Neuer Bestätigungstext
- Überarbeitetes "Was Dich erwartet"

Ausführung:
    python scripts/create_beitrittsformular_v2.py
"""

import os
import sys
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import json

SCOPES = [
    'https://www.googleapis.com/auth/forms.body',
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

def get_credentials():
    """Holt oder erstellt Credentials."""
    creds = None
    token_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'token_forms.json')
    creds_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'credentials.json')
    
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                print("❌ Fehler: credentials.json nicht gefunden!")
                sys.exit(1)
            
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    return creds


def create_beitrittsformular():
    """Erstellt das Beitrittsformular V2."""
    
    creds = get_credentials()
    forms_service = build('forms', 'v1', credentials=creds)
    
    print("🚀 Erstelle Beitrittsformular V2...")
    
    # === FORMULAR ERSTELLEN ===
    form = {
        "info": {
            "title": "Fördermitglied werden - UnternehmerVernetzt Deutschland e.V.",
            "documentTitle": "Beitrittsantrag UnternehmerVernetzt V2"
        }
    }
    
    result = forms_service.forms().create(body=form).execute()
    form_id = result['formId']
    print(f"✅ Formular erstellt: {form_id}")
    
    requests = []
    item_index = 0
    
    # --- SEKTION 1: WILLKOMMEN ---
    requests.append({
        "createItem": {
            "item": {
                "title": "Willkommen bei UnternehmerVernetzt! 🤝",
                "description": """Schön, dass du Fördermitglied werden möchtest!

UnternehmerVernetzt Deutschland e.V. ist Träger des @vfsverband – ein lebendiges Netzwerk von Unternehmern.

🎯 Was Dich erwartet:
• Lebendige Community mit aktiven Unternehmern
• Fachgruppen für Social Media, KI, Coding und allgemeine Unternehmerfragen
• Riesiges und stetig wachsendes Videoarchiv
• Häufig Vorteile bei Events des @vfsverband
• Regelmäßige Netzwerktreffen und Austausch

💰 Mitgliedsbeitrag: 25 € / Monat (oder 300 € / Jahr)
📋 Kündigung: Jederzeit zum Quartalsende möglich

⏱️ Dieser Antrag dauert ca. 3-5 Minuten.""",
                "textItem": {}
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Page Break
    requests.append({
        "createItem": {
            "item": {
                "title": "Persönliche Daten",
                "description": "Bitte gib deine Kontaktdaten ein.",
                "pageBreakItem": {}
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # --- PERSÖNLICHE DATEN ---
    
    # Anrede
    requests.append({
        "createItem": {
            "item": {
                "title": "Anrede *",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": [
                                {"value": "Herr"},
                                {"value": "Frau"},
                                {"value": "Divers"}
                            ]
                        }
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Vorname
    requests.append({
        "createItem": {
            "item": {
                "title": "Vorname *",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {"paragraph": False}
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Nachname
    requests.append({
        "createItem": {
            "item": {
                "title": "Nachname *",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {"paragraph": False}
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # E-Mail
    requests.append({
        "createItem": {
            "item": {
                "title": "E-Mail-Adresse *",
                "description": "Hierhin senden wir die Bestätigung.",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {"paragraph": False}
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Telefon
    requests.append({
        "createItem": {
            "item": {
                "title": "Telefon / Mobil",
                "description": "Optional",
                "questionItem": {
                    "question": {
                        "required": False,
                        "textQuestion": {"paragraph": False}
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Instagram
    requests.append({
        "createItem": {
            "item": {
                "title": "Instagram-Name",
                "description": "Optional - z.B. @deinname (hilft uns, dich in der Community zu vernetzen!)",
                "questionItem": {
                    "question": {
                        "required": False,
                        "textQuestion": {"paragraph": False}
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Page Break - Adresse
    requests.append({
        "createItem": {
            "item": {
                "title": "Adresse",
                "description": "Für Mitgliedsunterlagen und Rechnungen.",
                "pageBreakItem": {}
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # --- ADRESSE ---
    
    # Straße
    requests.append({
        "createItem": {
            "item": {
                "title": "Straße und Hausnummer *",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {"paragraph": False}
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # PLZ
    requests.append({
        "createItem": {
            "item": {
                "title": "Postleitzahl *",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {"paragraph": False}
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Ort
    requests.append({
        "createItem": {
            "item": {
                "title": "Ort *",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {"paragraph": False}
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Page Break - Mitgliedschaft
    requests.append({
        "createItem": {
            "item": {
                "title": "Mitgliedschaft & Zahlung",
                "description": """👤 Natürliche Person: 25 €/Monat oder 300 €/Jahr
🏢 Juristische Person: Nur 300 €/Jahr""",
                "pageBreakItem": {}
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # --- MITGLIEDSCHAFT ---
    
    # Mitgliedsart
    requests.append({
        "createItem": {
            "item": {
                "title": "Mitgliedschaft als *",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": [
                                {"value": "Natürliche Person (Privatperson / Einzelunternehmer)"},
                                {"value": "Juristische Person (GmbH, UG, AG, etc.)"}
                            ]
                        }
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Firmenname
    requests.append({
        "createItem": {
            "item": {
                "title": "Firmenname",
                "description": "Nur bei juristischer Person",
                "questionItem": {
                    "question": {
                        "required": False,
                        "textQuestion": {"paragraph": False}
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Zahlungsweise
    requests.append({
        "createItem": {
            "item": {
                "title": "Zahlungsweise *",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": [
                                {"value": "Monatlich (25 € / Monat)"},
                                {"value": "Jährlich (300 € / Jahr)"}
                            ]
                        }
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Zahlungsart
    requests.append({
        "createItem": {
            "item": {
                "title": "Zahlungsart *",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": [
                                {"value": "Per Lastschrift (bequem & automatisch)"},
                                {"value": "Auf Rechnung (manuelle Überweisung)"}
                            ]
                        }
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Page Break - Bankdaten
    requests.append({
        "createItem": {
            "item": {
                "title": "Bankverbindung (nur bei Lastschrift)",
                "description": """⚠️ NUR AUSFÜLLEN wenn du "Per Lastschrift" gewählt hast!
Bei "Auf Rechnung" kannst du diese Sektion überspringen.""",
                "pageBreakItem": {}
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # --- BANKDATEN (OPTIONAL) ---
    
    # IBAN
    requests.append({
        "createItem": {
            "item": {
                "title": "IBAN",
                "description": "Nur bei Lastschrift. Beispiel: DE89 3704 0044 0532 0130 00",
                "questionItem": {
                    "question": {
                        "required": False,
                        "textQuestion": {"paragraph": False}
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Kontoinhaber
    requests.append({
        "createItem": {
            "item": {
                "title": "Kontoinhaber",
                "description": "Nur bei Lastschrift",
                "questionItem": {
                    "question": {
                        "required": False,
                        "textQuestion": {"paragraph": False}
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # SEPA-Mandat
    requests.append({
        "createItem": {
            "item": {
                "title": "SEPA-Lastschriftmandat",
                "description": "Nur bei Lastschrift",
                "questionItem": {
                    "question": {
                        "required": False,
                        "choiceQuestion": {
                            "type": "CHECKBOX",
                            "options": [
                                {"value": "Ich erteile das SEPA-Lastschriftmandat für den Mitgliedsbeitrag."}
                            ]
                        }
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Page Break - Bestätigung
    requests.append({
        "createItem": {
            "item": {
                "title": "Bestätigung",
                "description": """📄 Satzung: https://www.driver39.de/verein/satzung
📄 Datenschutz: https://www.driver39.de/datenschutz""",
                "pageBreakItem": {}
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # --- BESTÄTIGUNG ---
    
    # Fördermitgliedschaft
    requests.append({
        "createItem": {
            "item": {
                "title": "Antrag Fördermitgliedschaft *",
                "description": "UnternehmerVernetzt Deutschland e.V., Träger des @vfsverband",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "CHECKBOX",
                            "options": [
                                {"value": "Hiermit beantrage ich die Fördermitgliedschaft im Verein. Der monatliche Mitgliedsbeitrag beträgt 25 Euro. Die Mitgliedschaft kann jederzeit zum Quartalsende formlos per Kündigung beendet werden. Ich habe die Satzung gelesen und erkenne sie an."}
                            ]
                        }
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Datenschutz
    requests.append({
        "createItem": {
            "item": {
                "title": "Datenschutz *",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "CHECKBOX",
                            "options": [
                                {"value": "Ich habe die Datenschutzerklärung gelesen und stimme zu."}
                            ]
                        }
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Abschluss
    requests.append({
        "createItem": {
            "item": {
                "title": "🎉 Vielen Dank!",
                "description": """Dein Antrag wird vom Vorstand geprüft.
📧 Bestätigung per E-Mail in 1-3 Werktagen.

Fragen? info@driver39.de | @vfsverband""",
                "textItem": {}
            },
            "location": {"index": item_index}
        }
    })
    
    # === BATCH UPDATE ===
    print("📝 Füge Felder hinzu...")
    forms_service.forms().batchUpdate(formId=form_id, body={"requests": requests}).execute()
    print("✅ Alle Felder hinzugefügt!")
    
    # === SHEET ERSTELLEN ===
    sheets_service = build('sheets', 'v4', credentials=creds)
    spreadsheet = {'properties': {'title': 'UnternehmerVernetzt - Beitrittsanträge V2'}}
    sheet_result = sheets_service.spreadsheets().create(body=spreadsheet).execute()
    sheet_id = sheet_result['spreadsheetId']
    sheet_url = sheet_result['spreadsheetUrl']
    print(f"✅ Sheet erstellt: {sheet_id}")
    
    # === AUSGABE ===
    form_url = f"https://docs.google.com/forms/d/{form_id}/edit"
    form_view_url = f"https://docs.google.com/forms/d/{form_id}/viewform"
    
    print("\n" + "="*60)
    print("🎉 FERTIG!")
    print("="*60)
    print(f"\n📝 Formular bearbeiten: {form_url}")
    print(f"\n👁️ Teilnehmer-Link: {form_view_url}")
    print(f"\n📊 Google Sheet: {sheet_url}")
    print("\n⚠️  WICHTIG: Verknüpfe das Sheet manuell!")
    print("="*60)
    
    # Config speichern
    config = {
        "form_id": form_id,
        "form_url": form_url,
        "form_view_url": form_view_url,
        "sheet_id": sheet_id,
        "sheet_url": sheet_url
    }
    
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'beitrittsformular_v2.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n💾 Config: config/beitrittsformular_v2.json")
    return config


if __name__ == "__main__":
    create_beitrittsformular()
