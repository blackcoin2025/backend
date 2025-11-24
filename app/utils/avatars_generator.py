import os
import hashlib
from PIL import Image, ImageDraw, ImageFont

GENERATED_DIR = "static/generated_avatars"


def generate_avatar(username: str) -> str:
    """
    Génère un avatar basé sur le username :
    - couleur unique selon hash SHA-256
    - initiale au centre
    """

    username = username.strip().lower()

    if not os.path.exists(GENERATED_DIR):
        os.makedirs(GENERATED_DIR)

    filename = f"{username}.png"
    path = os.path.join(GENERATED_DIR, filename)

    # Déjà généré → renvoi direct
    if os.path.isfile(path):
        return path

    # ------------------------ Couleur unique ------------------------
    h = int(hashlib.sha256(username.encode("utf-8")).hexdigest(), 16)
    bg_color = (
        (h >> 24) & 255,
        (h >> 16) & 255,
        (h >> 8) & 255
    )

    # ------------------------ Image ------------------------
    img = Image.new("RGB", (256, 256), color=bg_color)
    draw = ImageDraw.Draw(img)

    initial = username[0].upper()

    # Police
    try:
        font = ImageFont.truetype("arial.ttf", 150)
    except:
        font = ImageFont.load_default()

    # Centrage
    w, h = draw.textsize(initial, font=font)
    draw.text((128 - w / 2, 128 - h / 2), initial, fill="white", font=font)

    # Sauvegarde
    img.save(path, "PNG")

    return path
