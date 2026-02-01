"""
Admin-Funktionen für das Portal
"""

import streamlit as st
import hashlib

# Admin-E-Mails (können in Secrets ausgelagert werden)
ADMIN_EMAILS = [
    "robert@driver39.de",
    "robert.hoffmann@driver39.de"
]

def check_admin_password(password: str) -> bool:
    """Prüft das Admin-Passwort."""
    # Passwort aus Secrets holen
    correct_password = st.secrets.get("admin_password", "UV2024!")
    return password == correct_password


def is_admin_logged_in() -> bool:
    """Prüft ob Admin eingeloggt ist."""
    return st.session_state.get("is_admin", False)


def admin_login():
    """Zeigt Admin-Login Dialog."""
    if is_admin_logged_in():
        return True
    
    st.markdown("### 🔐 Admin-Bereich")
    st.info("Dieser Bereich ist nur für Administratoren zugänglich.")
    
    with st.form("admin_login"):
        password = st.text_input("Admin-Passwort", type="password")
        submitted = st.form_submit_button("Anmelden", use_container_width=True)
        
        if submitted:
            if check_admin_password(password):
                st.session_state["is_admin"] = True
                st.success("✅ Erfolgreich angemeldet!")
                st.rerun()
            else:
                st.error("❌ Falsches Passwort!")
    
    return False


def admin_logout():
    """Loggt Admin aus."""
    if "is_admin" in st.session_state:
        del st.session_state["is_admin"]


def require_admin(func):
    """Decorator für Admin-geschützte Funktionen."""
    def wrapper(*args, **kwargs):
        if not is_admin_logged_in():
            admin_login()
            return None
        return func(*args, **kwargs)
    return wrapper


def show_admin_header():
    """Zeigt Admin-Header mit Logout-Button."""
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("### 👑 Admin-Bereich")
    with col2:
        if st.button("🚪 Abmelden", use_container_width=True):
            admin_logout()
            st.rerun()
