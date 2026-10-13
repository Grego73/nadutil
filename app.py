import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image, ImageOps
import io
import json
from groq import Groq  # Importation du client Groq

# ==========================================
# 1. CONFIGURATION DES APIS & CONFIG
# ==========================================

# Initialisation du client Groq (Fini les coupures Google !)
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
client_groq = Groq(api_key=GROQ_API_KEY)

# Initialisation Firebase en copiant la configuration de votre calculateur
if not firebase_admin._apps:
    firebase_creds = dict(st.secrets["text_key"])
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

uploaded_file = st.file_uploader("Choisir une image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    try:
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image)
        st.image(image, caption="Feuille importée (remise à l'endroit)", use_column_width=True)
    except Exception as e:
        st.error(f"Impossible de traiter l'affichage de l'image : {e}")
    
    if st.button("🪄 Analyser et extraire les données"):
        with st.spinner("Analyse ultra-rapide de l'écriture manuscrite via Groq..."):
            try:
                # Convertir l'image PIL en base64 pour Groq
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                image_bytes = img_byte_arr.getvalue()
                import base64
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                
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
                
                # Appel au modèle Vision de Groq (Llama 3.2 11B Vision)
                chat_completion = client_groq.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}",
                                    },
                                },
                            ],
                        }
                    ],
                    model="qwen/qwen3.8-27b",  # <--- METTEZ À JOUR CETTE LIGNE
                    temperature=0.0,
                )
                
                # Récupération du résultat texte
                result_text = chat_completion.choices[0].message.content.strip()
                
                # Nettoyage si le modèle a quand même mis des balises markdown
                if result_text.startswith("```json"):
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                elif result_text.startswith("```"):
                    result_text = result_text.split("```")[1].split("```")[0].strip()
                
                donnees_extraites = json.loads(result_text)
                st.session_state['donnees_repas'] = donnees_extraites
                st.success("Extraction réussie avec Groq !")
                
            except Exception as e:
                st.error(f"Erreur lors de l'analyse : {e}")

# ==========================================
# 3. VALIDATION ET ENREGISTREMENT FIREBASE
# ==========================================

if 'donnees_repas' in st.session_state:
    data = st.session_state['donnees_repas']
    st.subheader(f"📝 Vérification des données (Semaine {data.get('semaine', '??')})")
    
    jours_data = data.get('jours', {})
    valeurs_finales = {}
    
    for jour in ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]:
        repas = jours_data.get(jour, jours_data.get(jour.lower(), {}))
        st.markdown(f"**{jour}**")
        col1, col2 = st.columns(2)
        with col1:
            dej = col1.number_input(f"Déjeuner - {jour}", value=int(repas.get('dejeuner', 0)), key=f"dej_{jour}")
        with col2:
            din = col2.number_input(f"Dîner - {jour}", value=int(repas.get('diner', 0)), key=f"din_{jour}")
        valeurs_finales[jour.lower()] = {"dejeuner": dej, "diner": din}

    if st.button("💾 Enregistrer dans Firebase"):
        try:
            doc_id = f"semaine_{data.get('semaine', '37')}_{data.get('annee', '2026')}"
            doc_ref = db.collection("repas_servis").document(doc_id)
            
            doc_ref.set({
                "numero_semaine": int(data.get('semaine', 37)),
                "annee": int(data.get('annee', 2026)),
                "donnees": valeurs_finales
            })
            st.balloons()
            st.success(f"Données enregistrées avec succès dans Firestore ! (ID: {doc_id})")
            del st.session_state['donnees_repas']
            st.rerun()
        except Exception as e:
            st.error(f"Erreur d'enregistrement Firebase : {e}")
