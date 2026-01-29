# 🏛️ Vereins-Generator: Kunden-Portal

## Übersicht

Dieses Portal ermöglicht es deinen Kunden nach der Vereinsgründung:
- Ihre Stammdaten einzusehen und zu bearbeiten
- Dokumente aus Vorlagen zu generieren (als PDF)
- Ihre generierten Dokumente herunterzuladen

---

## 🏗️ Architektur

```
┌─────────────────────────────────────────────────────────────────┐
│  DEIN LOKALES ADMIN-TOOL                                        │
│  /vereins_generator/                                            │
│                                                                 │
│  [☁️ Kunde freigeben] ──────────▶ Supabase Cloud DB            │
│  [🔄 Sync]            ◀──────────                               │
└─────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────┐
│  KUNDEN-PORTAL (Streamlit Cloud)                                │
│  /kunden_portal/                                                │
│                                                                 │
│  1. Google Login                                                │
│  2. Stammdaten anzeigen/bearbeiten                             │
│  3. Vorlagen-Katalog                                           │
│  4. PDF generieren                                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 SETUP-ANLEITUNG

### Schritt 1: Supabase Projekt erstellen

1. Gehe zu https://supabase.com
2. "Start your project" (kostenlos)
3. Projekt erstellen:
   - Name: `vereins-portal`
   - Region: Frankfurt (eu-central-1)
   - Passwort notieren!

4. Nach Erstellung → Settings → API:
   - **Project URL** kopieren (z.B. `https://xyz.supabase.co`)
   - **anon public key** kopieren

### Schritt 2: Datenbank-Schema anlegen

In Supabase → SQL Editor → "New query" → Folgendes einfügen und ausführen:

```sql
-- Kunden (synchronisiert aus deinem Admin-Tool)
CREATE TABLE kunden (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    local_id INTEGER UNIQUE,           -- ID aus deiner lokalen DB
    name TEXT NOT NULL,
    email TEXT UNIQUE,                  -- Für Login-Match
    vereinsname TEXT,
    sheet_data JSONB,                   -- Alle Stammdaten
    is_active BOOLEAN DEFAULT false,    -- Freigegeben?
    synced_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Vorlagen-Katalog
CREATE TABLE vorlagen (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT NOT NULL,
    kategorie TEXT NOT NULL,
    beschreibung TEXT,
    google_doc_id TEXT NOT NULL,        -- Master-Template ID
    sortierung INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Generierte Dokumente
CREATE TABLE dokumente (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    kunde_id UUID REFERENCES kunden(id),
    vorlage_id UUID REFERENCES vorlagen(id),
    name TEXT,
    pdf_url TEXT,                       -- Link zum PDF
    google_doc_url TEXT,                -- Temporäres Doc (wird gelöscht)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Kategorien für Vorlagen
CREATE TABLE kategorien (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    icon TEXT DEFAULT '📄',
    sortierung INTEGER DEFAULT 0
);

-- System-Status (für Wartungsmodus)
CREATE TABLE system_status (
    id INTEGER PRIMARY KEY DEFAULT 1,
    is_maintenance BOOLEAN DEFAULT false,
    maintenance_message TEXT,
    api_version TEXT DEFAULT '1.0',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Initial-Daten
INSERT INTO system_status (is_maintenance, api_version) VALUES (false, '1.0');

INSERT INTO kategorien (name, icon, sortierung) VALUES
    ('Mitgliedschaft', '👥', 1),
    ('Versammlungen', '🏛️', 2),
    ('Vorstand', '👔', 3),
    ('Finanzen', '💰', 4),
    ('Satzung', '📜', 5),
    ('Behörden', '🏢', 6),
    ('Sonstiges', '📋', 99);

-- Row Level Security (RLS) aktivieren
ALTER TABLE kunden ENABLE ROW LEVEL SECURITY;
ALTER TABLE vorlagen ENABLE ROW LEVEL SECURITY;
ALTER TABLE dokumente ENABLE ROW LEVEL SECURITY;

-- Policies: Kunden sehen nur ihre eigenen Daten
CREATE POLICY "Kunden sehen eigene Daten" ON kunden
    FOR SELECT USING (email = auth.jwt() ->> 'email');

CREATE POLICY "Kunden bearbeiten eigene Daten" ON kunden
    FOR UPDATE USING (email = auth.jwt() ->> 'email');

-- Vorlagen sind für alle sichtbar
CREATE POLICY "Vorlagen sind öffentlich" ON vorlagen
    FOR SELECT USING (is_active = true);

-- Dokumente: Nur eigene
CREATE POLICY "Eigene Dokumente sehen" ON dokumente
    FOR SELECT USING (kunde_id IN (SELECT id FROM kunden WHERE email = auth.jwt() ->> 'email'));

CREATE POLICY "Eigene Dokumente erstellen" ON dokumente
    FOR INSERT WITH CHECK (kunde_id IN (SELECT id FROM kunden WHERE email = auth.jwt() ->> 'email'));
```

### Schritt 3: Google OAuth aktivieren

1. Supabase → Authentication → Providers
2. Google aktivieren
3. Google Cloud Console:
   - Neues OAuth 2.0 Client erstellen
   - Redirect URI: `https://[DEIN-PROJEKT].supabase.co/auth/v1/callback`
4. Client ID und Secret in Supabase eintragen

### Schritt 4: Konfiguration

Erstelle `.streamlit/secrets.toml`:

```toml
[supabase]
url = "https://xyz.supabase.co"
key = "eyJ..."  # anon public key

[google]
# Für Docs API (PDF-Generierung)
client_secret_path = "config/client_secret.json"
```

---

## 📁 Projektstruktur

```
kunden_portal/
├── app.py                  # Haupt-App
├── pages/
│   ├── 1_📋_Stammdaten.py
│   ├── 2_📄_Vorlagen.py
│   └── 3_📜_Dokumente.py
├── utils/
│   ├── auth.py            # Google Login
│   ├── supabase_client.py # DB-Verbindung
│   ├── pdf_generator.py   # Dokument → PDF
│   └── maintenance.py     # Wartungsmodus-Check
├── .streamlit/
│   └── secrets.toml
├── requirements.txt
└── README.md
```

---

## 🔄 Sync vom Admin-Tool

Im Admin-Tool gibt es zwei neue Buttons:

### "☁️ Kunde freigeben"
- Lädt Kundendaten nach Supabase hoch
- Setzt `is_active = true`
- Kunde kann sich ab dann einloggen

### "🔄 Sync"
- Holt Änderungen vom Kunden zurück
- Aktualisiert lokale Datenbank

---

## 🛡️ Robustheit

### API-Versionierung
- Jede Anfrage prüft `system_status.api_version`
- Bei Mismatch → Fehlermeldung

### Wartungsmodus
- `system_status.is_maintenance = true`
- Zeigt Wartungsseite mit Message

### Fehlerbehandlung
- Alle API-Calls in try/catch
- Benutzerfreundliche Fehlermeldungen
- Logging für Debugging

---

## 🚀 Deployment

### Streamlit Cloud
1. GitHub Repository erstellen
2. https://streamlit.io/cloud
3. App deployen
4. Secrets konfigurieren

### Custom Domain (optional)
- `portal.deinverein.de` → Streamlit Cloud App

---

## 💰 Kosten

| Service | Free Tier | Für dich |
|---------|-----------|----------|
| Supabase | 50k reads/Monat, 500MB | ✅ Reicht |
| Streamlit Cloud | Unlimited | ✅ Kostenlos |
| Google APIs | Großzügig | ✅ Kostenlos |

**Gesamtkosten: 0€**
