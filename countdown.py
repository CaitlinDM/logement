# countdown.py — visuel calé sur ta maquette 1024×512
# - fond transparent
# - mêmes tailles/placements (gros "J - X", pastille large, libellé)
# - icônes: calendrier.png & home-sweet-home.png (tes fichiers)
# - rendu net (supersampling ×2)
# - envoi avec @everyone
import os, io, datetime as dt, requests
from PIL import Image, ImageDraw, ImageFont

# ───────────── Config événements ─────────────
EVENTS = [
    {"name": "Signature du bail", "date": dt.date(2025, 8, 22), "color": "#f9c068", "icon": "calendrier.png"},
    {"name": "Emménagement",      "date": dt.date(2025, 8, 30), "color": "#438c55", "icon": "home-sweet-home.png"},
]

# ───────────── Taille finale & supersampling ─────────────
FINAL_W, FINAL_H = 1024, 512  # comme ta maquette
SCALE            = 2          # on dessine en 2× puis on réduit (anti-aliasing fort)
W, H             = FINAL_W * SCALE, FINAL_H * SCALE

# ───────────── Géométrie des cartes ─────────────
GAP_CARDS = int(40 * SCALE)            # espace entre les 2 cartes
CARD_W    = (W - GAP_CARDS) // 2
CARD_H    = H
RADIUS    = int(46 * SCALE)            # gros arrondi (comme ta capture)

# Paddings internes & gaps verticaux (calés sur la maquette)
PAD_X       = int(70 * SCALE)
PAD_TOP     = int(58 * SCALE)
PAD_BOTTOM  = int(56 * SCALE)

ICON_SIZE   = int(CARD_H * 0.23)       # ~23% hauteur carte (icône bien visible)
GAP_ICON_JX = int(30 * SCALE)
GAP_JX_PILL = int(22 * SCALE)
GAP_PILL_LB = int(26 * SCALE)

# Tailles de police (finales) → on multiplie par SCALE pour le rendu HD
JX_SIZE_FINAL    = 88   # "J - X" très grand
DATE_SIZE_FINAL  = 36   # pastille date
LABEL_SIZE_FINAL = 44   # libellé en bas

# Polices dispo sur les runners Ubuntu
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# ───────────── Utilitaires ─────────────
MONTHS_FR = ["janvier","février","mars","avril","mai","juin","juillet","août",
             "septembre","octobre","novembre","décembre"]
def format_date_fr(d: dt.date) -> str:
    return f"{d.day} {MONTHS_FR[d.month-1]} {d.year}"

def hex_to_rgba(hex_color, a=255):
    h = hex_color.lstrip("#")
    return (int(h[0:2],16), int(h[2:4],16), int(h[4:6],16), a)

def pill_color(hex_color, factor=0.26, alpha=240):
    # pastille un peu plus foncée que la carte
    r,g,b,_ = hex_to_rgba(hex_color)
    return (int(r*(1-factor)), int(g*(1-factor)), int(b*(1-factor)), alpha)

def load_icon(filename, size):
    path = os.path.join(os.path.dirname(__file__), filename)
    img = Image.open(path).convert("RGBA")
    return img.resize((size, size), Image.LANCZOS)

def text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont):
    b = draw.textbbox((0,0), text, font=font)  # [x0,y0,x1,y1]
    return b[2]-b[0], b[3]-b[1]

# ───────────── Rendu d’une carte ─────────────
def draw_card(event: dict, today: dt.date) -> Image.Image:
    card = Image.new("RGBA", (CARD_W, CARD_H), (0,0,0,0))
    d = ImageDraw.Draw(card)

    # fond arrondi plein
    d.rounded_rectangle((0,0,CARD_W,CARD_H), RADIUS, fill=hex_to_rgba(event["color"]))

    # zone utile & centre
    x0,y0 = PAD_X, PAD_TOP
    x1,y1 = CARD_W - PAD_X, CARD_H - PAD_BOTTOM
    cx = (x0 + x1) // 2

    # icône
    icon = load_icon(event["icon"], ICON_SIZE)
    icon_y = y0
    card.paste(icon, (cx - ICON_SIZE//2, icon_y), icon)

    # J - X (très grand, centré)
    delta = (event["date"] - today).days
    if   delta > 1: jtxt = f"J - {delta}"
    elif delta == 1: jtxt = "J - 1"
    elif delta == 0: jtxt = "J - 0"  # on garde la cohérence “J - X” visuelle
    else:            jtxt = "PASSÉ"

    f_jx = ImageFont.truetype(FONT_BOLD, JX_SIZE_FINAL * SCALE)
    wj, hj = text_size(d, jtxt, f_jx)
    jy = icon_y + ICON_SIZE + GAP_ICON_JX
    d.text((cx - wj//2, jy), jtxt, font=f_jx, fill=(255,255,255,255))

    # Pastille date (grande et bien ronde)
    date_str = format_date_fr(event["date"])
    f_date = ImageFont.truetype(FONT_BOLD, DATE_SIZE_FINAL * SCALE)
    tw, th = text_size(d, date_str, f_date)
    pad_x, pad_y = int(20*SCALE), int(12*SCALE)
    pill_w, pill_h = tw + pad_x*2, th + pad_y*2
    px = cx - pill_w//2
    py = jy + hj + GAP_JX_PILL
    d.rounded_rectangle((px, py, px+pill_w, py+pill_h), pill_h//2, fill=pill_color(event["color"]))
    d.text((cx - tw//2, py + pad_y - int(2*SCALE)), date_str, font=f_date, fill=(255,255,255,255))

    # Libellé (gros)
    f_lbl = ImageFont.truetype(FONT_BOLD, LABEL_SIZE_FINAL * SCALE)
    lw, lh = text_size(d, event["name"], f_lbl)
    ly = py + pill_h + GAP_PILL_LB
    # sécurité si jamais ça touche le bas
    if ly + lh > y1:
        # réduit très légèrement
        f_lbl = ImageFont.truetype(FONT_BOLD, int(LABEL_SIZE_FINAL * 0.95) * SCALE)
        lw, lh = text_size(d, event["name"], f_lbl)
        ly = min(ly, y1 - lh)
    d.text((cx - lw//2, ly), event["name"], font=f_lbl, fill=(255,255,255,255))

    return card

# ───────────── Construction de l’image ─────────────
def build_image(today: dt.date) -> Image.Image:
    canvas = Image.new("RGBA", (W, H), (0,0,0,0))  # fond transparent
    x = 0
    for i, ev in enumerate(EVENTS):
        card = draw_card(ev, today)
        canvas.paste(card, (x, 0), card)
        x += CARD_W + (GAP_CARDS if i == 0 else 0)

    # downscale 2× → texte & icônes très nets
    final = canvas.resize((FINAL_W, FINAL_H), Image.LANCZOS)
    return final

# ───────────── Envoi Discord (@everyone) ─────────────
def send_to_discord(img: Image.Image):
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        raise RuntimeError("DISCORD_WEBHOOK_URL manquant (secret GitHub).")

    buf = io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    files = {"file": ("countdowns.png", buf, "image/png")}
    payload = {
        "username": "Compte à rebours",
        "content": "@everyone",
        "allowed_mentions": {"parse": ["everyone"]},
        "embeds": [{ "image": {"url": "attachment://countdowns.png"} }]
    }
    import json
    r = requests.post(webhook, data={"payload_json": json.dumps(payload)}, files=files, timeout=30)
    r.raise_for_status()

# ───────────── Point d’entrée (daily.yml appelle run()) ─────────────
def run():
    # date locale Europe/Paris si dispo
    try:
        from zoneinfo import ZoneInfo
        today = dt.datetime.now(ZoneInfo("Europe/Paris")).date()
    except Exception:
        today = dt.date.today()
    img = build_image(today)
    send_to_discord(img)

if __name__ == "__main__":
    run()
