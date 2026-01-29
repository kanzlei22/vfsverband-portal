"""
📜 Meine Dokumente - Übersicht aller generierten Dokumente
Mit Löschen und Umbenennen Funktionen
"""

import streamlit as st
from utils.auth import require_auth
from utils.supabase_client import get_meine_dokumente, delete_dokument, rename_dokument
from datetime import datetime

st.set_page_config(page_title="Meine Dokumente", page_icon="📜", layout="wide")

# Auth Check
kunde = require_auth()

st.header("📜 Meine Dokumente")
st.caption("Übersicht deiner erstellten Dokumente")

# === DOKUMENTE LADEN ===
dokumente = get_meine_dokumente(kunde["id"])

if not dokumente:
    st.info("""
    Du hast noch keine Dokumente erstellt.
    
    👉 Gehe zu **Vorlagen** um dein erstes Dokument zu erstellen.
    """)
    
    if st.button("📄 Zu den Vorlagen", type="primary"):
        st.switch_page("pages/2_📄_Vorlagen.py")
    
    st.stop()

# === STATISTIK ===
col1, col2 = st.columns([1, 3])
with col1:
    st.metric("Anzahl Dokumente", len(dokumente))
with col2:
    if st.button("🔄 Aktualisieren"):
        st.rerun()

st.markdown("---")

# === DOKUMENTE ANZEIGEN ===
for doc in dokumente:
    doc_id = doc.get("id")
    
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns([4, 2, 1, 1])
        
        with col1:
            # Name (editierbar wenn im Edit-Modus)
            if st.session_state.get(f"editing_{doc_id}"):
                new_name = st.text_input(
                    "Name",
                    value=doc.get("name", ""),
                    key=f"name_input_{doc_id}",
                    label_visibility="collapsed"
                )
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("💾 Speichern", key=f"save_{doc_id}"):
                        success, error = rename_dokument(doc_id, new_name)
                        if success:
                            st.success("Gespeichert!")
                            del st.session_state[f"editing_{doc_id}"]
                            st.rerun()
                        else:
                            st.error(f"Fehler: {error}")
                with c2:
                    if st.button("❌ Abbrechen", key=f"cancel_{doc_id}"):
                        del st.session_state[f"editing_{doc_id}"]
                        st.rerun()
            else:
                st.markdown(f"**📄 {doc.get('name', 'Unbenannt')}**")
                
                # Vorlage-Info
                if doc.get("vorlagen"):
                    vorlage_info = doc["vorlagen"]
                    st.caption(f"Vorlage: {vorlage_info.get('name', '')} | {vorlage_info.get('kategorie', '')}")
        
        with col2:
            # Datum formatieren (UTC → deutsche Zeit)
            created = doc.get("created_at", "")
            if created:
                try:
                    from datetime import timedelta
                    dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    # UTC+1 (bzw. UTC+2 bei Sommerzeit)
                    dt_local = dt + timedelta(hours=1)
                    formatted_date = dt_local.strftime("%d.%m.%Y %H:%M")
                except:
                    formatted_date = created[:16]
                st.caption(f"📅 {formatted_date}")
        
        with col3:
            # Umbenennen Button
            if not st.session_state.get(f"editing_{doc_id}"):
                if st.button("✏️", key=f"edit_{doc_id}", help="Umbenennen"):
                    st.session_state[f"editing_{doc_id}"] = True
                    st.rerun()
        
        with col4:
            # Löschen Button
            if not st.session_state.get(f"editing_{doc_id}"):
                if st.button("🗑️", key=f"delete_{doc_id}", help="Löschen"):
                    st.session_state[f"confirm_delete_{doc_id}"] = True
                    st.rerun()
        
        # Löschen-Bestätigung
        if st.session_state.get(f"confirm_delete_{doc_id}"):
            st.warning(f"Möchtest du **{doc.get('name', 'dieses Dokument')}** wirklich löschen?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Ja, löschen", key=f"confirm_yes_{doc_id}", type="primary"):
                    success, error = delete_dokument(doc_id)
                    if success:
                        st.success("Gelöscht!")
                        del st.session_state[f"confirm_delete_{doc_id}"]
                        st.rerun()
                    else:
                        st.error(f"Fehler: {error}")
            with c2:
                if st.button("❌ Abbrechen", key=f"confirm_no_{doc_id}"):
                    del st.session_state[f"confirm_delete_{doc_id}"]
                    st.rerun()
        
        # Download-Link (falls vorhanden)
        if doc.get("pdf_url") and not st.session_state.get(f"editing_{doc_id}") and not st.session_state.get(f"confirm_delete_{doc_id}"):
            st.link_button("⬇️ PDF herunterladen", doc["pdf_url"], use_container_width=True, type="primary")

# === HINWEIS ===
st.markdown("---")
st.info("""
💡 **Hinweis:** Dokumente die direkt heruntergeladen wurden erscheinen hier in der Historie. 
Du findest die PDF-Dateien in deinem Downloads-Ordner.
""")

# === FOOTER ===
st.markdown("---")
if st.button("📄 Neues Dokument erstellen", use_container_width=True, type="primary"):
    st.switch_page("pages/2_📄_Vorlagen.py")
