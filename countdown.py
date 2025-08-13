# countdown.py
import os, io
import datetime as dt
import requests
from PIL import Image, ImageDraw, ImageFont

# ─────────── config événements ───────────
EVENTS = [
    {"name": "Signature du bail", "date": dt.date(2025, 8, 22), "color": "#f9c068", "icon": "calendrier.png"},
    {"name": "Emménagement",      "date": dt.date(2025, 8, 30), "color": "#438c55", "icon": "home-sweet-home.png"},
]

# mise en page
CARD_W, CARD_H = 300, 400
RADIUS = 30
ICON_SIZE = 90
PAD_TOP, PAD_BOTTOM, PAD_X = 30, 28, 28
SPACING = 40
MARGIN = 0  # fond transparent partout

# polices (présentes sur Ubuntu runner)
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

MONTHS_FR = ["janvier","février","mars","avril","mai","juin","juillet","août",
             "septembre","octobre","novembre","décembre"]

def format_date_fr(d: dt.date) -> str:
    return f"{d.day} {MONTHS_FR[d.month-1]} {d.year}"

def hex_to_rgba(hex_color, a=255):
    h = hex_color.lstrip("#")
    return (int(h[0:2],16), int(h[2:4],16), int(h[4:6],16), a)

def pill_color(hex_color, factor=0.22, alpha=200):
    r,g,b,_ = hex_to_rgba(hex_color)
    return (int(r*(1-factor)), int(g*(1-factor)), int(b*(1-factor)), alpha)

def load_icon(filename, size):
    path = os.path.join(os.path.dirname(__file__), filename)
    img = Image.open(path).convert("RGBA")
    return img.resize((size, size), Image.LANCZOS)

def draw_card(event: dict, today: dt.date) -> Image.Image:
    card = Image.new("RGBA", (CARD_W, CARD_H), (0,0,0,0))
    d = ImageDraw.Draw(card)

    # fond carte arrondi
    d.rounded_rectangle((0,0,CARD_W,CARD_H), RADIUS, fill=hex_to_rgba(event["color"]))

    # zone utile + centre
    x0,y0 = PAD_X, PAD_TOP
    x1,y1 = CARD_W-PAD_X, CARD_H-PAD_BOTTOM
    cx = (x0+x1)//2

    # icône
    icon = load_icon(event["icon"], ICON_SIZE)
    card.paste(icon, (cx-ICON_SIZE//2, y0), icon)

    # J - X
    delta = (event["date"] - today).days
    if   delta > 1: jtxt = f"J - {delta}"
    elif delta == 1: jtxt = "J - 1"
    elif delta == 0: jtxt = "AUJOURD’HUI"
    else:            jtxt = "PASSÉ"

    f_big = ImageFont.truetype(FONT_BOLD, 48 if len(jtxt) <= 9 else 44)
    w,h = d.textbbox((0,0), jtxt, font=f_big)[2:]
    jy = y0 + ICON_SIZE + 18
    d.text((cx - w//2, jy), jtxt, font=f_big, fill=(255,255,255,255))

    # pastille date (légèrement plus sombre que la carte)
    date_str = format_date_fr(event["date"])
    f_date = ImageFont.truetype(FONT_BOLD, 24)
    tw, th = d.textbbox((0,0), date_str, font=f_date)[2:]
    pad_x, pad_y = 14, 8
    pill_w, pill_h = tw + pad_x*2, th + pad_y*2
    px = cx - pill_w//2
    py = jy + h + 14
    d.rounded_rectangle((px, py, px+pill_w, py+pill_h), pill_h//2, fill=pill_color(event["color"]))
    d.text((cx - tw//2, py + pad_y - 2), date_str, font=f_date, fill=(255,255,255,255))

    # libellé
    f_lbl = ImageFont.truetype(FONT_BOLD, 26)
    lw, lh = d.textbbox((0,0), event["name"], font=f_lbl)[2:]
    ly = py + pill_h + 14
    if ly + lh > y1:  # léger ajustement si ça déborde
        f_lbl = ImageFont.truetype(FONT_BOLD, 24)
        lw, lh = d.textbbox((0,0), event["name"], font=f_lbl)[2:]
        ly = y1 - lh
    d.text((cx - lw//2, ly), event["name"], font=f_lbl, fill=(255,255,255,255))

    return card

def build_image(today: dt.date) -> Image.Image:
    w = CARD_W*len(EVENTS) + SPACING*(len(EVENTS)-1) + MARGIN*2
    h = CARD_H + MARGIN*2
    canvas = Image.new("RGBA", (w,h), (0,0,0,0))
    x = MARGIN
    for ev in EVENTS:
        card = draw_card(ev, today)
        canvas.paste(card, (x, MARGIN), card)
        x += CARD_W + SPACING
    return canvas

def send_to_discord(img: Image.Image):
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        raise RuntimeError("DISCORD_WEBHOOK_URL manquant (secret GitHub non défini).")
    buf = io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    files = {"file": ("countdowns.png", buf, "image/png")}
    payload = {
        "username": "Compte à rebours",
        "embeds": [{ "image": {"url": "attachment://countdowns.png"} }]
    }
    import json
    r = requests.post(webhook, data={"payload_json": json.dumps(payload)}, files=files, timeout=30)
    r.raise_for_status()

def run():
    # heure locale Europe/Paris (utile si tu veux l’utiliser)
    try:
        from zoneinfo import ZoneInfo
        today = dt.datetime.now(ZoneInfo("Europe/Paris")).date()
    except Exception:
        today = dt.date.today()
    img = build_image(today)
    send_to_discord(img)

if __name__ == "__main__":
    run()
