import os
import base64
from openai import OpenAI

# Initialiser le client (nécessite une clé API)
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Fonction pour encoder l'image en Base64
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

image_path = "votre_feuille_repas.png"
base64_image = encode_image(image_path)

# Appel au modèle de vision
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Traduis cette feuille de repas manuscrite en texte structuré."},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_image}"}}
            ],
        }
    ],
)

# Afficher le résultat textuel
print(response.choices[0].message.content)
