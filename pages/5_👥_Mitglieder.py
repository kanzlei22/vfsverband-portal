"""
👥 Mitgliederverwaltung
UnternehmerVernetzt Deutschland e.V.
"""

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from utils.auth import require_auth
from utils.supabase_client import get_supabase
from utils.mitglieder_sync import (
    sync_from_google_sheet,
    sync_to_hubspot,
    export_meinverein_csv,
    get_mitglieder_stats
)

# Auth check
require_auth()

st.title("👥 Mitgliederverwaltung")
st.caption("UnternehmerVernetzt Deutschland e.V.")

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
tab1, tab2, tab3, tab4 = st.tabs([
    "📥 Neue Anträge", 
    "📋 Alle Mitglieder", 
    "🔄 Synchronisation",
    "➕ Manuell anlegen"
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
                    st.success(f"✅ {result['imported']} neue Anträge importiert")
                    st.rerun()
                else:
                    st.error(f"❌ Fehler: {result['error']}")
    
    # Neue Anträge anzeigen
    supabase = get_supabase()
    response = supabase.table("mitglieder").select("*").eq("status", "neu").order("antragsdatum", desc=True).execute()
    
    neue_antraege = response.data if response.data else []
    
    if not neue_antraege:
        st.info("🎉 Keine neuen Anträge vorhanden.")
    else:
        for antrag in neue_antraege:
            with st.expander(f"**{antrag['vorname']} {antrag['nachname']}** - {antrag['email']}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Persönliche Daten:**")
                    st.write(f"- Anrede: {antrag.get('anrede', '-')}")
                    st.write(f"- Name: {antrag['vorname']} {antrag['nachname']}")
                    st.write(f"- E-Mail: {antrag['email']}")
                    st.write(f"- Telefon: {antrag.get('telefon', '-')}")
                    
                    st.write("**Adresse:**")
                    st.write(f"- {antrag.get('strasse', '-')}")
                    st.write(f"- {antrag.get('plz', '-')} {antrag.get('ort', '-')}")
                
                with col2:
                    st.write("**Mitgliedschaft:**")
                    art = "Natürliche Person" if antrag.get('mitgliedsart') == 'natuerlich' else "Juristische Person"
                    st.write(f"- Art: {art}")
                    st.write(f"- Zahlungsweise: {antrag.get('zahlungsweise', 'monatlich')}")
                    st.write(f"- Beitrag: {antrag.get('beitrag_monatlich', 25):.2f} €/Monat")
                    
                    st.write("**Bankdaten:**")
                    st.write(f"- IBAN: {antrag.get('iban', '-')[:8]}...{antrag.get('iban', '-')[-4:]}")
                    st.write(f"- Kontoinhaber: {antrag.get('kontoinhaber', '-')}")
                    
                    st.write(f"**Antragsdatum:** {antrag.get('antragsdatum', '-')[:10]}")
                
                # Aktions-Buttons
                st.divider()
                col_a, col_b, col_c = st.columns(3)
                
                with col_a:
                    if st.button("✅ Genehmigen", key=f"approve_{antrag['id']}", type="primary"):
                        # Status aktualisieren
                        supabase.table("mitglieder").update({
                            "status": "genehmigt",
                            "genehmigt_am": datetime.now().isoformat(),
                            "genehmigt_von": st.session_state.user.get("email", "admin"),
                            "mandatsreferenz": f"UV-{datetime.now().year}-{str(antrag['id'])[:8].upper()}"
                        }).eq("id", antrag['id']).execute()
                        
                        st.success("✅ Mitglied genehmigt!")
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
        
        # Anzahl ausstehend
        response = supabase.table("mitglieder").select("id").eq("status", "genehmigt").eq("sync_hubspot", False).execute()
        pending_hubspot = len(response.data) if response.data else 0
        
        st.info(f"**{pending_hubspot}** Mitglieder noch nicht synchronisiert")
        
        if st.button("🔄 Zu HubSpot synchronisieren", use_container_width=True, disabled=pending_hubspot==0):
            with st.spinner("Synchronisiere zu HubSpot..."):
                result = sync_to_hubspot()
                if result["success"]:
                    st.success(f"✅ {result['synced']} Kontakte synchronisiert")
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
        
        if st.button("📥 XLSX herunterladen", use_container_width=True, disabled=pending_meinverein==0):
            result = export_meinverein_csv()
            if result["success"]:
                st.download_button(
                    label="💾 Download XLSX für MeinVerein",
                    data=result["xlsx_data"],
                    file_name=f"meinverein_import_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                # Als exportiert markieren
                if st.button("✅ Als exportiert markieren"):
                    for mid in result["member_ids"]:
                        supabase.table("mitglieder").update({
                            "sync_meinverein": True,
                            "sync_meinverein_datum": datetime.now().isoformat()
                        }).eq("id", mid).execute()
                    st.success("Mitglieder als exportiert markiert")
                    st.rerun()
            else:
                st.error(f"❌ Fehler: {result['error']}")
    
    st.divider()
    
    # Sync-Historie
    st.markdown("### 📜 Letzte Synchronisierungen")
    
    response = supabase.table("mitglieder").select("vorname, nachname, sync_hubspot_datum, sync_meinverein_datum").order("sync_hubspot_datum", desc=True).limit(10).execute()
    
    if response.data:
        for m in response.data:
            if m.get("sync_hubspot_datum") or m.get("sync_meinverein_datum"):
                hs = m.get("sync_hubspot_datum", "-")[:10] if m.get("sync_hubspot_datum") else "-"
                mv = m.get("sync_meinverein_datum", "-")[:10] if m.get("sync_meinverein_datum") else "-"
                st.write(f"- {m['vorname']} {m['nachname']}: HubSpot {hs} | MeinVerein {mv}")


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
            
            st.markdown("**Adresse**")
            strasse = st.text_input("Straße + Hausnummer *")
            plz = st.text_input("PLZ *")
            ort = st.text_input("Ort *")
        
        with col2:
            st.markdown("**Mitgliedschaft**")
            mitgliedsart = st.selectbox("Art *", ["natuerlich", "juristisch"], format_func=lambda x: "Natürliche Person" if x == "natuerlich" else "Juristische Person")
            zahlungsweise = st.selectbox("Zahlungsweise *", ["monatlich", "jaehrlich"], format_func=lambda x: "Monatlich (25€)" if x == "monatlich" else "Jährlich (300€)")
            
            st.markdown("**Bankdaten**")
            iban = st.text_input("IBAN *")
            kontoinhaber = st.text_input("Kontoinhaber *")
            
            st.markdown("**Status**")
            status = st.selectbox("Status", ["neu", "genehmigt"], index=1)
            quelle = st.selectbox("Quelle", ["manuell", "wiso_import"])
            notizen = st.text_area("Notizen")
        
        submitted = st.form_submit_button("💾 Mitglied anlegen", type="primary", use_container_width=True)
        
        if submitted:
            # Validierung
            if not all([vorname, nachname, email, strasse, plz, ort, iban, kontoinhaber]):
                st.error("Bitte fülle alle Pflichtfelder aus.")
            else:
                # Prüfe ob E-Mail bereits existiert
                existing = supabase.table("mitglieder").select("id").eq("email", email.lower()).execute()
                
                if existing.data:
                    st.error("❌ Ein Mitglied mit dieser E-Mail existiert bereits!")
                else:
                    # Anlegen
                    beitrag = 25.00 if mitgliedsart == "natuerlich" else 300.00/12
                    mandatsref = f"UV-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M%S')}"
                    
                    neues_mitglied = {
                        "anrede": anrede,
                        "vorname": vorname,
                        "nachname": nachname,
                        "email": email.lower().strip(),
                        "telefon": telefon,
                        "strasse": strasse,
                        "plz": plz,
                        "ort": ort,
                        "iban": iban.replace(" ", "").upper(),
                        "kontoinhaber": kontoinhaber,
                        "mandatsreferenz": mandatsref,
                        "mandatsdatum": datetime.now().date().isoformat(),
                        "mitgliedsart": mitgliedsart,
                        "zahlungsweise": zahlungsweise,
                        "beitrag_monatlich": beitrag,
                        "status": status,
                        "quelle": quelle,
                        "notizen": notizen,
                        "genehmigt_am": datetime.now().isoformat() if status == "genehmigt" else None,
                        "genehmigt_von": st.session_state.user.get("email", "admin") if status == "genehmigt" else None
                    }
                    
                    result = supabase.table("mitglieder").insert(neues_mitglied).execute()
                    
                    if result.data:
                        st.success(f"✅ Mitglied {vorname} {nachname} erfolgreich angelegt!")
                        st.balloons()
                    else:
                        st.error("❌ Fehler beim Anlegen.")
