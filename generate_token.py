from google_auth_oauthlib.flow import InstalledAppFlow
import json

SCOPES = [
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive'
]

# Nutze die client_secret.json aus dem Admin-Tool
flow = InstalledAppFlow.from_client_secrets_file(
    '../config/client_secret.json',  # Pfad anpassen falls nötig
    SCOPES
)

creds = flow.run_local_server(port=0)

with open('config/token.json', 'w') as f:
    f.write(creds.to_json())

print("✅ Neues token.json erstellt!")