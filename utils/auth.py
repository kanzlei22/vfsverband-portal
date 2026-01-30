"""
Authentifizierung mit Google OAuth via streamlit-google-auth
"""

import streamlit as st
import json
import tempfile
import os
from streamlit_google_auth import Authenticate
from utils.supabase_client import get_kunde_by_email


def get_authenticator():
    """Erstellt den Google Authenticator."""
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
    
    # Temp-Datei erstellen
    temp_dir = tempfile.gettempdir()
    creds_path = os.path.join(temp_dir, "google_creds.json")
    
    with open(creds_path, "w") as f:
        json.dump(credentials, f)
    
    return Authenticate(
        secret_credentials_path=creds_path,
        cookie_name="vereins_portal_auth",
        cookie_key=st.secrets.get("cookie_key", "vereins_portal_secret_key_2026"),
        redirect_uri=st.secrets.get("redirect_url", "https://vfsverband.streamlit.app"),
    )


def login_page():
    """Zeigt die Login-Seite an."""
    st.markdown("""
    <style>
        .login-title {
            font-size: 2rem;
            margin-bottom: 1rem;
            text-align: center;
        }
        .login-subtitle {
            color: #666;
            margin-bottom: 2rem;
            text-align: center;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<p class="login-title">🏛️ Vereins-Portal</p>', unsafe_allow_html=True)
        st.markdown('<p class="login-subtitle">Sichere Anmeldung mit Google</p>', unsafe_allow_html=True)
        
        # Google Login
        authenticator = get_authenticator()
        authenticator.check_authentification()
        
        # Login Button anzeigen
        authenticator.login()


def check_auth():
    """
    Prüft Authentifizierung und gibt Kunde zurück.
    Returns: kunde dict oder None
    """
    authenticator = get_authenticator()
    authenticator.check_authentification()
    
    if st.session_state.get("connected"):
        email = st.session_state.get("user_info", {}).get("email", "").lower().strip()
        
        if email:
            # User in Session speichern
            st.session_state.user = {"email": email}
            
            # Kunde in Datenbank suchen
            kunde = get_kunde_by_email(email)
            
            if kunde:
                st.session_state.kunde = kunde
                return kunde
            else:
                st.session_state.kunde = None
                return None
    
    return None


def get_current_user():
    """Gibt den aktuellen User zurück oder None."""
    return st.session_state.get("user")


def get_current_kunde():
    """Gibt den aktuellen Kunden zurück oder None."""
    return st.session_state.get("kunde")


def logout():
    """Loggt den User aus."""
    try:
        authenticator = get_authenticator()
        authenticator.logout()
    except:
        pass
    
    st.session_state.user = None
    st.session_state.kunde = None
    st.session_state.connected = False


def require_auth():
    """Stellt sicher, dass User eingeloggt ist."""
    if not st.session_state.get("connected"):
        st.warning("⚠️ Bitte zuerst einloggen")
        st.switch_page("app.py")
        st.stop()
    
    if not st.session_state.get("kunde"):
        st.error("❌ Kein Zugang für diese E-Mail-Adresse")
        st.info("Deine E-Mail ist nicht für dieses Portal freigeschaltet. Kontaktiere deinen Berater.")
        st.stop()
    
    return st.session_state.kunde


def check_session():
    """Prüft ob eine gültige Session existiert."""
    return check_auth() is not None
