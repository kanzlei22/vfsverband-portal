"""
📄 Vorlagen - Dokumente aus Vorlagen generieren
"""

import streamlit as st
from utils.auth import require_auth
from utils.supabase_client import get_kategorien, get_vorlagen, get_vorlage_by_id, save_dokument
from utils.pdf_generator import generate_pdf_from_template
from datetime import datetime

st.set_page_config(page_title="Vorlagen", page_icon="📄", layout="wide")

# Auth Check
kunde = require_auth()

st.header("📄 Vorlagen-Katalog")
st.caption("Wähle eine Vorlage um ein Dokument zu erstellen")

# === KATEGORIEN LADEN ===
kategorien = get_kategorien()

if not kategorien:
    st.warning("Keine Kategorien verfügbar.")
    st.info("Der Administrator muss zuerst Vorlagen synchronisieren.")
    st.stop()

# === VORLAGEN PRO KATEGORIE ZÄHLEN ===
alle_vorlagen = get_vorlagen()
vorlagen_count = {}
for v in alle_vorlagen:
    cat = v.get("kategorie", "Sonstiges")
    vorlagen_count[cat] = vorlagen_count.get(cat, 0) + 1

# === KATEGORIE AUSWÄHLEN ===
kategorie_options = []
for k in kategorien:
    name = k["name"]
    count = vorlagen_count.get(name, 0)
    icon = k.get("icon", "📄")
    kategorie_options.append({
        "name": name,
        "display": f"{icon} {name} ({count})",
        "count": count
    })

# Nur Kategorien mit Vorlagen anzeigen
kategorie_options = [k for k in kategorie_options if k["count"] > 0]

if not kategorie_options:
    st.warning("Keine Vorlagen verfügbar.")
    st.stop()

selected_display = st.selectbox(
    "Kategorie wählen",
    options=[k["display"] for k in kategorie_options]
)

# Name extrahieren
selected_kategorie = next(
    (k["name"] for k in kategorie_options if k["display"] == selected_display), 
    None
)

# === VORLAGEN LADEN ===
vorlagen = get_vorlagen(kategorie=selected_kategorie)

if not vorlagen:
    st.info(f"Keine Vorlagen in der Kategorie '{selected_kategorie}' verfügbar.")
    st.stop()

# === VORLAGEN ANZEIGEN ===
st.markdown("---")
st.subheader(f"Vorlagen ({len(vorlagen)})")

for vorlage in vorlagen:
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"**{vorlage['name']}**")
            if vorlage.get("beschreibung"):
                st.caption(vorlage["beschreibung"])
        
        with col2:
            if st.button("📄 PDF erstellen", key=f"gen_{vorlage['id']}", use_container_width=True):
                st.session_state.selected_vorlage = vorlage["id"]

# === PDF GENERIERUNG ===
if "selected_vorlage" in st.session_state:
    vorlage = get_vorlage_by_id(st.session_state.selected_vorlage)
    
    if vorlage:
        st.markdown("---")
        st.subheader(f"📄 {vorlage['name']} erstellen")
        
        with st.form("generate_form"):
            st.info(f"""
            **Vorlage:** {vorlage['name']}
            
            Das Dokument wird mit deinen aktuellen Stammdaten erstellt.
            """)
            
            zusatz = st.text_input(
                "Zusatz im Dateinamen (optional)", 
                placeholder="z.B. 2024 oder Entwurf"
            )
            
            submitted = st.form_submit_button("🚀 PDF jetzt erstellen", type="primary")
            
            if submitted:
                with st.spinner("PDF wird erstellt..."):
                    sheet_data = kunde.get("sheet_data", {})
                    
                    timestamp = datetime.now().strftime("%Y%m%d")
                    filename = f"{vorlage['name']}_{kunde['name']}"
                    if zusatz:
                        filename += f"_{zusatz}"
                    filename += f"_{timestamp}.pdf"
                    
                    pdf_bytes, error = generate_pdf_from_template(
                        template_id=vorlage["google_doc_id"],
                        sheet_data=sheet_data,
                        output_name=filename
                    )
                    
                    if error:
                        st.session_state.pdf_error = error
                    elif pdf_bytes:
                        st.session_state.pdf_bytes = pdf_bytes
                        st.session_state.pdf_filename = filename
                        
                        # In Datenbank speichern (mit PDF in Storage)
                        save_dokument(
                            kunde_id=kunde["id"],
                            vorlage_id=vorlage["id"],
                            name=filename,
                            pdf_url=None,
                            pdf_bytes=pdf_bytes
                        )
        
        # Download außerhalb des Forms
        if "pdf_error" in st.session_state:
            st.error(f"❌ Fehler: {st.session_state.pdf_error}")
            del st.session_state.pdf_error
        
        if "pdf_bytes" in st.session_state:
            st.success("✅ PDF erfolgreich erstellt!")
            st.download_button(
                label="⬇️ PDF herunterladen",
                data=st.session_state.pdf_bytes,
                file_name=st.session_state.pdf_filename,
                mime="application/pdf",
                type="primary",
                use_container_width=True
            )
            if st.button("🔄 Weitere PDF erstellen"):
                del st.session_state.pdf_bytes
                del st.session_state.pdf_filename
                del st.session_state.selected_vorlage
                st.rerun()
        
        if st.button("❌ Abbrechen") and "pdf_bytes" not in st.session_state:
            del st.session_state.selected_vorlage
            st.rerun()

# === HINWEIS ===
st.markdown("---")
st.info("""
💡 **Hinweis:** Die Dokumente werden mit deinen aktuellen Stammdaten erstellt.
Prüfe vorher unter "Stammdaten" ob alle Angaben korrekt sind.
""")
