import streamlit as st
from google import genai
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image, ImageOps  # <--- IL FAUT RAJOUTER CETTE LIGNE ICI !
import io
import json


# ==========================================
# 1. CONFIGURATION DES APIS & CONFIG
# ==========================================

# Configuration Gemini
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
client = genai.Client(api_key=GOOGLE_API_KEY)

# Initialisation Firebase en copiant la configuration du calculateur
if not firebase_admin._apps:
    # Récupérer directement le dictionnaire généré par Streamlit sous [text_key]
    firebase_creds = dict(st.secrets["text_key"])
    
    # Correction automatique des sauts de ligne de la clé privée si nécessaire
    if "private_key" in firebase_creds:
        firebase_creds["private_key"] = firebase_creds["private_key"].replace("\\n", "\n")
        
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred)

db = firestore.client()


# ==========================================
# 2. INTERFACE UTILISATEUR (STREAMLIT)
# ==========================================

st.title("📊 Numérisation des Repas Servis")
st.write("Prenez en photo ou téléversez la feuille de la semaine.")

# Option pour charger l'image
uploaded_file = st.file_uploader("Choisir une image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    try:
        # 1. Ouvrir l'image avec PIL
        image = Image.open(uploaded_file)
        
        # 2. Corriger automatiquement l'orientation (Exif) si elle est sur le côté
        image = ImageOps.exif_transpose(image)
        
        # Afficher l'image remise à l'endroit sur l'interface
        st.image(image, caption="Feuille importée (remise à l'endroit)", use_column_width=True)
        
    except Exception as e:
        st.error(f"Impossible de traiter l'affichage de l'image : {e}")
    
    if st.button("🪄 Analyser et extraire les données"):
        with st.spinner("Analyse de l'écriture manuscrite en cours..."):
            try:
                # Convertir l'image PIL corrigée en octets pour l'envoyer à Gemini
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                image_bytes = img_byte_arr.getvalue()
                
                # Prompt de traitement pour l'IA
                prompt = """
                Analyse cette feuille manuscrite intitulée 'EFFECTIF REEL DES REPAS SERVIS'.
                Extrais les données pour chaque jour visible (LUNDI, MARDI, MERCREDI, JEUDI, VENDREDI).
                Pour chaque jour, trouve le total du 'DEJEUNER' (chiffre final validé/entouré) et le total du 'DINER'.
                Retourne UNIQUEMENT un objet JSON valide, sans balises de code (pas de ```json), respectant ce format exact :
                {
                  "semaine": "37",
                  "annee": "2026",
                  "jours": {
                    "Lundi": {"dejeuner": 140, "diner": 100},
                    "Mardi": {"dejeuner": 140, "diner": 97}
                  }
                }
                """
                
                # Appel à l'IA avec l'image redressée
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        prompt,
                        {"mime_type": "image/png", "data": image_bytes}
                    ]
                )
                
                # Convertir la réponse texte en dictionnaire Python
                donnees_extraites = json.loads(response.text.strip())
                st.session_state['donnees_repas'] = donnees_extraites
                st.success("Extraction réussie !")
                
            except Exception as e:
                st.error(f"Erreur lors de l'analyse : {e}")

# ==========================================
# 3. VALIDATION ET ENREGISTREMENT FIREBASE
# ==========================================

if 'donnees_repas' in st.session_state:
    data = st.session_state['donnees_repas']
    
    st.subheader(f"📝 Vérification des données (Semaine {data['semaine']})")
    
    # Formulaire dynamique pour modifier les chiffres si l'IA s'est trompée
    valeurs_finales = {}
    for jour, repas in data['jours'].items():
        st.markdown(f"**{jour}**")
        col1, col2 = st.columns(2)
        with col1:
            dej = col1.number_input(f"Déjeuner - {jour}", value=int(repas.get('dejeuner', 0)), key=f"dej_{jour}")
        with col2:
            din = col2.number_input(f"Dîner - {jour}", value=int(repas.get('diner', 0)), key=f"din_{jour}")
        valeurs_finales[jour.lower()] = {"dejeuner": dej, "diner": din}

    # Bouton de sauvegarde vers Firebase
    if st.button("💾 Enregistrer dans Firebase"):
        try:
            doc_id = f"semaine_{data['semaine']}_{data['annee']}"
            doc_ref = db.collection("repas_servis").document(doc_id)
            
            # Envoi des données nettoyées
            doc_ref.set({
                "numero_semaine": int(data['semaine']),
                "annee": int(data['annee']),
                "donnees": valeurs_finales
            })
            
            st.balloons()
            st.success(f"Données enregistrées avec succès dans Firestore ! (ID: {doc_id})")
            # Nettoyer la session après enregistrement
            del st.session_state['donnees_repas']
            
        except Exception as e:
            st.error(f"Erreur d'enregistrement Firebase : {e}")
