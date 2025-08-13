from PIL import Image, ImageDraw, ImageFont
import datetime as dt
import requests
import os

# === CONFIG ===
EVENTS = [
    {"label": "Signature du bail", "date": (2025, 8, 22), "color": "#f9c068", "icon": "calendrier.png"},
    {"label": "Emménagement", "date": (2025, 8, 30), "color": "#438c55", "icon": "home-sweet-home.png"},
]

FONT_BOLD = ImageFont.truetype("arialbd.ttf", 48)
FONT_MEDIUM = ImageFont.truetype("arialbd.ttf", 36)
FONT_SMALL = ImageFont.truetype("arialbd.ttf", 28)

CARD_WIDTH, CARD_HEIGHT = 300, 340
PADDING = 20
ICON_SIZE = 80  # taille icône

def render_countdown():
    now = dt.date.today()

    cards = []
    for event in EVENTS:
        # calcul J-X
        event_date = dt.date(*event["date"])
        days_left = (event_date - now).days
        jx_text = f"J - {days_left}"

        # création carte
        card = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), event["color"])
        draw = ImageDraw.Draw(card)

        # icône
        icon = Image.open(event["icon"]).convert("RGBA")
        icon = icon.resize((ICON_SIZE, ICON_SIZE), Image.LANCZOS)

        # position icône centrée
        icon_x = (CARD_WIDTH - ICON_SIZE) // 2
        current_y = PADDING
        card.paste(icon, (icon_x, current_y), icon)
        current_y += ICON_SIZE + 15

        # J-X centré
        w, h = draw.textsize(jx_text, font=FONT_BOLD)
        draw.text(((CARD_WIDTH - w) / 2, current_y), jx_text, font=FONT_BOLD, fill="white")
        current_y += h + 10

        # date centrée dans bulle
        date_str = event_date.strftime("%d %B %Y").replace(" 0", " ")
        w, h = draw.textsize(date_str, font=FONT_MEDIUM)
        date_bg_width = w + 20
        date_bg_height = h + 10
        date_bg_x = (CARD_WIDTH - date_bg_width) / 2
        draw.rounded_rectangle(
            [date_bg_x, current_y, date_bg_x + date_bg_width, current_y + date_bg_height],
            radius=12,
            fill=(0, 0, 0, 100)
        )
        draw.text(
            ((CARD_WIDTH - w) / 2, current_y + 5),
            date_str,
            font=FONT_MEDIUM,
            fill="white"
        )
        current_y += date_bg_height + 15

        # label centré
        w, h = draw.textsize(event["label"], font=FONT_SMALL)
        draw.text(((CARD_WIDTH - w) / 2, current_y), event["label"], font=FONT_SMALL, fill="white")

        cards.append(card)

    # concat cartes
    total_width = len(cards) * (CARD_WIDTH + 20) - 20
    img = Image.new("RGBA", (total_width, CARD_HEIGHT), (0, 0, 0, 0))
    x_offset = 0
    for card in cards:
        img.paste(card, (x_offset, 0))
        x_offset += CARD_WIDTH + 20

    img.save("countdown.png")

def run():
    render_countdown()
    url = os.environ["DISCORD_WEBHOOK_URL"]
    with open("countdown.png", "rb") as f:
        requests.post(
            url,
            data={"content": "@everyone"},
            files={"file": f},
            timeout=20
        )

if __name__ == "__main__":
    run()
