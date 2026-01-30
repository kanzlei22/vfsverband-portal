"""
Authentifizierung mit Google OAuth via streamlit-google-auth
"""

import streamlit as st
import json
import tempfile
import os
from utils.supabase_client import get_kunde_by_email

# Authenticator wird nur einmal pro App-Start erstellt
_authenticator = None


def _init_authenticator():
    """Initialisiert den Authenticator einmalig."""
    global _authenticator
    
    if _authenticator is not None:
        return _authenticator
    
    from streamlit_google_auth import Authenticate
    
    # Credentials aus Secrets in temp Datei schreiben
    credentials = {
        "web": {
            "client_id": st.secrets["google_oauth"]["client_id"],
            "client_secret": st.secrets["google_oauth"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [st.secrets.get("redirect_url", "https://vfsverband.streamlit.app")]
        }
    }
    
    temp_dir = tempfile.gettempdir()
    creds_path = os.path.join(temp_dir, "google_creds.json")
    
    with open(creds_path, "w") as f:
        json.dump(credentials, f)
    
    _authenticator = Authenticate(
        secret_credentials_path=creds_path,
        cookie_name="vereins_portal_auth",
        cookie_key=st.secrets.get("cookie_key", "vereins_portal_secret_key_2026"),
        redirect_uri=st.secrets.get("redirect_url", "https://vfsverband.streamlit.app"),
    )
    
    return _authenticator


def handle_auth():
    """
    Hauptfunktion für Auth-Handling. Rufe diese EINMAL pro Seite auf.
    Returns: (is_logged_in: bool, kunde: dict or None)
    """
    auth = _init_authenticator()
    auth.check_authentification()
    
    if st.session_state.get("connected"):
        email = st.session_state.get("user_info", {}).get("email", "").lower().strip()
        
        if email:
            st.session_state.user = {"email": email}
            kunde = get_kunde_by_email(email)
            st.session_state.kunde = kunde
            return True, kunde
    
    return False, None


def show_login():
    """Zeigt den Login-Button. Rufe NACH handle_auth() auf."""
    auth = _init_authenticator()
    
    st.markdown("""
    <style>
        .login-title { font-size: 2rem; margin-bottom: 1rem; text-align: center; }
        .login-subtitle { color: #666; margin-bottom: 2rem; text-align: center; }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<p class="login-title">🏛️ Vereins-Portal</p>', unsafe_allow_html=True)
        st.markdown('<p class="login-subtitle">Sichere Anmeldung mit Google</p>', unsafe_allow_html=True)
        auth.login()
        st.markdown("---")
        st.caption("Mit dem Login stimmst du unseren Nutzungsbedingungen zu.")


def get_current_user():
    """Gibt den aktuellen User zurück oder None."""
    return st.session_state.get("user")


def get_current_kunde():
    """Gibt den aktuellen Kunden zurück oder None."""
    return st.session_state.get("kunde")


def logout():
    """Loggt den User aus."""
    global _authenticator
    try:
        if _authenticator:
            _authenticator.logout()
    except:
        pass
    
    st.session_state.user = None
    st.session_state.kunde = None
    st.session_state.connected = False


def require_auth():
    """Für Unterseiten: Stellt sicher, dass User eingeloggt ist."""
    if not st.session_state.get("connected"):
        st.warning("⚠️ Bitte zuerst einloggen")
        st.switch_page("app.py")
        st.stop()
    
    if not st.session_state.get("kunde"):
        st.error("❌ Kein Zugang für diese E-Mail-Adresse")
        st.info("Deine E-Mail ist nicht für dieses Portal freigeschaltet.")
        st.stop()
    
    return st.session_state.kunde


# Legacy Funktionen für Kompatibilität
def login_page():
    """Legacy: Wird durch handle_auth() + show_login() ersetzt."""
    show_login()

def check_session():
    """Legacy: Wird durch handle_auth() ersetzt."""
    is_logged_in, _ = handle_auth()
    return is_logged_in

def check_auth():
    """Legacy: Wird durch handle_auth() ersetzt."""
    _, kunde = handle_auth()
    return kunde
