"""
Authentifizierung mit Google OAuth via Supabase
"""

import streamlit as st
from utils.supabase_client import get_supabase, get_kunde_by_email

# OAuth Konfiguration
GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile"
]


def login_page():
    """Zeigt die Login-Seite an."""
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 2rem;
            text-align: center;
        }
        .login-title {
            font-size: 2rem;
            margin-bottom: 1rem;
        }
        .login-subtitle {
            color: #666;
            margin-bottom: 2rem;
        }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<p class="login-title">🏛️ Vereins-Portal</p>', unsafe_allow_html=True)
        st.markdown('<p class="login-subtitle">Bitte melde dich mit deinem Google-Konto an</p>', unsafe_allow_html=True)
        
        # Google Login Button
        if st.button("🔐 Mit Google anmelden", use_container_width=True, type="primary"):
            try:
                supabase = get_supabase()
                
                # OAuth URL generieren
                redirect_url = st.secrets.get("redirect_url", "https://vfsverband.streamlit.app")
                
                result = supabase.auth.sign_in_with_oauth({
                    "provider": "google",
                    "options": {
                        "redirect_to": redirect_url,
                        "scopes": " ".join(GOOGLE_SCOPES)
                    }
                })
                
                if result and result.url:
                    st.markdown(f'<meta http-equiv="refresh" content="0; url={result.url}">', unsafe_allow_html=True)
                    st.info("Weiterleitung zu Google...")
                    
            except Exception as e:
                st.error(f"Login-Fehler: {str(e)}")
        
        st.markdown("---")
        st.caption("Mit dem Login stimmst du unseren Nutzungsbedingungen zu.")
        
        # Debug: Manuelle Token-Eingabe (für Entwicklung)
        with st.expander("🔧 Debug: Manueller Login"):
            manual_email = st.text_input("E-Mail eingeben (nur Entwicklung)")
            if st.button("Manuell einloggen") and manual_email:
                process_login(manual_email)
                st.rerun()


def process_login(email: str):
    """Verarbeitet den Login und prüft Berechtigung."""
    # E-Mail normalisieren
    email = email.lower().strip()
    
    # User in Session speichern
    st.session_state.user = {"email": email}
    
    # Kunde in Datenbank suchen
    kunde = get_kunde_by_email(email)
    
    if kunde:
        st.session_state.kunde = kunde
    else:
        st.session_state.kunde = None


def get_current_user():
    """Gibt den aktuellen User zurück oder None."""
    return st.session_state.get("user")


def get_current_kunde():
    """Gibt den aktuellen Kunden zurück oder None."""
    return st.session_state.get("kunde")


def logout():
    """Loggt den User aus."""
    try:
        supabase = get_supabase()
        supabase.auth.sign_out()
    except:
        pass
    
    st.session_state.user = None
    st.session_state.kunde = None


def require_auth():
    """Decorator/Check: Stellt sicher, dass User eingeloggt ist."""
    if not st.session_state.get("user"):
        st.warning("⚠️ Bitte zuerst einloggen")
        st.switch_page("app.py")
        st.stop()
    
    if not st.session_state.get("kunde"):
        st.error("❌ Kein Zugang für diese E-Mail-Adresse")
        st.stop()
    
    return st.session_state.kunde


def check_session():
    """Prüft ob eine gültige Session existiert (nach OAuth Redirect)."""
    try:
        # Debug: URL Parameter anzeigen
        params = st.query_params
        st.write(f"DEBUG: Query Params: {dict(params)}")
        
        supabase = get_supabase()
        session = supabase.auth.get_session()
        
        st.write(f"DEBUG: Session: {session}")
        
        if session and session.user:
            email = session.user.email
            st.write(f"DEBUG: Email gefunden: {email}")
            process_login(email)
            return True
    except Exception as e:
        st.write(f"DEBUG: Fehler in check_session: {e}")
    
    return False
