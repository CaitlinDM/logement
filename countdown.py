# countdown.py
import os, io, datetime as dt, requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ────────────────────────── CONFIG ──────────────────────────
WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]

EVENTS = [
    # (label, date ISO, icon, left color, right color)
    ("Signature du bail", "2025-08-22", "calendar", "#ff7a6e", "#ff5db1"),  # rose/corail
    ("Emménagement",      "2025-08-30", "home",     "#21d4fd", "#28e06e"),  # cyan/vert
]

# image finale
W, H   = 1024, 512
M      = 28                       # marge
CARD_R = 44                       # coins arrondis
BG     = "#202329"                # fond autour des cartes

# ───────────────────── utilitaires visuels ───────────────────
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
    mask = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(mask); d.rounded_rectangle([0,0,*img.size], r, fill=255)
    out = Image.new("RGBA", img.size); out.paste(img, (0,0), mask); return out

def soft_shadow(size, r=50, spread=1.8, alpha=110):
    w,h = size; base = Image.new("L", (w,h), 0); d = ImageDraw.Draw(base)
    d.rounded_rectangle((r,r,w-r,h-r), r, fill=alpha)
    return base.filter(ImageFilter.GaussianBlur(radius=r*spread))

# fonts (présentes sur runners Ubuntu)
def font_b(sz): return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", sz)
def font_r(sz): return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", sz)

# icônes (blanches, pleines – pas de “porte” noire)
def draw_calendar(draw, cx, cy, scale=1.0):
    w,h = int(180*scale), int(150*scale)
    x0,y0 = cx-w//2, cy-h//2+15
    draw.rounded_rectangle((x0,y0,x0+w,y0+h), radius=int(24*scale), fill=(255,255,255))
    ring_w = int(24*scale)
    draw.rectangle((x0+int(28*scale), y0-int(30*scale), x0+int(60*scale), y0), fill=(255,255,255))
    draw.rectangle((x0+w-int(60*scale), y0-int(30*scale), x0+w-int(28*scale), y0), fill=(255,255,255))

def draw_home(draw, cx, cy, scale=1.0):
    s = int(180*scale)
    # toit
    draw.polygon([(cx, cy-s//2), (cx-s//2, cy), (cx+s//2, cy)], fill=(255,255,255))
    # corps
    w, h = int(160*scale), int(120*scale)
    x0,y0 = cx-w//2, cy
    draw.rectangle((x0, y0, x0+w, y0+h), fill=(255,255,255))

# ───────────────────── dates (FR + fuseau) ───────────────────
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

# ───────────────────── canvas & dessin ───────────────────────
BG_RGB = hex_to_rgb(BG)
canvas = Image.new("RGB", (W,H), BG_RGB)
draw = ImageDraw.Draw(canvas)

cols = 2; gap = 28
card_w = (W - 2*M - gap) // cols
card_h = H - 2*M
x_positions = [M, M + card_w + gap]

for i,(label, date_iso, icon, c1, c2) in enumerate(EVENTS[:2]):
    base = grad_rect((card_w, card_h), c1, c2)
    card = rounded(base, CARD_R)

    # ombre
    sh = soft_shadow((card_w+80, card_h+80))
    sh_img = Image.new("RGBA", (card_w+80, card_h+80), (0,0,0,0))
    sh_img.putalpha(sh); canvas.paste(sh_img, (x_positions[i]-40, M-20), sh_img)

    canvas.paste(card, (x_positions[i], M), card)

    d2 = ImageDraw.Draw(canvas)

    # delta
    target = dt.date.fromisoformat(date_iso)
    delta = (target - today).days
    if   delta > 1:  jtxt = f"J - {delta}"
    elif delta == 1: jtxt = "J - 1"
    elif delta == 0: jtxt = "AUJOURD’HUI"
    else:            jtxt = "PASSÉ"

    # icône
    cx = x_positions[i] + card_w//2
    top = M + int(card_h*0.18)
    if icon == "calendar": draw_calendar(d2, cx, top, 1.0)
    else:                  draw_home(d2, cx, top, 1.0)

    # J - X (gros)
    fs = 92 if len(jtxt) <= 7 else 80
    bbox = d2.textbbox((0,0), jtxt, font=font_b(fs))
    wj, hj = bbox[2]-bbox[0], bbox[3]-bbox[1]
    d2.text((cx-wj//2, top+140), jtxt, font=font_b(fs), fill="white")

    # pastille date (FR)
    date_str = format_date_fr(target)
    fw = font_b(34)
    tw, th = d2.textbbox((0,0), date_str, font=fw)[2:]
    pill_pad_x, pill_pad_y = 26, 10
    pill_w, pill_h = tw + pill_pad_x*2, th + pill_pad_y*2
    pill = Image.new("RGBA", (pill_w, pill_h), (255,255,255,38))
    pill = rounded(pill, pill_h//2)
    px = cx - pill_w//2; py = top + 140 + hj + 24
    canvas.paste(pill, (px, py), pill)
    d2.text((cx - tw//2, py + pill_pad_y - 3), date_str, font=fw, fill="white")

    # label en bas
    lbl_f = font_b(40)
    lw, lh = d2.textbbox((0,0), label, font=lbl_f)[2:]
    d2.text((cx-lw//2, py + pill_h + 22), label, font=lbl_f, fill="white")

# envoi au webhook (image attachée dans l’embed)
buf = io.BytesIO(); canvas.save(buf, format="PNG"); buf.seek(0)
files = { "file": ("countdowns.png", buf, "image/png") }
payload = {
    "username": "Compte à rebours",
    "embeds": [{ "image": {"url": "attachment://countdowns.png"} }]
}
import json
r = requests.post(WEBHOOK, data={"payload_json": json.dumps(payload)}, files=files, timeout=30)
r.raise_for_status()
