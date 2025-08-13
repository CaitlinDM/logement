# countdown.py
import os, io, datetime as dt, requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ─────────────────────── CONFIG ───────────────────────
WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]

EVENTS = [
    # (label, date ISO, icon, left color, right color)
    ("Signature du bail", "2025-08-22", "calendar", "#ff7a6e", "#ff5db1"),  # rose/corail
    ("Emménagement",      "2025-08-30", "home",     "#21d4fd", "#28e06e"),  # cyan/vert
]

# image finale
W, H   = 1024, 512          # taille globale (aperçu Discord)
M      = 28                 # marge extérieure
GAP    = 28                 # espace entre cartes
CARD_R = 44                 # rayon coins cartes
BG     = "#202329"          # fond sombre (rien ne doit dépasser dessus)

# Mise en page interne de chaque carte (padding)
PAD_TOP    = 36
PAD_BOTTOM = 30
PAD_X      = 28

# Icônes 2x plus petites (scale 0.5 au lieu de 1.0)
ICON_SCALE = 0.5

# ───────────────── util couleur/forme ─────────────────
def hex_to_rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i+2],16) for i in (0,2,4))
def lerp(a,b,t): return a + (b-a)*t

def grad_rect(size, c1, c2):
    w,h = size
    im = Image.new("RGB", (w,h), c1); px = im.load()
    c1, c2 = hex_to_rgb(c1), hex_to_rgb(c2)
    for y in range(h):
        t = y/(h-1)
        r = int(lerp(c1[0], c2[0], t)); g = int(lerp(c1[1], c2[1], t)); b = int(lerp(c1[2], c2[2], t))
        for x in range(w): px[x,y] = (r,g,b)
    return im

def rounded(img, r):
    """Retourne une image RGBA avec coins arrondis et alpha correct (pour coller sans débordement)."""
    mask = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(mask); d.rounded_rectangle([0,0,*img.size], r, fill=255)
    out = Image.new("RGBA", img.size)
    out.paste(img, (0,0), mask)
    return out

# ─────────────── fonts (présentes sur runner) ───────────────
def font_b(sz): return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", sz)
def font_r(sz): return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", sz)

# ─────────────────────── icônes blanches ─────────────────────
def draw_calendar(draw, cx, cy, scale=1.0):
    # bloc principal
    w,h = int(180*scale), int(150*scale)
    x0,y0 = cx-w//2, cy-h//2+8
    draw.rounded_rectangle((x0,y0,x0+w,y0+h), radius=int(24*scale), fill=(255,255,255))
    # anneaux
    draw.rectangle((x0+int(28*scale), y0-int(24*scale), x0+int(60*scale), y0), fill=(255,255,255))
    draw.rectangle((x0+w-int(60*scale), y0-int(24*scale), x0+w-int(28*scale), y0), fill=(255,255,255))

def draw_home(draw, cx, cy, scale=1.0):
    s = int(180*scale)
    # toit
    draw.polygon([(cx, cy-s//2), (cx-s//2, cy), (cx+s//2, cy)], fill=(255,255,255))
    # corps
    w, h = int(160*scale), int(120*scale)
    x0,y0 = cx-w//2, cy
    draw.rectangle((x0, y0, x0+w, y0+h), fill=(255,255,255))

# ────────────────── dates FR + fuseau Paris ──────────────────
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

# ────────────────────── canvas global ────────────────────────
BG_RGB = hex_to_rgb(BG)
canvas = Image.new("RGB", (W,H), BG_RGB)

# calcul cartes (2 colonnes)
card_w = (W - 2*M - GAP) // 2
card_h = H - 2*M

def draw_card(label, date_iso, icon, c1, c2):
    """Retourne une carte RGBA auto-contenue (rien ne dépasse)."""
    # base carte
    base = grad_rect((card_w, card_h), c1, c2)
    card = rounded(base, CARD_R)  # RGBA coin arrondi
    # on dessine TOUT à l'intérieur de 'card'
    d = ImageDraw.Draw(card)

    # aire utile interne (pour éviter les bords)
    usable_x0, usable_y0 = PAD_X, PAD_TOP
    usable_x1, usable_y1 = card_w - PAD_X, card_h - PAD_BOTTOM
    cx = (usable_x0 + usable_x1) // 2

    # delta
    target = dt.date.fromisoformat(date_iso)
    delta = (target - today).days
    if   delta > 1:  jtxt = f"J - {delta}"
    elif delta == 1: jtxt = "J - 1"
    elif delta == 0: jtxt = "AUJOURD’HUI"
    else:            jtxt = "PASSÉ"

    # icône (2x plus petite)
    top_icon = usable_y0 + 4
    if icon == "calendar":
        draw_calendar(d, cx, top_icon + int(90*ICON_SCALE), ICON_SCALE)
    else:
        draw_home(d, cx, top_icon + int(90*ICON_SCALE), ICON_SCALE)

    # J - X
    fs = 92 if len(jtxt) <= 7 else 80
    j_bbox = d.textbbox((0,0), jtxt, font=font_b(fs))
    j_w, j_h = j_bbox[2]-j_bbox[0], j_bbox[3]-j_bbox[1]
    j_y = top_icon + int(180*ICON_SCALE) + 16
    d.text((cx - j_w//2, j_y), jtxt, font=font_b(fs), fill="white")

    # pastille date
    date_str = format_date_fr(target)
    fw = font_b(34)
    tw, th = d.textbbox((0,0), date_str, font=fw)[2:]
    pill_pad_x, pill_pad_y = 26, 10
    pill_w, pill_h = tw + pill_pad_x*2, th + pill_pad_y*2
    pill = Image.new("RGBA", (pill_w, pill_h), (255,255,255,38))
    # arrondi pastille
    mask = Image.new("L", (pill_w, pill_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,pill_w,pill_h), radius=pill_h//2, fill=255)
    px = cx - pill_w//2
    py = j_y + j_h + 22
    card.paste(pill, (px, py), mask)
    d.text((cx - tw//2, py + pill_pad_y - 3), date_str, font=fw, fill="white")

    # label
    lbl_f = font_b(40)
    lw, lh = d.textbbox((0,0), label, font=lbl_f)[2:]
    label_y = py + pill_h + 18
    # clamp si ça dépasse (on réduit la police si nécessaire)
    if label_y + lh > usable_y1:
        lbl_f = font_b(36)
        lw, lh = d.textbbox((0,0), label, font=lbl_f)[2:]
        label_y = min(label_y, usable_y1 - lh)
    d.text((cx - lw//2, label_y), label, font=lbl_f, fill="white")

    return card

# dessiner et coller les cartes (sans ombres externes, sans débordement)
x_positions = [M, M + card_w + GAP]
for i, (label, date_iso, icon, c1, c2) in enumerate(EVENTS[:2]):
    card_img = draw_card(label, date_iso, icon, c1, c2)
    canvas.paste(card_img, (x_positions[i], M), card_img)  # collage via alpha → rien ne dépasse

# envoi au webhook (image attachée dans l'embed)
buf = io.BytesIO(); canvas.save(buf, format="PNG"); buf.seek(0)
files = { "file": ("countdowns.png", buf, "image/png") }
payload = {
    "username": "Compte à rebours",
    "embeds": [{ "image": {"url": "attachment://countdowns.png"} }]
}
import json
r = requests.post(WEBHOOK, data={"payload_json": json.dumps(payload)}, files=files, timeout=30)
r.raise_for_status()
