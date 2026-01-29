"""
📋 Stammdaten - Kunden können ihre Daten einsehen und bearbeiten
"""

import streamlit as st
from utils.auth import require_auth
from utils.supabase_client import update_kunde_data

st.set_page_config(page_title="Stammdaten", page_icon="📋", layout="wide")

# Auth Check
kunde = require_auth()

st.header("📋 Stammdaten")
st.caption(f"Kunde: {kunde.get('name', '')}")

# Stammdaten laden
sheet_data = kunde.get("sheet_data", {}) or {}

# === VORDEFINIERTE FELDER ===
# Links: Feldname aus Forms/Stammdaten | Rechts: Label für Anzeige | Typ
# Die Platzhalter-Zuordnung erfolgt im PDF-Generator
REQUIRED_FIELDS = {
    "🏢 Vereinsdaten": [
        ("Vereinsname (Ihre Idee)", "Vereinsname", "text"),
        ("Sitz des Vereins", "Sitz", "text"),
        ("Anschrift des Vereins", "Anschrift des Vereins", "textarea"),
        ("Vereinszweck (Ihre Grundidee)", "Vereinszweck (Grundidee)", "textarea"),
    ],
    "📝 KI-generierte Texte": [
        ("vereinsname", "Vereinsname (final)", "text"),
        ("claim", "Claim / Leitspruch", "textarea"),
        ("verwirklichung", "Verwirklichung des Vereinszwecks", "textarea"),
        ("Vorbemerkung", "Vorbemerkung zur Satzung", "textarea"),
        ("gründungsprotokoll_idee", "Text Gründungsprotokoll", "textarea"),
        ("gericht_anschreiben_zweck", "Text Gerichtsanschreiben", "textarea"),
    ],
    "📅 Gründung": [
        ("Gründungsort", "Gründungsort", "text"),
        ("Gründungsdatum", "Gründungsdatum", "text"),
        ("Gründungszeit", "Gründungszeit", "text"),
    ],
    "👤 Gründer (1. Vorsitzender)": [
        ("Name Gründer", "Name", "text"),
        ("Anschrift Gründer", "Anschrift", "textarea"),
        ("Geburtsdatum Gründer", "Geburtsdatum", "text"),
        ("Geburtsort Gründer", "Geburtsort", "text"),
    ],
    "👥 Mitglied 2": [
        ("Name Mitglied 2", "Name", "text"),
        ("Anschrift Mitglied 2", "Anschrift", "textarea"),
    ],
    "👥 Mitglied 3": [
        ("Name Mitglied 3", "Name", "text"),
        ("Anschrift Mitglied 3", "Anschrift", "textarea"),
    ],
    "👥 Mitglied 4": [
        ("Name Mitglied 4", "Name", "text"),
        ("Anschrift Mitglied 4", "Anschrift", "textarea"),
    ],
    "👥 Mitglied 5": [
        ("Name Mitglied 5", "Name", "text"),
        ("Anschrift Mitglied 5", "Anschrift", "textarea"),
    ],
    "👥 Mitglied 6": [
        ("Name Mitglied 6", "Name", "text"),
        ("Anschrift Mitglied 6", "Anschrift", "textarea"),
    ],
    "👥 Mitglied 7": [
        ("Name Mitglied 7", "Name", "text"),
        ("Anschrift Mitglied 7", "Anschrift", "textarea"),
    ],
    "📝 Protokoll": [
        ("Protokollführer", "Protokollführer", "text"),
    ],
    "⚖️ Gericht": [
        ("Amtsgericht", "Amtsgericht", "text"),
        ("Amtsgericht Anschrift", "Anschrift", "textarea"),
    ],
    "📜 Notar": [
        ("Notar", "Notar", "text"),
        ("Notar Anschrift 1", "Anschrift Zeile 1", "text"),
        ("Notar Anschrift 2", "Anschrift Zeile 2", "text"),
    ],
}

# === BEARBEITUNGSMODUS ===
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

col1, col2 = st.columns([4, 1])
with col2:
    if st.button("✏️ Bearbeiten" if not st.session_state.edit_mode else "❌ Abbrechen", use_container_width=True):
        st.session_state.edit_mode = not st.session_state.edit_mode
        st.rerun()

# === FORTSCHRITT ANZEIGEN ===
total_fields = sum(len(fields) for fields in REQUIRED_FIELDS.values())
filled_fields = sum(1 for fields in REQUIRED_FIELDS.values() for key, _, _ in fields if sheet_data.get(key))
progress = filled_fields / total_fields if total_fields > 0 else 0

st.progress(progress, text=f"Ausgefüllt: {filled_fields} von {total_fields} Feldern ({int(progress*100)}%)")

# === DATEN ANZEIGEN / BEARBEITEN ===
edited_data = {}

for category, fields in REQUIRED_FIELDS.items():
    # Prüfen wie viele Felder in dieser Kategorie ausgefüllt sind
    cat_filled = sum(1 for key, _, _ in fields if sheet_data.get(key))
    cat_total = len(fields)
    
    with st.expander(f"{category} ({cat_filled}/{cat_total})", expanded=st.session_state.edit_mode):
        for key, label, field_type in fields:
            current_value = sheet_data.get(key, "")
            
            if st.session_state.edit_mode:
                # Bearbeitbar
                if field_type == "textarea":
                    new_value = st.text_area(
                        label, 
                        value=str(current_value) if current_value else "",
                        key=f"edit_{key}",
                        height=120,
                        placeholder=f"{label} eingeben..."
                    )
                else:
                    new_value = st.text_input(
                        label, 
                        value=str(current_value) if current_value else "",
                        key=f"edit_{key}",
                        placeholder=f"{label} eingeben..."
                    )
                edited_data[key] = new_value
            else:
                # Nur Anzeige
                st.markdown(f"**{label}**")
                if current_value:
                    if field_type == "textarea":
                        st.text(str(current_value))
                    else:
                        st.write(str(current_value))
                else:
                    st.caption("— nicht ausgefüllt —")

# === ZUSÄTZLICHE FELDER (aus Sync) ===
# Felder die nicht in REQUIRED_FIELDS sind aber in sheet_data existieren
known_keys = {key for fields in REQUIRED_FIELDS.values() for key, _, _ in fields}
extra_fields = {k: v for k, v in sheet_data.items() if k not in known_keys and v}

if extra_fields:
    with st.expander(f"📋 Weitere Felder ({len(extra_fields)})", expanded=False):
        for key, value in extra_fields.items():
            if st.session_state.edit_mode:
                new_value = st.text_input(key, value=str(value) if value else "", key=f"edit_extra_{key}")
                edited_data[key] = new_value
            else:
                st.markdown(f"**{key}**")
                st.write(str(value) if value else "—")

# === SPEICHERN ===
if st.session_state.edit_mode:
    st.divider()
    
    if st.button("💾 Änderungen speichern", type="primary", use_container_width=True):
        # Alle Felder zusammenführen
        final_data = {**sheet_data}
        for key, value in edited_data.items():
            if value:  # Nur nicht-leere Werte speichern
                final_data[key] = value
            elif key in final_data and not value:
                # Leere Werte entfernen wenn sie vorher da waren
                pass  # Behalten falls gewünscht
        
        # In Supabase speichern
        success, error = update_kunde_data(kunde["id"], final_data)
        
        if success:
            st.session_state.kunde["sheet_data"] = final_data
            st.session_state.edit_mode = False
            st.success("✅ Änderungen gespeichert!")
            st.rerun()
        else:
            st.error(f"❌ Fehler beim Speichern: {error}")

# === HINWEIS ===
st.markdown("---")
st.info("""
💡 **Hinweis:** Fülle alle Felder aus, die du für deine Dokumente benötigst.
Die Daten werden automatisch in deine generierten PDFs eingesetzt.
""")

