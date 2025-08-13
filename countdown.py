from datetime import datetime, date
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont
import requests

# -------------------------
# Config
# -------------------------
EVENTS = [
    {
        "name": "Signature du bail",
        "date": date(2025, 8, 22),
        "color": "#f9c068",
        "icon": "calendrier.png"
    },
    {
        "name": "Emménagement",
        "date": date(2025, 8, 30),
        "color": "#438c55",
        "icon": "home-sweet-home.png"
    }
]

DISCORD_WEBHOOK_URL = "<WEBHOOK ICI>"  # ⚠️ OU via secret GitHub

# -------------------------
# Fonctions
# -------------------------
def create_card(event, today):
    # Dimensions
    card_w, card_h = 300, 400
    radius = 30

    # Image transparente
    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    # Fond avec coins arrondis
    draw.rounded_rectangle(
        [(0, 0), (card_w, card_h)],
        radius=radius,
        fill=event["color"]
    )

    # Charger et redimensionner l'icône
    icon = Image.open(event["icon"]).convert("RGBA")
    icon_size = 90  # plus petit qu'avant
    icon = icon.resize((icon_size, icon_size), Image.LANCZOS)
    icon_x = (card_w - icon_size) // 2
    card.paste(icon, (icon_x, 30), icon)

    # Police
    font_big = ImageFont.truetype("arial.ttf", 48)
    font_date = ImageFont.truetype("arial.ttf", 24)
    font_small = ImageFont.truetype("arial.ttf", 26)

    # Calcul J-X
    days_left = (event["date"] - today).days
    jx_text = f"J - {days_left}"
    w, h = draw.textsize(jx_text, font=font_big)
    draw.text(((card_w - w) / 2, 140), jx_text, font=font_big, fill="white")

    # Pastille date
    date_str = event["date"].strftime("%d %B %Y")
    pastille_w, pastille_h = draw.textsize(date_str, font=font_date)
    pastille_padding = 10
    pastille_x = (card_w - pastille_w - pastille_padding*2) / 2
    pastille_y = 210
    draw.rounded_rectangle(
        [
            (pastille_x, pastille_y),
            (pastille_x + pastille_w + pastille_padding*2, pastille_y + pastille_h + 6)
        ],
        radius=15,
        fill=(0, 0, 0, 60)  # noir transparent
    )
    draw.text((card_w/2 - pastille_w/2, pastille_y+3), date_str, font=font_date, fill="white")

    # Nom de l'événement
    w_name, h_name = draw.textsize(event["name"], font=font_small)
    draw.text(((card_w - w_name) / 2, 280), event["name"], font=font_small, fill="white")

    return card

def create_image():
    today = date.today()

    # Taille totale
    spacing = 40
    card_width = 300
    total_w = card_width * len(EVENTS) + spacing * (len(EVENTS) - 1)
    total_h = 400

    img = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

    # Ajouter chaque carte
    for i, event in enumerate(EVENTS):
        card = create_card(event, today)
        img.paste(card, (i * (card_width + spacing), 0), card)

    return img

def send_to_discord(image):
    import io
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)

    files = {"file": ("countdown.png", buffer, "image/png")}
    data = {"content": "⏳ **Comptes à rebours du jour**"}
    requests.post(DISCORD_WEBHOOK_URL, data=data, files=files)

# -------------------------
# Main
# -------------------------
if __name__ == "__main__":
    img = create_image()
    send_to_discord(img)
