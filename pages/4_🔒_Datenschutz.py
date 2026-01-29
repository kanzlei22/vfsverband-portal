"""
🔒 Datenschutzerklärung
Informationen zur Datenverarbeitung im Vereins-Portal
"""

import streamlit as st

st.set_page_config(
    page_title="Datenschutz | Vereins-Portal",
    page_icon="🔒",
    layout="wide"
)

# === SIDEBAR ===
with st.sidebar:
    st.markdown("### 🏛️ Vereins-Portal")
    st.caption("powered by Driver39")
    st.markdown("---")
    
    if st.button("← Zurück zur Startseite", use_container_width=True):
        st.switch_page("app.py")
    
    st.markdown("---")
    st.markdown("**Kontakt bei Fragen:**")
    st.markdown("[📱 WhatsApp](https://wa.me/4915678123456)")
    st.markdown("[✉️ E-Mail](mailto:datenschutz@driver39.de)")

# === HAUPTINHALT ===
st.title("🔒 Datenschutzerklärung")
st.caption("Stand: Januar 2026")

st.markdown("---")

st.markdown("""
## 1. Verantwortlicher

**Driver39**  
Robert Hoffmann  
[Adresse einfügen]  
E-Mail: datenschutz@driver39.de  
Web: www.driver39.de

---

## 2. Welche Daten werden verarbeitet?

Im Rahmen des Vereins-Portals werden folgende Daten verarbeitet:

### Stammdaten
- Name, Vorname
- E-Mail-Adresse
- Telefonnummer (falls angegeben)
- Anschrift

### Vereinsdaten
- Vereinsname
- Sitz des Vereins
- Vereinszweck
- Vorstandsmitglieder (Name, Funktion, Anschrift)
- Gründungsdaten

### Technische Daten
- IP-Adresse (anonymisiert)
- Login-Zeitpunkte
- Geräte-Informationen

---

## 3. Wo werden die Daten gespeichert?

Deine Daten werden sicher gespeichert bei:

### Supabase (Datenbank)
- **Anbieter:** Supabase Inc., San Francisco, USA
- **Serverstandort:** Frankfurt am Main, Deutschland (EU)
- **Zertifizierung:** SOC 2 Type II
- **Verschlüsselung:** AES-256 (at rest), TLS 1.3 (in transit)

### Google Cloud (Dokumenten-Generierung)
- **Anbieter:** Google Ireland Limited
- **Serverstandort:** EU (Belgien/Niederlande)
- **Zertifizierung:** ISO 27001, SOC 2/3

**Wichtig:** Alle Daten werden ausschließlich auf Servern innerhalb der Europäischen Union verarbeitet.

---

## 4. Zweck der Datenverarbeitung

Deine Daten werden verarbeitet für:

1. **Bereitstellung des Portals** - Damit du dich einloggen und deine Vereinsdaten verwalten kannst
2. **Dokumenten-Generierung** - Um personalisierte Vereinsdokumente (Satzung, Protokolle, etc.) zu erstellen
3. **Kommunikation** - Um dich über den Stand deiner Vereinsgründung zu informieren
4. **Service-Verbesserung** - Um das Portal stetig zu verbessern

---

## 5. Rechtsgrundlage

Die Verarbeitung erfolgt auf Basis von:

- **Art. 6 Abs. 1 lit. b DSGVO** - Vertragserfüllung (Dienstleistungsvertrag)
- **Art. 6 Abs. 1 lit. a DSGVO** - Einwilligung (bei optionalen Funktionen)
- **Art. 6 Abs. 1 lit. f DSGVO** - Berechtigtes Interesse (Sicherheit, Betrieb)

---

## 6. Speicherdauer

- **Aktive Kunden:** Daten werden gespeichert, solange du das Portal nutzt
- **Nach Vertragsende:** Löschung nach 3 Jahren (gesetzliche Aufbewahrungspflichten)
- **Auf Anfrage:** Sofortige Löschung möglich (siehe Rechte unten)

---

## 7. Deine Rechte

Du hast folgende Rechte bezüglich deiner Daten:

| Recht | Beschreibung |
|-------|-------------|
| **Auskunft** | Du kannst jederzeit erfahren, welche Daten wir über dich gespeichert haben |
| **Berichtigung** | Falsche Daten können korrigiert werden |
| **Löschung** | Du kannst die Löschung deiner Daten verlangen |
| **Einschränkung** | Du kannst die Verarbeitung einschränken lassen |
| **Datenübertragbarkeit** | Du kannst deine Daten in einem gängigen Format erhalten |
| **Widerspruch** | Du kannst der Verarbeitung widersprechen |

**Kontakt für Anfragen:**  
datenschutz@driver39.de

---

## 8. Cookies & Tracking

Das Portal verwendet **ausschließlich technisch notwendige Cookies**:

- **Session-Cookie** - Für deine Anmeldung (wird beim Schließen des Browsers gelöscht)
- **Keine Tracking-Cookies** - Wir verwenden kein Google Analytics oder ähnliches
- **Keine Werbung** - Es werden keine Werbe-Cookies gesetzt

---

## 9. Datensicherheit

Wir setzen folgende Sicherheitsmaßnahmen ein:

✅ SSL/TLS-Verschlüsselung für alle Verbindungen  
✅ Verschlüsselte Speicherung sensibler Daten  
✅ Regelmäßige Sicherheits-Updates  
✅ Zugriffskontrolle und Logging  
✅ Automatische Backups  

---

## 10. Änderungen dieser Erklärung

Diese Datenschutzerklärung kann bei Bedarf aktualisiert werden. Die aktuelle Version ist immer im Portal abrufbar. Bei wesentlichen Änderungen informieren wir dich per E-Mail.

---

## 11. Beschwerderecht

Du hast das Recht, dich bei einer Aufsichtsbehörde zu beschweren:

**Bayerisches Landesamt für Datenschutzaufsicht (BayLDA)**  
Promenade 18  
91522 Ansbach  
Web: www.lda.bayern.de

---

## Fragen?

Bei Fragen zum Datenschutz erreichst du uns unter:

📧 datenschutz@driver39.de  
📱 WhatsApp: [Nachricht schreiben](https://wa.me/4915678123456)

""")

st.markdown("---")

if st.button("← Zurück zur Startseite", use_container_width=True, type="primary"):
    st.switch_page("app.py")
