# countdown.py — cartes plus basses, rendu net (supersampling x2)
import os, io, datetime as dt, requests
from PIL import Image, ImageDraw, ImageFont

# ───────────── config événements ─────────────
EVENTS = [
    {"name": "Signature du bail", "date": dt.date(2025, 8, 22), "color": "#f9c068", "icon": "calendrier.png"},
    {"name": "Emménagement",      "date": dt.date(2025, 8, 30), "color": "#438c55", "icon": "home-sweet-home.png"},
]

# rendu net : on dessine en 2× puis on réduit (anti-aliasing fort)
SCALE = 2

# taille finale affichée dans Discord (après réduction)
FINAL_W, FINAL_H = 920, 360  # plus bas que précédemment
SPACING = 36                  # espace entre cartes
MARGIN  = 0                   # fond transparent partout

# dérivés (zone de travail haute résolution)
W, H = FINAL_W * SCALE, FINAL_H * SCALE
SPACING2 = SPACING * SCALE

# cartes (hauteur réduite)
CARD_W  = int((FINAL_W - SPACING) / 2) * SCALE
CARD_H  = (FINAL_H) * SCALE
RADIUS  = 34 * SCALE//2  # coins arrondis

# paddings internes (proportionnels)
PAD_X      = int(24 * SCALE)
PAD_TOP    = int(22 * SCALE)
PAD_BOTTOM = int(20 * SCALE)

# icône proportionnelle et éléments
ICON_SIZE     = int(CARD_H * 0.28)           # ~28% de la hauteur de carte
GAP_ICON_JX   = int(12 * SCALE)
GAP_JX_PILL   = int(10 * SCALE)
GAP_PILL_LBL  = int(10 * SCALE)

# polices présentes sur runner Ubuntu
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_REG  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

MONTHS_FR = ["janvier","février","mars","avril","mai","juin","juillet","août",
             "septembre","octobre","novembre","décembre"]

def format_date_fr(d: dt.date) -> str:
    return f"{d.day} {MONTHS_FR[d.month-1]} {d.year}"

def hex_to_rgba(hex_color, a=255):
    h = hex_color.lstrip("#")
    return (int(h[0:2],16), int(h[2:4],16), int(h[4:6],16), a)

def pill_color(hex_color, factor=0.22, alpha=220):
    r,g,b,_ = hex_to_rgba(hex_color)
    return (int(r*(1-factor)), int(g*(1-factor)), int(b*(1-factor)), alpha)

def load_icon(filename, size):
    path = os.path.join(os.path.dirname(__file__), filename)
    img = Image.open(path).convert("RGBA")
    return img.resize((size, size), Image.LANCZOS)

def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont):
    # bbox donne [x0,y0,x1,y1]
    b = draw.textbbox((0,0), text, font=font)
    return b[2]-b[0], b[3]-b[1]

def draw_card(event: dict, today: dt.date) -> Image.Image:
    card = Image.new("RGBA", (CARD_W, CARD_H), (0,0,0,0))
    d = ImageDraw.Draw(card)

    # fond arrondi rempli
    d.rounded_rectangle((0,0,CARD_W,CARD_H), RADIUS, fill=hex_to_rgba(event["color"]))

    # zone utile
    x0,y0 = PAD_X, PAD_TOP
    x1,y1 = CARD_W-PAD_X, CARD_H-PAD_BOTTOM
    cx = (x0+x1)//2

    # icône (centrée, petite)
    icon = load_icon(event["icon"], ICON_SIZE)
    icon_y = y0
    card.paste(icon, (cx-ICON_SIZE//2, icon_y), icon)

    # J - X (plus compact)
    delta = (event["date"] - today).days
    if   delta > 1: jtxt = f"J - {delta}"
    elif delta == 1: jtxt = "J - 1"
    elif delta == 0: jtxt = "AUJOURD’HUI"
    else:            jtxt = "PASSÉ"

    f_big = ImageFont.truetype(FONT_BOLD, int(36 * SCALE))
    wj, hj = text_size(d, jtxt, f_big)
    jy = icon_y + ICON_SIZE + GAP_ICON_JX
    d.text((cx - wj//2, jy), jtxt, font=f_big, fill=(255,255,255,255))

    # pastille date
    date_str = format_date_fr(event["date"])
    f_date = ImageFont.truetype(FONT_BOLD, int(18 * SCALE))
    tw, th = text_size(d, date_str, f_date)
    pad_x, pad_y = int(10*SCALE), int(6*SCALE)
    pill_w, pill_h = tw + pad_x*2, th + pad_y*2
    px = cx - pill_w//2
    py = jy + hj + GAP_JX_PILL
    d.rounded_rectangle((px, py, px+pill_w, py+pill_h), pill_h//2, fill=pill_color(event["color"]))
    d.text((cx - tw//2, py + pad_y - int(1*SCALE)), date_str, font=f_date, fill=(255,255,255,255))

    # libellé (gras, même baseline entre cartes)
    f_lbl = ImageFont.truetype(FONT_BOLD, int(20 * SCALE))
    lw, lh = text_size(d, event["name"], f_lbl)
    ly = py + pill_h + GAP_PILL_LBL
    # clamp si bord bas
    if ly + lh > y1:
        f_lbl = ImageFont.truetype(FONT_BOLD, int(18 * SCALE))
        lw, lh = text_size(d, event["name"], f_lbl)
        ly = min(ly, y1 - lh)
    d.text((cx - lw//2, ly), event["name"], font=f_lbl, fill=(255,255,255,255))

    return card

def build_image(today: dt.date) -> Image.Image:
    canvas = Image.new("RGBA", (W, H), (0,0,0,0))
    x = MARGIN * SCALE
    for ev in EVENTS:
        card = draw_card(ev, today)
        canvas.paste(card, (x, MARGIN), card)
        x += CARD_W + SPACING2
    # downscale propre → texte net
    final = canvas.resize((FINAL_W, FINAL_H), Image.LANCZOS)
    return final

def send_to_discord(img: Image.Image):
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        raise RuntimeError("DISCORD_WEBHOOK_URL manquant (secret GitHub).")
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
    # date locale Europe/Paris
    try:
        from zoneinfo import ZoneInfo
        today = dt.datetime.now(ZoneInfo("Europe/Paris")).date()
    except Exception:
        today = dt.date.today()
    img = build_image(today)
    send_to_discord(img)

if __name__ == "__main__":
    run()
