"""
Admin-Funktionen für das Portal
Prüft Admin-Berechtigung über Google E-Mail
"""

import streamlit as st


def get_admin_emails():
    """Holt die Liste der Admin-E-Mails aus Secrets."""
    return [e.lower() for e in st.secrets.get("admin_emails", [])]


def get_current_user_email():
    """Gibt die E-Mail des eingeloggten Users zurück."""
    if st.session_state.get("user"):
        return st.session_state.user.get("email", "").lower()
    return ""


def is_admin():
    """Prüft ob der eingeloggte User Admin ist."""
    user_email = get_current_user_email()
    admin_emails = get_admin_emails()
    return user_email in admin_emails


def require_admin():
    """
    Prüft Admin-Berechtigung.
    Stoppt die Seite wenn nicht Admin.
    """
    if not is_admin():
        st.error("⛔ Zugriff verweigert")
        st.warning("Diese Seite ist nur für Administratoren zugänglich.")
        st.info(f"Eingeloggt als: {get_current_user_email() or 'Nicht eingeloggt'}")
        if st.button("← Zur Startseite"):
            st.switch_page("app.py")
        st.stop()
