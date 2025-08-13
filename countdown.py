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

lines = []
next_event_color = 0x95a5a6  # gris par défaut

for title, date_str, color in EVENTS:
    d = dt.date.fromisoformat(date_str)
    delta = (d - today).days

    if delta >= 0 and next_event_color == 0x95a5a6:
        next_event_color = color  # première date future -> couleur

    if delta > 1:
        msg = f"{title} — **J - {delta}**\n📅 {d.strftime('%d/%m/%Y')}"
    elif delta == 1:
        msg = f"{title} — **J - 1** *(demain)*\n📅 {d.strftime('%d/%m/%Y')}"
    elif delta == 0:
        msg = f"{title} — 🎉 **C'EST AUJOURD'HUI !** 🎉\n📅 {d.strftime('%d/%m/%Y')}"
    else:
        msg = f"{title} — ✅ Passé le {d.strftime('%d/%m/%Y')}"

    lines.append(msg)

payload = {
    "username": "Compte à rebours",
    "embeds": [{
        "title": "⏳ Comptes à rebours",
        "description": "\n\n".join(lines),  # double saut de ligne = plus aéré
        "color": next_event_color,
        "footer": {"text": f"Fuseau : Europe/Paris • Aujourd'hui à {now_utc.astimezone(PARIS).strftime('%H:%M')}"},
        "timestamp": dt.datetime.utcnow().isoformat() + "Z"
    }]
}

resp = requests.post(WEBHOOK, json=payload, timeout=20)
resp.raise_for_status()
