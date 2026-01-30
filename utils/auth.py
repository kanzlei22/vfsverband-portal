"""
Authentifizierung mit Google OAuth - eigene Implementierung
Ohne externe Libraries, browserunabhängig
"""

import streamlit as st
import requests
from urllib.parse import urlencode
from utils.supabase_client import get_kunde_by_email

# Google OAuth Endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def get_oauth_config():
    """Holt OAuth Konfiguration aus Secrets."""
    return {
        "client_id": st.secrets["google_oauth"]["client_id"],
        "client_secret": st.secrets["google_oauth"]["client_secret"],
        "redirect_uri": st.secrets.get("redirect_url", "https://vfsverband.streamlit.app"),
    }


def get_google_auth_url():
    """Generiert die Google OAuth URL."""
    config = get_oauth_config()
    
    params = {
        "client_id": config["client_id"],
        "redirect_uri": config["redirect_uri"],
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_token(code: str):
    """Tauscht den Auth-Code gegen ein Access Token."""
    config = get_oauth_config()
    
    data = {
        "client_id": config["client_id"],
        "client_secret": config["client_secret"],
        "code": code,
        "grant_type": "authorization_code",
        "redirect_uri": config["redirect_uri"],
    }
    
    response = requests.post(GOOGLE_TOKEN_URL, data=data)
    
    if response.status_code == 200:
        return response.json()
    else:
        return None


def get_user_info(access_token: str):
    """Holt User-Info von Google."""
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(GOOGLE_USERINFO_URL, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    return None


def handle_auth():
    """
    Hauptfunktion für Auth-Handling.
    Returns: (is_logged_in: bool, kunde: dict or None)
    """
    # Bereits eingeloggt?
    if st.session_state.get("user") and st.session_state.get("kunde"):
        return True, st.session_state.kunde
    
    # Prüfe ob OAuth Code in URL
    params = st.query_params
    code = params.get("code")
    
    if code:
        # Code gegen Token tauschen
        token_data = exchange_code_for_token(code)
        
        if token_data and "access_token" in token_data:
            # User-Info holen
            user_info = get_user_info(token_data["access_token"])
            
            if user_info and "email" in user_info:
                email = user_info["email"].lower().strip()
                
                # In Session speichern
                st.session_state.user = {"email": email, "name": user_info.get("name", "")}
                
                # Kunde in Datenbank suchen
                kunde = get_kunde_by_email(email)
                st.session_state.kunde = kunde
                
                # Code aus URL entfernen
                st.query_params.clear()
                
                return True, kunde
        
        # Fehler - Code ungültig
        st.query_params.clear()
        st.error("Login fehlgeschlagen. Bitte erneut versuchen.")
    
    return False, None


def show_login():
    """Zeigt die Login-Seite."""
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
        
        # Google Login Button
        auth_url = get_google_auth_url()
        
        st.markdown(f'''
            <a href="{auth_url}" target="_top" style="
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 100%;
                padding: 12px 24px;
                background-color: #4285f4;
                color: white;
                text-decoration: none;
                border-radius: 4px;
                font-size: 16px;
                font-weight: 500;
                gap: 10px;
            ">
                <img src="https://www.google.com/favicon.ico" width="20" height="20">
                Mit Google anmelden
            </a>
        ''', unsafe_allow_html=True)
        
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
    st.session_state.user = None
    st.session_state.kunde = None


def require_auth():
    """Für Unterseiten: Stellt sicher, dass User eingeloggt ist."""
    if not st.session_state.get("user"):
        st.warning("⚠️ Bitte zuerst einloggen")
        st.switch_page("app.py")
        st.stop()
    
    if not st.session_state.get("kunde"):
        st.error("❌ Kein Zugang für diese E-Mail-Adresse")
        st.info("Deine E-Mail ist nicht für dieses Portal freigeschaltet.")
        st.stop()
    
    return st.session_state.kunde


# Legacy Funktionen
def check_session():
    is_logged_in, _ = handle_auth()
    return is_logged_in

def check_auth():
    _, kunde = handle_auth()
    return kunde

def login_page():
    show_login()
