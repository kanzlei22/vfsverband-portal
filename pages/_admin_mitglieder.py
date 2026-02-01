"""
👥 Mitgliederverwaltung (Admin-Bereich)
UnternehmerVernetzt Deutschland e.V.
"""

import streamlit as st
from datetime import datetime
import pandas as pd
from utils.supabase_client import get_supabase
from utils.mitglieder_sync import (
    sync_from_google_sheet,
    sync_to_hubspot,
    export_meinverein_csv,
    get_mitglieder_stats,
    mark_meinverein_exported
)

# === PAGE CONFIG muss ZUERST kommen ===
st.set_page_config(page_title="Admin - Mitgliederverwaltung", page_icon="👑", layout="wide")

# === ADMIN CHECK via Google E-Mail ===
# Admin-Emails aus Secrets holen (kann Liste oder String sein)
admin_emails_raw = st.secrets.get("admin_emails", [])

# Falls es ein String ist, in Liste umwandeln
if isinstance(admin_emails_raw, str):
    admin_emails = [admin_emails_raw.lower().strip()]
else:
    admin_emails = [e.lower().strip() for e in admin_emails_raw]

# User E-Mail holen
user_email = ""
if st.session_state.get("user"):
    user_email = st.session_state.user.get("email", "").lower().strip()

# Check
is_admin = user_email in admin_emails and user_email != ""

if not is_admin:
    st.error("⛔ Zugriff verweigert")
    st.warning("Diese Seite ist nur für Administratoren zugänglich.")
    st.info(f"Eingeloggt als: {user_email or 'Nicht eingeloggt'}")
    # Debug-Info (kann später entfernt werden)
    with st.expander("Debug-Info"):
        st.write(f"User E-Mail: '{user_email}'")
        st.write(f"Admin E-Mails: {admin_emails}")
        st.write(f"In Liste: {user_email in admin_emails}")
    if st.button("← Zur Startseite"):
        st.switch_page("app.py")
    st.stop()

st.title("👥 Mitgliederverwaltung")
st.caption("UnternehmerVernetzt Deutschland e.V. | 👑 Admin-Bereich")

# Admin-Header
st.success(f"👑 Admin: {user_email}")

# === AUTO-SYNC beim ersten Seitenaufruf ===
if "auto_sync_done" not in st.session_state:
    st.session_state.auto_sync_done = False

if not st.session_state.auto_sync_done:
    with st.spinner("🔄 Prüfe neue Anträge..."):
        result = sync_from_google_sheet()
        st.session_state.auto_sync_done = True
        
        if result["success"]:
            if result["imported"] > 0:
                st.toast(f"🎉 Hurra! {result['imported']} neue Mitgliedsanträge!", icon="🎉")
                st.balloons()
            else:
                st.toast("✅ Keine neuen Anträge", icon="✅")

# === STATISTIK-KACHELN ===
stats = get_mitglieder_stats()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="🆕 Neue Anträge",
        value=stats.get("neu", 0),
        help="Anträge die noch nicht geprüft wurden"
    )

with col2:
    st.metric(
        label="⏳ In Prüfung",
        value=stats.get("pending", 0),
        help="Anträge in Bearbeitung"
    )

with col3:
    st.metric(
        label="✅ Aktive Mitglieder",
        value=stats.get("genehmigt", 0),
        help="Genehmigte Mitglieder"
    )

with col4:
    st.metric(
        label="⚠️ Sync ausstehend",
        value=stats.get("sync_pending", 0),
        help="Noch nicht zu HubSpot/MeinVerein synchronisiert"
    )

st.divider()

# === TABS ===
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📥 Neue Anträge", 
    "📋 Alle Mitglieder", 
    "🔄 Synchronisation",
    "➕ Manuell anlegen",
    "⚙️ Einstellungen"
])

# --- TAB 1: NEUE ANTRÄGE ---
with tab1:
    st.subheader("📥 Neue Anträge")
    
    # Button: Von Google Sheet importieren
    col1, col2 = st.columns([1, 3])
    with col1:
        if st.button("🔄 Sheet aktualisieren", use_container_width=True):
            with st.spinner("Importiere neue Anträge..."):
                result = sync_from_google_sheet()
                if result["success"]:
                    if result["imported"] > 0:
                        st.success(f"✅ {result['imported']} neue Anträge importiert!")
                        st.balloons()
                    else:
                        st.info("ℹ️ Keine neuen Anträge gefunden.")
                    st.rerun()
                else:
                    st.error(f"❌ Fehler: {result['error']}")
    
    # Neue Anträge anzeigen
    supabase = get_supabase()
    response = supabase.table("mitglieder").select("*").eq("status", "neu").order("created_at", desc=True).execute()
    
    neue_antraege = response.data if response.data else []
    
    if not neue_antraege:
        st.info("🎉 Keine neuen Anträge vorhanden.")
    else:
        st.success(f"📬 **{len(neue_antraege)} neue Anträge** warten auf Prüfung!")
        
        for antrag in neue_antraege:
            with st.expander(f"**{antrag['vorname']} {antrag['nachname']}** - {antrag['email']}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Persönliche Daten:**")
                    st.write(f"- Anrede: {antrag.get('anrede', '-')}")
                    st.write(f"- Name: {antrag['vorname']} {antrag['nachname']}")
                    st.write(f"- E-Mail: {antrag['email']}")
                    st.write(f"- Telefon: {antrag.get('telefon', '-')}")
                    st.write(f"- Instagram: {antrag.get('instagramname', '-')}")
                    
                    st.write("**Adresse:**")
                    st.write(f"- {antrag.get('strasse', '-')}")
                    st.write(f"- {antrag.get('plz', '-')} {antrag.get('ort', '-')}")
                
                with col2:
                    st.write("**Mitgliedschaft:**")
                    art = "Natürliche Person" if antrag.get('mitgliedsart') == 'natuerlich' else "Juristische Person"
                    st.write(f"- Art: {art}")
                    zahlungsweise = "Monatlich" if antrag.get('zahlungsweise') == 'monatlich' else "Jährlich"
                    st.write(f"- Zahlungsweise: {zahlungsweise}")
                    zahlungsart = "Lastschrift" if antrag.get('zahlungsart') == 'lastschrift' else "Rechnung"
                    st.write(f"- Zahlungsart: {zahlungsart}")
                    st.write(f"- Beitrag: {antrag.get('beitrag_monatlich', 25):.2f} €/Monat")
                    
                    if antrag.get('zahlungsart') == 'lastschrift' and antrag.get('iban'):
                        st.write("**Bankdaten:**")
                        iban = antrag.get('iban', '')
                        if len(iban) > 8:
                            st.write(f"- IBAN: {iban[:8]}...{iban[-4:]}")
                        else:
                            st.write(f"- IBAN: {iban}")
                        st.write(f"- Kontoinhaber: {antrag.get('kontoinhaber', '-')}")
                    else:
                        st.info("💳 Zahlung per Rechnung")
                    
                    created = antrag.get('created_at', '')[:10] if antrag.get('created_at') else '-'
                    st.write(f"**Antragsdatum:** {created}")
                
                # Aktions-Buttons
                st.divider()
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    if st.button("✅ Genehmigen", key=f"approve_{antrag['id']}", type="primary"):
                        import secrets
                        mandatsref = f"UV-{datetime.now().year}-{secrets.token_hex(4).upper()}"
                        
                        update_data = {
                            "status": "genehmigt",
                            "genehmigt_am": datetime.now().isoformat(),
                            "genehmigt_von": "admin"
                        }
                        
                        if antrag.get('zahlungsart') == 'lastschrift':
                            update_data["mandatsreferenz"] = mandatsref
                            update_data["mandatsdatum"] = datetime.now().date().isoformat()
                        
                        supabase.table("mitglieder").update(update_data).eq("id", antrag['id']).execute()
                        
                        st.success(f"✅ {antrag['vorname']} {antrag['nachname']} genehmigt!")
                        st.rerun()
                
                with col_b:
                    if st.button("⏳ In Prüfung", key=f"pending_{antrag['id']}"):
                        supabase.table("mitglieder").update({
                            "status": "pending"
                        }).eq("id", antrag['id']).execute()
                        st.info("Status auf 'In Prüfung' gesetzt")
                        st.rerun()
                
                with col_c:
                    if st.button("❌ Ablehnen", key=f"reject_{antrag['id']}"):
                        supabase.table("mitglieder").update({
                            "status": "abgelehnt"
                        }).eq("id", antrag['id']).execute()
                        st.warning("Antrag abgelehnt")
                        st.rerun()


# --- TAB 2: ALLE MITGLIEDER ---
with tab2:
    st.subheader("📋 Mitgliederliste")
    
    # Filter
    col1, col2, col3 = st.columns(3)
    with col1:
        status_filter = st.selectbox(
            "Status",
            ["Alle", "genehmigt", "neu", "pending", "abgelehnt"],
            index=0
        )
    with col2:
        sync_filter = st.selectbox(
            "Sync-Status",
            ["Alle", "HubSpot ausstehend", "MeinVerein ausstehend", "Vollständig synchronisiert"],
            index=0
        )
    with col3:
        search = st.text_input("🔍 Suche (Name/E-Mail)")
    
    # Daten laden
    query = supabase.table("mitglieder").select("*")
    
    if status_filter != "Alle":
        query = query.eq("status", status_filter)
    
    response = query.order("created_at", desc=True).execute()
    mitglieder = response.data if response.data else []
    
    # Filter anwenden
    if sync_filter == "HubSpot ausstehend":
        mitglieder = [m for m in mitglieder if not m.get("sync_hubspot")]
    elif sync_filter == "MeinVerein ausstehend":
        mitglieder = [m for m in mitglieder if not m.get("sync_meinverein")]
    elif sync_filter == "Vollständig synchronisiert":
        mitglieder = [m for m in mitglieder if m.get("sync_hubspot") and m.get("sync_meinverein")]
    
    if search:
        search_lower = search.lower()
        mitglieder = [m for m in mitglieder if 
                     search_lower in m.get("vorname", "").lower() or
                     search_lower in m.get("nachname", "").lower() or
                     search_lower in m.get("email", "").lower()]
    
    # Tabelle anzeigen
    if mitglieder:
        df = pd.DataFrame(mitglieder)
        
        # Spalten für Anzeige vorbereiten
        display_df = df[["vorname", "nachname", "email", "status", "sync_hubspot", "sync_meinverein"]].copy()
        display_df.columns = ["Vorname", "Nachname", "E-Mail", "Status", "HubSpot", "MeinVerein"]
        
        # Status-Icons
        status_icons = {"neu": "🆕", "pending": "⏳", "genehmigt": "✅", "abgelehnt": "❌"}
        display_df["Status"] = display_df["Status"].map(lambda x: f"{status_icons.get(x, '')} {x}")
        display_df["HubSpot"] = display_df["HubSpot"].map(lambda x: "✓" if x else "—")
        display_df["MeinVerein"] = display_df["MeinVerein"].map(lambda x: "✓" if x else "—")
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        st.caption(f"Gesamt: {len(mitglieder)} Mitglieder")
    else:
        st.info("Keine Mitglieder gefunden.")


# --- TAB 3: SYNCHRONISATION ---
with tab3:
    st.subheader("🔄 Synchronisation")
    
    col1, col2 = st.columns(2)
    
    # HubSpot Sync
    with col1:
        st.markdown("### 🟠 HubSpot")
        st.write("Synchronisiert genehmigte Mitglieder als Kontakte zu HubSpot.")
        st.caption("Setzt 'Mitglied im Verein für Unternehmer' = Ja")
        
        # Anzahl ausstehend
        response = supabase.table("mitglieder").select("id").eq("status", "genehmigt").eq("sync_hubspot", False).execute()
        pending_hubspot = len(response.data) if response.data else 0
        
        st.info(f"**{pending_hubspot}** Mitglieder noch nicht synchronisiert")
        
        if st.button("🔄 Zu HubSpot synchronisieren", use_container_width=True, disabled=pending_hubspot==0):
            with st.spinner("Synchronisiere zu HubSpot..."):
                result = sync_to_hubspot()
                if result["success"]:
                    if result["synced"] > 0:
                        st.success(f"✅ {result['synced']} Kontakte zu HubSpot synchronisiert!")
                        st.balloons()
                    else:
                        st.info("ℹ️ Keine neuen Kontakte zum Synchronisieren.")
                    st.rerun()
                else:
                    st.error(f"❌ Fehler: {result['error']}")
    
    # MeinVerein Export
    with col2:
        st.markdown("### 🔵 MeinVerein (Wiso)")
        st.write("Exportiert Mitglieder als XLSX für den Import in MeinVerein.")
        
        # Anzahl ausstehend
        response = supabase.table("mitglieder").select("id").eq("status", "genehmigt").eq("sync_meinverein", False).execute()
        pending_meinverein = len(response.data) if response.data else 0
        
        st.info(f"**{pending_meinverein}** Mitglieder noch nicht exportiert")
        
        if pending_meinverein > 0:
            result = export_meinverein_csv()
            if result["success"]:
                col_dl, col_mark = st.columns(2)
                with col_dl:
                    st.download_button(
                        label="💾 XLSX herunterladen",
                        data=result["xlsx_data"],
                        file_name=f"meinverein_import_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                with col_mark:
                    if st.button("✅ Als exportiert markieren", use_container_width=True):
                        mark_result = mark_meinverein_exported(result["member_ids"])
                        if mark_result["success"]:
                            st.success(f"✅ {len(result['member_ids'])} Mitglieder als exportiert markiert!")
                            st.rerun()
            else:
                st.error(f"❌ Fehler: {result['error']}")
    
    st.divider()
    
    # Sync-Historie
    st.markdown("### 📜 Letzte Synchronisierungen")
    
    response = supabase.table("mitglieder").select("vorname, nachname, sync_hubspot_datum, sync_meinverein_datum").order("sync_hubspot_datum", desc=True).limit(10).execute()
    
    if response.data:
        found = False
        for m in response.data:
            if m.get("sync_hubspot_datum") or m.get("sync_meinverein_datum"):
                found = True
                hs = m.get("sync_hubspot_datum", "-")[:10] if m.get("sync_hubspot_datum") else "-"
                mv = m.get("sync_meinverein_datum", "-")[:10] if m.get("sync_meinverein_datum") else "-"
                st.write(f"- {m['vorname']} {m['nachname']}: HubSpot {hs} | MeinVerein {mv}")
        if not found:
            st.info("Noch keine Synchronisierungen durchgeführt.")


# --- TAB 4: MANUELL ANLEGEN ---
with tab4:
    st.subheader("➕ Mitglied manuell anlegen")
    
    with st.form("neues_mitglied"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Persönliche Daten**")
            anrede = st.selectbox("Anrede *", ["Herr", "Frau", "Divers"])
            vorname = st.text_input("Vorname *")
            nachname = st.text_input("Nachname *")
            email = st.text_input("E-Mail *")
            telefon = st.text_input("Telefon")
            instagramname = st.text_input("Instagram-Name")
            
            st.markdown("**Adresse**")
            strasse = st.text_input("Straße + Hausnummer *")
            plz = st.text_input("PLZ *")
            ort = st.text_input("Ort *")
        
        with col2:
            st.markdown("**Mitgliedschaft**")
            mitgliedsart = st.selectbox("Art *", ["natuerlich", "juristisch"], format_func=lambda x: "Natürliche Person" if x == "natuerlich" else "Juristische Person")
            zahlungsweise = st.selectbox("Zahlungsweise *", ["monatlich", "jaehrlich"], format_func=lambda x: "Monatlich (25€)" if x == "monatlich" else "Jährlich (300€)")
            zahlungsart = st.selectbox("Zahlungsart *", ["lastschrift", "rechnung"], format_func=lambda x: "Per Lastschrift" if x == "lastschrift" else "Auf Rechnung")
            
            st.markdown("**Bankdaten** (nur bei Lastschrift)")
            iban = st.text_input("IBAN")
            kontoinhaber = st.text_input("Kontoinhaber")
            
            st.markdown("**Status**")
            status = st.selectbox("Status", ["neu", "genehmigt"], index=1)
            quelle = st.selectbox("Quelle", ["manuell", "wiso_import"])
            notizen = st.text_area("Notizen")
        
        submitted = st.form_submit_button("💾 Mitglied anlegen", type="primary", use_container_width=True)
        
        if submitted:
            # Validierung
            required = [vorname, nachname, email, strasse, plz, ort]
            if zahlungsart == "lastschrift":
                required.extend([iban, kontoinhaber])
            
            if not all(required):
                st.error("Bitte fülle alle Pflichtfelder aus.")
            else:
                # Prüfe ob E-Mail bereits existiert
                existing = supabase.table("mitglieder").select("id").eq("email", email.lower()).execute()
                
                if existing.data:
                    st.error("❌ Ein Mitglied mit dieser E-Mail existiert bereits!")
                else:
                    import secrets as sec
                    beitrag = 25.00
                    mandatsref = f"UV-{datetime.now().year}-{sec.token_hex(4).upper()}" if zahlungsart == "lastschrift" else None
                    
                    neues_mitglied = {
                        "anrede": anrede,
                        "vorname": vorname,
                        "nachname": nachname,
                        "email": email.lower().strip(),
                        "telefon": telefon,
                        "instagramname": instagramname,
                        "strasse": strasse,
                        "plz": plz,
                        "ort": ort,
                        "iban": iban.replace(" ", "").upper() if iban else None,
                        "kontoinhaber": kontoinhaber if kontoinhaber else None,
                        "mandatsreferenz": mandatsref,
                        "mandatsdatum": datetime.now().date().isoformat() if zahlungsart == "lastschrift" else None,
                        "mitgliedsart": mitgliedsart,
                        "zahlungsweise": zahlungsweise,
                        "zahlungsart": zahlungsart,
                        "beitrag_monatlich": beitrag,
                        "status": status,
                        "quelle": quelle,
                        "notizen": notizen,
                        "genehmigt_am": datetime.now().isoformat() if status == "genehmigt" else None,
                        "genehmigt_von": "admin" if status == "genehmigt" else None
                    }
                    
                    result = supabase.table("mitglieder").insert(neues_mitglied).execute()
                    
                    if result.data:
                        st.success(f"✅ Mitglied {vorname} {nachname} erfolgreich angelegt!")
                        st.balloons()
                    else:
                        st.error("❌ Fehler beim Anlegen.")


# --- TAB 5: EINSTELLUNGEN ---
with tab5:
    st.subheader("⚙️ Einstellungen & Links")
    
    # === GOOGLE FORMS LINKS ===
    st.markdown("### 📝 Google Forms & Tabelle")
    
    # Links aus secrets oder hardcoded
    form_edit_url = st.secrets.get("form_edit_url", "https://docs.google.com/forms/d/1FNv0ByOfq-q6ThDZVB1hJm2iiGcfSM_PYs4RMNTPldc/edit")
    form_public_url = st.secrets.get("form_public_url", "https://docs.google.com/forms/d/e/1FAIpQLSdXXX/viewform")
    sheet_url = st.secrets.get("sheet_url", "https://docs.google.com/spreadsheets/d/1FNv0ByOfq-q6ThDZVB1hJm2iiGcfSM_PYs4RMNTPldc/edit")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🔧 Formular bearbeiten**")
        st.markdown(f"[Formular öffnen]({form_edit_url})")
    
    with col2:
        st.markdown("**🌐 Öffentlicher Link**")
        st.markdown(f"[Formular ansehen]({form_public_url})")
    
    with col3:
        st.markdown("**📊 Google Sheet**")
        st.markdown(f"[Tabelle öffnen]({sheet_url})")
    
    st.divider()
    
    # === EINBETTUNGSCODE ===
    st.markdown("### 🖥️ Einbettungscode für Website")
    st.caption("Diesen Code kann dein Webseiten-Admin verwenden:")
    
    embed_code = f'''<iframe 
  src="{form_public_url}?embedded=true" 
  width="100%" 
  height="1200" 
  frameborder="0" 
  marginheight="0" 
  marginwidth="0">
  Wird geladen…
</iframe>'''
    
    st.code(embed_code, language="html")
    
    st.divider()
    
    # === SYNC EINSTELLUNGEN ===
    st.markdown("### 🔄 Sync-Einstellungen")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Auto-Sync zurücksetzen"):
            st.session_state.auto_sync_done = False
            st.success("Auto-Sync zurückgesetzt. Wird beim nächsten Laden ausgeführt.")
            st.rerun()
    
    with col2:
        if st.button("📊 Statistik aktualisieren"):
            st.rerun()
    
    st.divider()
    
    # === ADMIN INFO ===
    st.markdown("### 👑 Admin-Info")
    st.info(f"""
    **Admin-Passwort ändern:**
    In Streamlit Cloud Secrets unter `admin_password` setzen.
    
    **Links anpassen:**
    In Secrets können folgende Werte gesetzt werden:
    - `form_edit_url` - Link zum Bearbeiten des Formulars
    - `form_public_url` - Öffentlicher Link zum Formular  
    - `sheet_url` - Link zur Google-Tabelle
    """)
