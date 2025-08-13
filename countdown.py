# countdown.py
import os, io, datetime as dt, requests
from PIL import Image, ImageDraw, ImageFont

# ───────────────────── CONFIG ─────────────────────
WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]

EVENTS = [
    # (label, date ISO, icon: 'calendar' | 'house', hex card color)
    ("Signature du bail", "2025-08-22", "calendar", "#f9c068"),
    ("Emménagement",      "2025-08-30", "house",    "#438c55"),
]

# Image finale (fond TRANSPARENT)
W, H   = 1024, 512
M      = 24           # marge extérieure
GAP    = 28           # espace entre cartes
CARD_R = 44           # rayon des coins
PAD_X  = 28           # padding interne des cartes
PAD_TOP, PAD_BOTTOM = 34, 28

# Icônes (taille cible dans la carte)
ICON_W, ICON_H = 120, 120  # SVG rasterisé ~2x plus petit qu'avant

# ───────────── util couleurs/forme ─────────────
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0,2,4))

def darken(hex_color, factor=0.22):
    """Assombrit légèrement la couleur pour la pastille date."""
    r,g,b = hex_to_rgb(hex_color)
    r = int(r * (1 - factor))
    g = int(g * (1 - factor))
    b = int(b * (1 - factor))
    return (r,g,b, 200)  # alpha pour pill (semi-opaque)

def rounded_rect_rgba(size, radius, fill_hex):
    """Carte pleine couleur avec coins arrondis (RGBA, fond transparent)."""
    w,h = size
    base = Image.new("RGBA", (w,h), (0,0,0,0))
    shape = Image.new("L", (w,h), 0)
    d = ImageDraw.Draw(shape)
    d.rounded_rectangle((0,0,w,h), radius, fill=255)
    card = Image.new("RGBA", (w,h), hex_to_rgb(fill_hex)+(255,))
    base.paste(card, (0,0), shape)
    return base

# ───────────── polices (runners Ubuntu) ─────────────
def font_b(sz): return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", sz)
def font_r(sz): return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", sz)

# ───────────── icônes SVG → PNG (CairoSVG) ─────────────
from cairosvg import svg2png

SVG_CALENDAR = """
<svg width="128" height="128" viewBox="0 0 128 128" fill="none"
     xmlns="http://www.w3.org/2000/svg">
  <rect x="16" y="28" width="96" height="84" rx="12" fill="white" stroke="#1e1e1e" stroke-width="6"/>
  <rect x="16" y="28" width="96" height="20" rx="6" fill="#1e1e1e"/>
  <rect x="32" y="8" width="16" height="24" rx="8" fill="#1e1e1e"/>
  <rect x="80" y="8" width="16" height="24" rx="8" fill="#1e1e1e"/>
  <!-- petites cases -->
  <g fill="#1e1e1e">
    <rect x="32" y="58" width="16" height="12" rx="4"/>
    <rect x="56" y="58" width="16" height="12" rx="4"/>
    <rect x="80" y="58" width="16" height="12" rx="4"/>
    <rect x="32" y="78" width="16" height="12" rx="4"/>
    <rect x="56" y="78" width="16" height="12" rx="4"/>
    <rect x="80" y="78" width="16" height="12" rx="4"/>
    <rect x="32" y="98" width="16" height="12" rx="4"/>
    <rect x="56" y="98" width="16" height="12" rx="4"/>
    <rect x="80" y="98" width="16" height="12" rx="4"/>
  </g>
</svg>
"""

SVG_HOUSE = """
<svg width="128" height="128" viewBox="0 0 128 128" fill="none"
     xmlns="http://www.w3.org/2000/svg">
  <!-- toit -->
  <polygon points="20,64 64,28 108,64" fill="#e25d60" stroke="#c24a4d" stroke-width="6" stroke-linejoin="round"/>
  <!-- corps -->
  <rect x="28" y="60" width="72" height="56" rx="8" fill="#f2e0bd" stroke="#c19a6b" stroke-width="6"/>
  <!-- porte -->
  <rect x="58" y="84" width="18" height="32" rx="4" fill="#775b4b"/>
  <!-- fenêtre -->
  <rect x="72" y="76" width="20" height="14" rx="3" fill="#7dd3fc" stroke="#388fb7" stroke-width="5"/>
  <!-- jardinière -->
  <rect x="70" y="90" width="24" height="6" rx="3" fill="#2f855a"/>
</svg>
"""

def render_svg(svg_str, width, height):
    png_bytes = svg2png(bytestring=svg_str.encode("utf-8"), output_width=width, output_height=height, background_color=None)
    return Image.open(io.BytesIO(png_bytes)).convert("RGBA")

# ───────────── dates FR + fuseau ─────────────
try:
    from zoneinfo import ZoneInfo
    PARIS = ZoneInfo("Europe/Paris")
except Exception:
    PARIS = None

MONTHS_FR = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]
def format_date_fr(d: dt.date):
    return f"{d.day} {MONTHS_FR[d.month-1]} {d.year}"

now_utc = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
now_paris = now_utc.astimezone(PARIS) if PARIS else now_utc
today = now_paris.date()

# ───────────── canvas global (TRANSPARENT) ─────────────
canvas = Image.new("RGBA", (W,H), (0,0,0,0))

# géométrie des cartes
card_w = (W - 2*M - GAP) // 2
card_h = H - 2*M
x_positions = [M, M + card_w + GAP]

def draw_card(card_color, label, date_iso, icon_name):
    # carte de base
    card = rounded_rect_rgba((card_w, card_h), CARD_R, card_color)
    d = ImageDraw.Draw(card)

    # zone utile interne
    x0, y0 = PAD_X, PAD_TOP
    x1, y1 = card_w - PAD_X, card_h - PAD_BOTTOM
    cx = (x0 + x1) // 2

    # icône
    svg = SVG_CALENDAR if icon_name == "calendar" else SVG_HOUSE
    icon = render_svg(svg, ICON_W, ICON_H)
    icon_y = y0
    card.paste(icon, (cx - ICON_W//2, icon_y), icon)

    # delta J - X
    target = dt.date.fromisoformat(date_iso)
    delta = (target - today).days
    if   delta > 1:  jtxt = f"J - {delta}"
    elif delta == 1: jtxt = "J - 1"
    elif delta == 0: jtxt = "AUJOURD’HUI"
    else:            jtxt = "PASSÉ"

    fs = 72 if len(jtxt) <= 9 else 64
    wj, hj = d.textbbox((0,0), jtxt, font=font_b(fs))[2:]
    jy = icon_y + ICON_H + 18
    d.text((cx - wj//2, jy), jtxt, font=font_b(fs), fill=(255,255,255,255))

    # pastille date (couleur = card assombrie)
    date_str = format_date_fr(target)
    fdate = font_b(30)
    tw, th = d.textbbox((0,0), date_str, font=fdate)[2:]
    pill_pad_x, pill_pad_y = 22, 8
    pill_w, pill_h = tw + pill_pad_x*2, th + pill_pad_y*2
    pill = Image.new("RGBA", (pill_w, pill_h), darken(card_color, 0.28))
    # arrondi pastille
    mask = Image.new("L", (pill_w, pill_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,pill_w,pill_h), radius=pill_h//2, fill=255)
    px = cx - pill_w//2
    py = jy + hj + 16
    card.paste(pill, (px, py), mask)
    d.text((cx - tw//2, py + pill_pad_y - 2), date_str, font=fdate, fill=(255,255,255,255))

    # label
    flab = font_b(36)
    lw, lh = d.textbbox((0,0), label, font=flab)[2:]
    ly = py + pill_h + 14
    # si trop bas, réduit un peu
    if ly + lh > y1:
        flab = font_b(32)
        lw, lh = d.textbbox((0,0), label, font=flab)[2:]
        ly = min(ly, y1 - lh)
    d.text((cx - lw//2, ly), label, font=flab, fill=(255,255,255,255))

    return card

# dessiner et coller les deux cartes (aucun débordement)
for i,(label, date_iso, icon, color) in enumerate(EVENTS[:2]):
    card_img = draw_card(color, label, date_iso, icon)
    canvas.paste(card_img, (x_positions[i], M), card_img)

# ───────────── envoi Discord (image attachée) ─────────────
buf = io.BytesIO()
canvas.save(buf, format="PNG")
buf.seek(0)

files = {"file": ("countdowns.png", buf, "image/png")}
payload = {
    "username": "Compte à rebours",
    "embeds": [{ "image": { "url": "attachment://countdowns.png" } }]
}
import json
r = requests.post(WEBHOOK, data={"payload_json": json.dumps(payload)}, files=files, timeout=30)
r.raise_for_status()
