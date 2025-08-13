# countdown.py
import os
import datetime as dt
import requests

try:
    from zoneinfo import ZoneInfo  # Python 3.9+, standard
    PARIS = ZoneInfo("Europe/Paris")
except Exception:
    PARIS = None

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]

# === ÉVÉNEMENTS (déjà remplis) ===
EVENTS = [
    ("Signature du bail", "2025-08-22", "📝"),
    ("Emménagement",     "2025-08-30", "🏡"),
]
# ================================

# Aujourd'hui en heure de Paris (gère été/hiver)
now_utc = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
today = now_utc.astimezone(PARIS).date() if PARIS else dt.date.today()

lines = []
for title, date_str, emoji in EVENTS:
    d = dt.date.fromisoformat(date_str)
    delta = (d - today).days
    if delta > 1:
        msg = f"J-{delta} avant **{title}** {emoji} ({d.strftime('%d/%m/%Y')})"
    elif delta == 1:
        msg = f"J-1 avant **{title}** {emoji} (demain • {d.strftime('%d/%m/%Y')})"
    elif delta == 0:
        msg = f"🎉 **C'EST AUJOURD'HUI !** {title} {emoji}"
    else:
        msg = f"{title} {emoji} : **passé** (le {d.strftime('%d/%m/%Y')})"
    lines.append("• " + msg)

payload = {
    "username": "Compte à rebours",
    "embeds": [{
        "title": "⏳ Comptes à rebours du jour",
        "description": "\n".join(lines),
        "footer": {"text": "Fuseau : Europe/Paris"},
        "timestamp": dt.datetime.utcnow().isoformat() + "Z",
    }]
}

resp = requests.post(WEBHOOK, json=payload, timeout=20)
resp.raise_for_status()
