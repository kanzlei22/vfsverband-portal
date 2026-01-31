#!/usr/bin/env python3
"""
Script zum Erstellen des Google Forms für Vereinsbeitritt
UnternehmerVernetzt Deutschland e.V.

Ausführung:
    python scripts/create_beitrittsformular.py
"""

import os
import sys
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import json

# Scopes für Forms und Drive
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
                print("   Bitte lade die OAuth Client Credentials von Google Cloud Console herunter.")
                sys.exit(1)
            
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    return creds


def create_beitrittsformular():
    """Erstellt das Beitrittsformular mit allen Sektionen."""
    
    creds = get_credentials()
    forms_service = build('forms', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    print("🚀 Erstelle Beitrittsformular...")
    
    # === FORMULAR ERSTELLEN ===
    form = {
        "info": {
            "title": "Beitrittsantrag - UnternehmerVernetzt Deutschland e.V.",
            "documentTitle": "Beitrittsantrag UnternehmerVernetzt"
        }
    }
    
    result = forms_service.forms().create(body=form).execute()
    form_id = result['formId']
    print(f"✅ Formular erstellt: {form_id}")
    
    # === FORMULAR-INHALT AUFBAUEN ===
    requests = []
    item_index = 0
    
    # --- SEKTION 1: WILLKOMMEN ---
    requests.append({
        "createItem": {
            "item": {
                "title": "Willkommen bei UnternehmerVernetzt! 🤝",
                "description": """Schön, dass du dich für eine Mitgliedschaft interessierst!

UnternehmerVernetzt Deutschland e.V. ist ein Netzwerk von Unternehmern, 
die sich gegenseitig unterstützen und gemeinsam wachsen.

📋 Was dich erwartet:
• Regelmäßige Netzwerktreffen
• Zugang zu exklusiven Events
• Austausch mit Gleichgesinnten
• Gemeinsame Projekte und Kooperationen

⏱️ Dieser Antrag dauert ca. 3-5 Minuten.

Alle mit * markierten Felder sind Pflichtfelder.""",
                "textItem": {}
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Page Break nach Willkommen
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
    
    # --- SEKTION 2: PERSÖNLICHE DATEN ---
    
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
                        "textQuestion": {
                            "paragraph": False
                        }
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
                        "textQuestion": {
                            "paragraph": False
                        }
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
                "description": "An diese Adresse senden wir die Bestätigung und alle wichtigen Informationen.",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {
                            "paragraph": False
                        }
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
                "description": "Optional - für Rückfragen",
                "questionItem": {
                    "question": {
                        "required": False,
                        "textQuestion": {
                            "paragraph": False
                        }
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
                "description": "Deine Anschrift für die Mitgliedsunterlagen.",
                "pageBreakItem": {}
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # --- SEKTION 3: ADRESSE ---
    
    # Straße + Hausnummer
    requests.append({
        "createItem": {
            "item": {
                "title": "Straße und Hausnummer *",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {
                            "paragraph": False
                        }
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
                        "textQuestion": {
                            "paragraph": False
                        }
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
                        "textQuestion": {
                            "paragraph": False
                        }
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
                "title": "Art der Mitgliedschaft",
                "description": """Wähle die passende Mitgliedschaftsart:

👤 **Natürliche Person** (Privatperson/Einzelunternehmer)
   • Monatlich: 25 € / Monat
   • Jährlich: 300 € / Jahr (entspricht 25 € / Monat)

🏢 **Juristische Person** (GmbH, UG, AG, etc.)
   • Nur Jahreszahlung: 300 € / Jahr""",
                "pageBreakItem": {}
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # --- SEKTION 4: MITGLIEDSCHAFT ---
    
    # Mitgliedsart
    requests.append({
        "createItem": {
            "item": {
                "title": "Ich beantrage die Mitgliedschaft als *",
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
    
    # Firmenname (optional)
    requests.append({
        "createItem": {
            "item": {
                "title": "Firmenname",
                "description": "Nur bei juristischer Person oder wenn du als Firma auftreten möchtest.",
                "questionItem": {
                    "question": {
                        "required": False,
                        "textQuestion": {
                            "paragraph": False
                        }
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
                "description": "Bei juristischen Personen ist nur Jahreszahlung möglich.",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "RADIO",
                            "options": [
                                {"value": "Monatlich (25 € / Monat per Lastschrift)"},
                                {"value": "Jährlich (300 € / Jahr per Lastschrift)"}
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
                "title": "Bankverbindung & SEPA-Lastschrift",
                "description": """Für den Einzug des Mitgliedsbeitrags benötigen wir deine Bankverbindung.

🔒 Deine Daten werden sicher und verschlüsselt übertragen.
📋 Mit der Angabe erteilst du uns ein SEPA-Lastschriftmandat.""",
                "pageBreakItem": {}
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # --- SEKTION 5: BANKDATEN ---
    
    # IBAN
    requests.append({
        "createItem": {
            "item": {
                "title": "IBAN *",
                "description": "Deine IBAN findest du auf deiner Bankkarte oder im Online-Banking. Beispiel: DE89 3704 0044 0532 0130 00",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {
                            "paragraph": False
                        }
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
                "title": "Kontoinhaber *",
                "description": "Name wie er auf dem Konto steht (falls abweichend von deinem Namen).",
                "questionItem": {
                    "question": {
                        "required": True,
                        "textQuestion": {
                            "paragraph": False
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
                "title": "Bestätigung & Einwilligung",
                "description": """Fast geschafft! Bitte lies und bestätige die folgenden Punkte.

📄 Satzung: https://www.driver39.de/verein/satzung
📄 Datenschutz: https://www.driver39.de/datenschutz""",
                "pageBreakItem": {}
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # --- SEKTION 6: BESTÄTIGUNG ---
    
    # Satzung akzeptiert
    requests.append({
        "createItem": {
            "item": {
                "title": "Satzung *",
                "questionItem": {
                    "question": {
                        "required": True,
                        "choiceQuestion": {
                            "type": "CHECKBOX",
                            "options": [
                                {"value": "Ich habe die Satzung gelesen und erkenne sie an."}
                            ]
                        }
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
                "title": "SEPA-Lastschriftmandat *",
                "description": """Gläubiger-Identifikationsnummer: DE... (wird nachgereicht)
Mandatsreferenz: Wird nach Aufnahme mitgeteilt

Ich ermächtige UnternehmerVernetzt Deutschland e.V., Zahlungen von meinem Konto 
mittels Lastschrift einzuziehen. Zugleich weise ich mein Kreditinstitut an, 
die vom Verein gezogenen Lastschriften einzulösen.""",
                "questionItem": {
                    "question": {
                        "required": True,
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
                                {"value": "Ich habe die Datenschutzerklärung gelesen und stimme der Verarbeitung meiner Daten zu."}
                            ]
                        }
                    }
                }
            },
            "location": {"index": item_index}
        }
    })
    item_index += 1
    
    # Abschluss-Text
    requests.append({
        "createItem": {
            "item": {
                "title": "🎉 Vielen Dank für dein Interesse!",
                "description": """Nach dem Absenden wird dein Antrag vom Vorstand geprüft.

📧 Du erhältst eine Bestätigung per E-Mail.
⏱️ Die Bearbeitung dauert in der Regel 1-3 Werktage.

Bei Fragen erreichst du uns unter:
📧 info@driver39.de
🌐 www.driver39.de/verein""",
                "textItem": {}
            },
            "location": {"index": item_index}
        }
    })
    
    # === BATCH UPDATE ===
    print("📝 Füge Felder hinzu...")
    
    forms_service.forms().batchUpdate(
        formId=form_id,
        body={"requests": requests}
    ).execute()
    
    print("✅ Alle Felder hinzugefügt!")
    
    # === ANTWORTEN MIT GOOGLE SHEET VERKNÜPFEN ===
    print("📊 Erstelle verknüpftes Google Sheet...")
    
    # Sheet erstellen
    sheets_service = build('sheets', 'v4', credentials=creds)
    
    spreadsheet = {
        'properties': {
            'title': 'UnternehmerVernetzt - Beitrittsanträge'
        }
    }
    
    sheet_result = sheets_service.spreadsheets().create(body=spreadsheet).execute()
    sheet_id = sheet_result['spreadsheetId']
    sheet_url = sheet_result['spreadsheetUrl']
    
    print(f"✅ Sheet erstellt: {sheet_id}")
    
    # Form mit Sheet verknüpfen
    link_request = {
        "requests": [{
            "updateSettings": {
                "settings": {
                    "responseDestinationType": "SPREADSHEET",
                    "responseDestinationId": sheet_id
                },
                "updateMask": "responseDestinationType,responseDestinationId"
            }
        }]
    }
    
    # Hinweis: Die direkte Verknüpfung über API ist komplex.
    # Stattdessen muss das Sheet manuell verknüpft werden.
    
    # === AUSGABE ===
    form_url = f"https://docs.google.com/forms/d/{form_id}/edit"
    form_view_url = f"https://docs.google.com/forms/d/{form_id}/viewform"
    
    print("\n" + "="*60)
    print("🎉 FERTIG!")
    print("="*60)
    print(f"\n📝 Formular bearbeiten:")
    print(f"   {form_url}")
    print(f"\n👁️ Formular ansehen (Teilnehmer-Link):")
    print(f"   {form_view_url}")
    print(f"\n📊 Google Sheet:")
    print(f"   {sheet_url}")
    print("\n⚠️  WICHTIG: Verknüpfe das Sheet manuell mit dem Formular:")
    print("    1. Öffne das Formular")
    print("    2. Klicke auf 'Antworten' Tab")
    print("    3. Klicke auf das grüne Sheet-Symbol")
    print("    4. Wähle 'Vorhandene Tabelle auswählen'")
    print("    5. Wähle 'UnternehmerVernetzt - Beitrittsanträge'")
    print("="*60)
    
    # Speichere IDs für spätere Verwendung
    config = {
        "form_id": form_id,
        "form_url": form_url,
        "form_view_url": form_view_url,
        "sheet_id": sheet_id,
        "sheet_url": sheet_url
    }
    
    config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'beitrittsformular.json')
    with open(config_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n💾 Konfiguration gespeichert in: config/beitrittsformular.json")
    
    return config


if __name__ == "__main__":
    create_beitrittsformular()
