# countdown.py — fond transparent, centrage vertical parfait, rendu net (×2), @everyone
import os, io, datetime as dt, requests
from PIL import Image, ImageDraw, ImageFont

# ───────────── Événements ─────────────
EVENTS = [
    {"name": "Signature du bail", "date": dt.date(2025, 8, 22), "color": "#f9c068", "icon": "calendrier.png"},
    {"name": "Emménagement",      "date": dt.date(2025, 8, 30), "color": "#438c55", "icon": "home-sweet-home.png"},
]

# ───────────── Taille & rendu ─────────────
FINAL_W, FINAL_H = 1024, 512   # format de ta maquette
SCALE            = 2           # supersampling pour une typographie nette
W, H             = FINAL_W * SCALE, FINAL_H * SCALE

# Cartes
GAP_CARDS = int(40 * SCALE)            # espace entre les 2 cartes
CARD_W    = (W - GAP_CARDS) // 2
CARD_H    = H
RADIUS    = int(46 * SCALE)

# Tailles et espacements internes (calés sur ton rendu)
ICON_SIZE        = int(CARD_H * 0.23)
GAP_ICON_JX      = int(30 * SCALE)
GAP_JX_PILL      = int(22 * SCALE)
GAP_PILL_LABEL   = int(26 * SCALE)

# Polices (Ubuntu runner)
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
SIZE_JX_FINAL    = 88   # px (final) pour "J - X"
SIZE_DATE_FINAL  = 36   # px (final) pour la pastille
SIZE_LABEL_FINAL = 44   # px (final) pour le libellé

# ───────────── Utils ─────────────
MONTHS_FR = ["janvier","février","mars","avril","mai","juin","juillet","août",
             "septembre","octobre","novembre","décembre"]
def format_date_fr(d: dt.date) -> str:
    return f"{d.day} {MONTHS_FR[d.month-1]} {d.year}"

def hex_to_rgba(hx, a=255):
    hx = hx.lstrip("#"); return (int(hx[0:2],16), int(hx[2:4],16), int(hx[4:6],16), a)

def pill_color(hex_color, factor=0.26, alpha=240):
    r,g,b,_ = hex_to_rgba(hex_color)
    return (int(r*(1-factor)), int(g*(1-factor)), int(b*(1-factor)), alpha)

def load_icon(path, size):
    p = os.path.join(os.path.dirname(__file__), path)
    im = Image.open(p).convert("RGBA")
    return im.resize((size, size), Image.LANCZOS)

def text_size(draw, text, font):
    x0,y0,x1,y1 = draw.textbbox((0,0), text, font=font)
    return (x1-x0, y1-y0)

# ───────────── Une carte, centrage vertical uniforme ─────────────
def draw_card(event: dict, today: dt.date) -> Image.Image:
    card = Image.new("RGBA", (CARD_W, CARD_H), (0,0,0,0))
    d = ImageDraw.Draw(card)

    # fond arrondi plein
    d.rounded_rectangle((0,0,CARD_W,CARD_H), RADIUS, fill=hex_to_rgba(event["color"]))

    # contenus (on calcule d'abord la hauteur totale pour centrer le bloc)
    # 1) icône
    icon = load_icon(event["icon"], ICON_SIZE)
    icon_h = ICON_SIZE

    # 2) J - X
    delta = (event["date"] - today).days
    jtxt = f"J - {max(delta, 0)}" if delta >= 0 else "PASSÉ"
    f_jx = ImageFont.truetype(FONT_BOLD, SIZE_JX_FINAL * SCALE)
    wj, hj = text_size(d, jtxt, f_jx)

    # 3) pastille date
    date_txt = format_date_fr(event["date"])
    f_date   = ImageFont.truetype(FONT_BOLD, SIZE_DATE_FINAL * SCALE)
    tw, th   = text_size(d, date_txt, f_date)
    pad_x, pad_y = int(20*SCALE), int(12*SCALE)
    pill_w, pill_h = tw + pad_x*2, th + pad_y*2

    # 4) libellé
    f_lbl = ImageFont.truetype(FONT_BOLD, SIZE_LABEL_FINAL * SCALE)
    lw, lh = text_size(d, event["name"], f_lbl)

    # Hauteur totale du bloc (icône + gaps + JX + gap + pastille + gap + label)
    total_h = icon_h + GAP_ICON_JX + hj + GAP_JX_PILL + pill_h + GAP_PILL_LABEL + lh

    # Y de départ pour centrer verticalement dans la carte
    start_y = (CARD_H - total_h) // 2
    cx = CARD_W // 2

    # Placement réel :
    y = start_y
    # icône (centrée)
    card.paste(icon, (cx - ICON_SIZE//2, y), icon); y += icon_h + GAP_ICON_JX
    # J - X
    d.text((cx - wj//2, y), jtxt, font=f_jx, fill=(255,255,255,255)); y += hj + GAP_JX_PILL
    # pastille date
    px = cx - pill_w//2
    d.rounded_rectangle((px, y, px+pill_w, y+pill_h), pill_h//2, fill=pill_color(event["color"]))
    d.text((cx - tw//2, y + pad_y - int(2*SCALE)), date_txt, font=f_date, fill=(255,255,255,255))
    y += pill_h + GAP_PILL_LABEL
    # libellé
    d.text((cx - lw//2, y), event["name"], font=f_lbl, fill=(255,255,255,255))

    return card

# ───────────── Assemblage & envoi ─────────────
def build_image(today: dt.date) -> Image.Image:
    canvas2x = Image.new("RGBA", (W, H), (0,0,0,0))  # fond transparent
    x = 0
    for i, ev in enumerate(EVENTS):
        card = draw_card(ev, today)
        canvas2x.paste(card, (x, 0), card)
        x += CARD_W + (GAP_CARDS if i == 0 else 0)
    # downscale pour netteté
    return canvas2x.resize((FINAL_W, FINAL_H), Image.LANCZOS)

def send_to_discord(img: Image.Image):
    webhook = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook:
        raise RuntimeError("DISCORD_WEBHOOK_URL manquant (secret GitHub).")
    buf = io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    files = {"file": ("countdowns.png", buf, "image/png")}
    payload = {
        "username": "Jour J",
        "content": "@everyone",
        "allowed_mentions": {"parse": ["everyone"]},
        "embeds": [{ "image": {"url": "attachment://countdowns.png"} }]
    }
    import json
    r = requests.post(webhook, data={"payload_json": json.dumps(payload)}, files=files, timeout=30)
    r.raise_for_status()

def run():
    try:
        from zoneinfo import ZoneInfo
        today = dt.datetime.now(ZoneInfo("Europe/Paris")).date()
    except Exception:
        today = dt.date.today()
    img = build_image(today)
    send_to_discord(img)

if __name__ == "__main__":
    run()
