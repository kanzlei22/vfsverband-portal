"""
🏛️ Vereins-Generator: Kunden-Portal
Hauptanwendung
"""

import streamlit as st
from utils.supabase_client import get_supabase, check_maintenance
from utils.auth import login_page, get_current_user, logout, check_session
from utils.config import (
    WHATSAPP_LINK, CALENDLY_LINK, BERATUNG_LINK, 
    IMPRESSUM_LINK, COMPANY_NAME, WEBSITE
)

# === PAGE CONFIG ===
st.set_page_config(
    page_title=f"Vereins-Portal | {COMPANY_NAME}",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# === WARTUNGSMODUS CHECK ===
is_maintenance, maintenance_msg = check_maintenance()
if is_maintenance:
    st.error("🔧 Wartungsmodus")
    st.warning(maintenance_msg or "Das Portal wird gerade gewartet. Bitte versuche es später erneut.")
    st.stop()

# === CUSTOM CSS ===
st.markdown("""
<style>
    /* Allgemein */
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.3rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 1.5rem;
    }
    
    /* Info-Karten */
    .info-card {
        background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 1rem;
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
        transition: transform 0.2s;
    }
    .info-card:hover {
        transform: translateY(-2px);
    }
    .info-card h3 {
        margin: 0 0 0.5rem 0;
        font-size: 1.3rem;
    }
    .info-card p {
        margin: 0;
        opacity: 0.9;
        font-size: 0.95rem;
    }
    
    /* Footer */
    .footer {
        margin-top: 3rem;
        padding: 2rem 0;
        border-top: 1px solid #e5e7eb;
        text-align: center;
        color: #6b7280;
        font-size: 0.9rem;
    }
    .footer a {
        color: #4f46e5;
        text-decoration: none;
    }
    .footer a:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

# === SESSION STATE ===
if "user" not in st.session_state:
    st.session_state.user = None
if "kunde" not in st.session_state:
    st.session_state.kunde = None

# === OAuth Callback prüfen ===
if not st.session_state.user:
    check_session()


def render_sidebar():
    """Rendert die Sidebar mit Login und Kontakt."""
    with st.sidebar:
        # Logo/Titel
        st.markdown("### 🏛️ Vereins-Portal")
        st.caption(f"powered by {COMPANY_NAME}")
        st.markdown("---")
        
        if st.session_state.user:
            st.success(f"✅ Eingeloggt als:\n{st.session_state.user['email']}")
            if st.button("🚪 Ausloggen", use_container_width=True):
                logout()
                st.rerun()
        else:
            st.info("Bitte einloggen")
        
        st.markdown("---")
        
        # Kontakt-Box in Sidebar
        st.markdown("### 💬 Hilfe & Kontakt")
        
        st.link_button("📱 WhatsApp", WHATSAPP_LINK, use_container_width=True)
        st.link_button("📅 Termin buchen", CALENDLY_LINK, use_container_width=True)
        st.link_button("💼 Beratung", BERATUNG_LINK, use_container_width=True)
        
        st.markdown("---")
        
        # Footer-Links in Sidebar
        st.page_link("pages/4_🔒_Datenschutz.py", label="🔒 Datenschutz", use_container_width=True)
        st.markdown(f"[Impressum]({IMPRESSUM_LINK})")
        st.caption(f"© 2026 {COMPANY_NAME}")


def render_footer():
    """Rendert den Footer mit Kontakt und Links."""
    st.markdown("---")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**💬 Kontakt**")
        st.markdown(f"[📱 WhatsApp Business]({WHATSAPP_LINK})")
        st.markdown(f"[📅 Kostenloses Erstgespräch]({CALENDLY_LINK})")
        st.markdown(f"[💼 Beratung buchen]({BERATUNG_LINK})")
    
    with col2:
        st.markdown("**📋 Rechtliches**")
        st.page_link("pages/4_🔒_Datenschutz.py", label="🔒 Datenschutzerklärung")
        st.markdown(f"[📄 Impressum]({IMPRESSUM_LINK})")
    
    with col3:
        st.markdown("**ℹ️ Über uns**")
        st.markdown(f"{COMPANY_NAME} - Dein Partner für Vereinsgründungen")
        st.markdown(f"[🌐 {WEBSITE.replace('https://', '')}]({WEBSITE})")
    
    st.markdown(f"""
    <div class="footer">
        <p>© 2026 {COMPANY_NAME} | Alle Rechte vorbehalten</p>
        <p>Bei Fragen erreichst du uns jederzeit per WhatsApp oder E-Mail.</p>
    </div>
    """, unsafe_allow_html=True)


def main():
    # Sidebar rendern
    render_sidebar()
    
    # Nicht eingeloggt → Login-Seite
    if not st.session_state.user:
        login_page()
        render_footer()
        return
    
    # Eingeloggt aber kein Kunde gefunden
    if not st.session_state.kunde:
        st.error("❌ Kein Zugang")
        st.warning("""
        Deine E-Mail-Adresse ist nicht für dieses Portal freigeschaltet.
        
        **Mögliche Gründe:**
        - Dein Verein wurde noch nicht freigeschaltet
        - Die E-Mail-Adresse stimmt nicht mit der hinterlegten überein
        
        Bei Fragen kontaktiere uns gerne!
        """)
        
        col1, col2 = st.columns(2)
        with col1:
            st.link_button("📱 WhatsApp schreiben", WHATSAPP_LINK, use_container_width=True, type="primary")
        with col2:
            if st.button("🔄 Erneut prüfen", use_container_width=True):
                st.rerun()
        
        render_footer()
        return
    
    # === HAUPTSEITE ===
    kunde = st.session_state.kunde
    
    # Header
    st.markdown(f'<p class="main-header">🏛️ Willkommen, {kunde.get("name", "")}</p>', unsafe_allow_html=True)
    
    vereinsname = kunde.get("vereinsname") or kunde.get("sheet_data", {}).get("vereinsname", "Dein Verein")
    st.markdown(f'<p class="sub-header">{vereinsname}</p>', unsafe_allow_html=True)
    
    # Info-Karten
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="info-card">
            <h3>📋 Stammdaten</h3>
            <p>Deine Vereinsdaten einsehen und bearbeiten</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("→ Zu den Stammdaten", key="btn_stammdaten", use_container_width=True):
            st.switch_page("pages/1_📋_Stammdaten.py")
    
    with col2:
        st.markdown("""
        <div class="info-card">
            <h3>📄 Vorlagen</h3>
            <p>Dokumente aus Vorlagen erstellen</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("→ Zu den Vorlagen", key="btn_vorlagen", use_container_width=True):
            st.switch_page("pages/2_📄_Vorlagen.py")
    
    with col3:
        st.markdown("""
        <div class="info-card">
            <h3>📜 Meine Dokumente</h3>
            <p>Erstellte Dokumente herunterladen</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("→ Zu meinen Dokumenten", key="btn_dokumente", use_container_width=True):
            st.switch_page("pages/3_📜_Dokumente.py")
    
    # Quick-Stats
    st.markdown("---")
    st.subheader("📊 Übersicht")
    
    try:
        supabase = get_supabase()
        doc_count = supabase.table("dokumente").select("id", count="exact").eq("kunde_id", kunde["id"]).execute()
        doc_num = doc_count.count or 0
    except:
        doc_num = 0
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Erstellte Dokumente", doc_num)
    with col2:
        st.metric("Status", "✅ Aktiv" if kunde.get("is_active") else "⏳ Ausstehend")
    with col3:
        synced = kunde.get("synced_at", "")[:10] if kunde.get("synced_at") else "—"
        st.metric("Letzte Synchronisation", synced)
    
    # Hinweis-Box
    st.markdown("---")
    st.info("""
    💡 **Tipp:** Halte deine Stammdaten aktuell! Änderungen werden automatisch 
    mit deinem Berater synchronisiert.
    """)
    
    # Footer
    render_footer()


if __name__ == "__main__":
    main()
