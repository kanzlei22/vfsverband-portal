"""
Kontakt-Konfiguration für das Kunden-Portal

ANPASSEN: Trage hier deine eigenen Kontaktdaten ein!
"""

# WhatsApp Business Nummer (mit Ländervorwahl, ohne +)
WHATSAPP_NUMBER = "4915678123456"  # TODO: Deine Nummer

# Calendly Link für kostenloses Erstgespräch
CALENDLY_LINK = "https://calendly.com/driver39/erstgespraech"  # TODO: Dein Link

# Beratungs-Buchungsseite
BERATUNG_LINK = "https://www.driver39.de/beratung"

# Impressum-Link
IMPRESSUM_LINK = "https://www.driver39.de/impressum"

# AGB-Link  
AGB_LINK = "https://www.driver39.de/agb"

# Firmenname
COMPANY_NAME = "Driver39"

# Website
WEBSITE = "https://www.driver39.de"

# E-Mail für Datenschutz-Anfragen
DATENSCHUTZ_EMAIL = "datenschutz@driver39.de"

# === GENERIERTE LINKS ===
def get_whatsapp_link(message: str = "") -> str:
    """Generiert WhatsApp-Link mit optionaler Nachricht."""
    base = f"https://wa.me/{WHATSAPP_NUMBER}"
    if message:
        import urllib.parse
        return f"{base}?text={urllib.parse.quote(message)}"
    return base

WHATSAPP_LINK = get_whatsapp_link()
