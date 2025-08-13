import os
import datetime as dt
import requests

try:
    from zoneinfo import ZoneInfo
    PARIS = ZoneInfo("Europe/Paris")
except Exception:
    PARIS = None

WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]

# === ÉVÉNEMENTS ===
EVENTS = [
    ("📝 Signature du bail", "2025-08-22", 0x3498db),  # bleu
    ("🏡 Emménagement",     "2025-08-30", 0x2ecc71),  # vert
]
# ==================

now_utc = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
today = now_utc.astimezone(PARIS).date() if PARIS else dt.date.today()

fields = []
for title, date_str, color in EVENTS:
    d = dt.date.fromisoformat(date_str)
    delta = (d - today).days

    if delta > 1:
        value = f"**J - {delta}**\n📅 {d.strftime('%d/%m/%Y')}"
    elif delta == 1:
        value = f"**J - 1** *(demain)*\n📅 {d.strftime('%d/%m/%Y')}"
    elif delta == 0:
        value = f"🎉 **C'EST AUJOURD'HUI !** 🎉\n📅 {d.strftime('%d/%m/%Y')}"
    else:
        value = f"✅ Passé le {d.strftime('%d/%m/%Y')}"

    fields.append({
        "name": title,
        "value": value,
        "inline": True
    })

# On met la couleur du premier événement à venir
next_event_color = 0x95a5a6  # gris par défaut
for _, date_str, color in EVENTS:
    if (dt.date.fromisoformat(date_str) - today).days >= 0:
        next_event_color = color
        break

payload = {
    "username": "Compte à rebours",
    "embeds": [{
        "title": "⏳ Comptes à rebours",
        "color": next_event_color,
        "fields": fields,
        "footer": {"text": "Fuseau : Europe/Paris"},
        "timestamp": dt.datetime.utcnow().isoformat() + "Z"
    }]
}

resp = requests.post(WEBHOOK, json=payload, timeout=20)
resp.raise_for_status()
