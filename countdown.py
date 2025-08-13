# countdown.py
import os, io, math, datetime as dt, requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --------- PARAMS ---------
WEBHOOK = os.environ["DISCORD_WEBHOOK_URL"]
EVENTS = [
    # (label, date ISO, icon_type, gradient_left(hex), gradient_right(hex))
    ("Signature du bail", "2025-08-22", "calendar", "#ff7a6e", "#ff5db1"),  # rose/corail
    ("Emménagement",      "2025-08-30", "home",     "#21d4fd", "#28e06e"),  # cyan/vert
]
BG = "#1f232b"    # fond sombre derrière les cartes
W, H = 1024, 512  # taille de l'image finale (adaptée aux aperçus Discord)
M = 28            # marge extérieure
CARD_R = 44       # rayon des coins des cartes
# --------------------------

# --- util couleurs ---
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0,2,4))

def lerp(a,b,t): return a + (b-a)*t

def grad_rect(size, c1, c2):
    w,h = size
    im = Image.new("RGB", (w,h), c1)
    p = im.load()
    c1 = hex_to_rgb(c1); c2 = hex_to_rgb(c2)
    for y in range(h):
        t = y/(h-1)
        r = int(lerp(c1[0], c2[0], t))
        g = int(lerp(c1[1], c2[1], t))
        b = int(lerp(c1[2], c2[2], t))
        for x in range(w):
            p[x,y] = (r,g,b)
    return im

# --- formes ---
def rounded(img, r):
    mask = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(mask)
    w,h = img.size
    d.rounded_rectangle((0,0,w,h), r, fill=255)
    out = Image.new("RGBA", img.size)
    out.paste(img, (0,0), mask)
    return out

def soft_shadow(size, r=50, spread=1.8, alpha=110):
    w,h = size
    base = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(base)
    d.rounded_rectangle((r,r,w-r,h-r), r, fill=alpha)
    return base.filter(ImageFilter.GaussianBlur(radius=r*spread))

# --- typographies (Ubuntu runner possède DejaVu) ---
def font_b(size): return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)
def font_r(size): return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)

# --- icônes vectorielles simples (dessinées à la main) ---
def draw_calendar(draw, cx, cy, scale, fill):
    # corps
    w,h = int(180*scale), int(150*scale)
    x0,y0 = cx-w//2, cy-h//2+15
    draw.rounded_rectangle((x0,y0,x0+w,y0+h), radius=int(24*scale), fill=fill)
    # anneaux
    ring_w = int(24*scale)
    draw.rectangle((x0+int(28*scale), y0-int(30*scale), x0+int(60*scale), y0), fill=fill)
    draw.rectangle((x0+w-int(60*scale), y0-int(30*scale), x0+w-int(28*scale), y0), fill=fill)
    # cases
    cell = int(22*scale); gap = int(10*scale)
    ox, oy = x0+int(24*scale), y0+int(24*scale)
    for r in range(2):
        for c in range(4):
            x = ox + c*(cell+gap)
            y = oy + r*(cell+gap)
            draw.rounded_rectangle((x,y,x+cell,y+cell), radius=int(5*scale), fill=(255,255,255,80))

def draw_home(draw, cx, cy, scale, fill):
    s = int(180*scale)
    # toit (triangle)
    p = [(cx, cy-s//2), (cx-s//2, cy), (cx+s//2, cy)]
    draw.polygon(p, fill=fill)
    # maison
    w, h = int(160*scale), int(120*scale)
    x0,y0 = cx-w//2, cy
    draw.rectangle((x0, y0, x0+w, y0+h), fill=fill)
    # porte
    dw, dh = int(46*scale), int(60*scale)
    dx = cx - dw//2
    draw.rectangle((dx, y0+h-dh, dx+dw, y0+h), fill=(BG_RGB))

# --- dates & deltas ---
try:
    from zoneinfo import ZoneInfo
    PARIS = ZoneInfo("Europe/Paris")
except Exception:
    PARIS = None

now_utc = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
today = now_utc.astimezone(PARIS).date() if PARIS else dt.date.today()

def delta_days(date_iso):
    d = dt.date.fromisoformat(date_iso)
    return (d - today).days, d

# --- canvas principal ---
BG_RGB = hex_to_rgb(BG)
canvas = Image.new("RGB", (W,H), BG_RGB)
draw = ImageDraw.Draw(canvas)

# positions des 2 cartes
cols = 2
gap = 28
card_w = (W - 2*M - gap) // cols
card_h = H - 2*M
x_positions = [M, M + card_w + gap]

for i,(label, date_iso, icon, c1, c2) in enumerate(EVENTS[:2]):
    # gradients + carte
    base = grad_rect((card_w, card_h), c1, c2)
    card = rounded(base, CARD_R)

    # ombre douce
    sh = soft_shadow((card_w+80, card_h+80))
    sh_img = Image.new("RGBA", (card_w+80, card_h+80), (0,0,0,0))
    sh_img.putalpha(sh)
    canvas.paste(sh_img, (x_positions[i]-40, M-20), sh_img)

    canvas.paste(card, (x_positions[i], M), card)

    # contenus
    d2 = ImageDraw.Draw(canvas)

    # delta
    delta, dobj = delta_days(date_iso)
    if   delta > 1:  jtxt = f"J - {delta}"
    elif delta == 1: jtxt = "J - 1"
    elif delta == 0: jtxt = "AUJOURD’HUI"
    else:            jtxt = "PASSÉ"

    # icône
    cx = x_positions[i] + card_w//2
    top = M + int(card_h*0.18)
    if icon == "calendar":
        draw_calendar(d2, cx, top, 1.0, fill=(255,255,255,220))
    else:
        draw_home(d2, cx, top, 1.0, fill=(255,255,255,220))

    # J - X
    fs = 88 if len(jtxt) <= 6 else 76
    wj, hj = d2.textbbox((0,0), jtxt, font=font_b(fs))[2:]
    d2.text((cx-wj//2, top+140), jtxt, font=font_b(fs), fill="white")

    # pastille date
    date_str = dobj.strftime("%d %B %Y").lower()
    pill_pad_x, pill_pad_y = 26, 10
    fw = font_b(34)
    tw, th = d2.textbbox((0,0), date_str, font=fw)[2:]
    pill_w, pill_h = tw + pill_pad_x*2, th + pill_pad_y*2
    pill = Image.new("RGBA", (pill_w, pill_h), (255,255,255,38))
    pill = rounded(pill, pill_h//2)
    px = cx - pill_w//2
    py = top + 140 + hj + 24
    canvas.paste(pill, (px, py), pill)
    d2.text((cx - tw//2, py + pill_pad_y - 3), date_str, font=fw, fill="white")

    # label
    f2 = font_b(40)
    lw, lh = d2.textbbox((0,0), label, font=f2)[2:]
    d2.text((cx-lw//2, py + pill_h + 22), label, font=f2, fill="white")

# Envoi au webhook (upload fichier + embed image)
buf = io.BytesIO()
canvas.save(buf, format="PNG")
buf.seek(0)

files = {
    "file": ("countdowns.png", buf, "image/png")
}
data = {
    "username": "Compte à rebours",
    "embeds": [{
        "image": {"url": "attachment://countdowns.png"},
        "color": 0x5865F2,  # violet Discord, décoratif
    }]
}

r = requests.post(WEBHOOK, data={"payload_json": __import__("json").dumps(data)}, files=files, timeout=30)
r.raise_for_status()
