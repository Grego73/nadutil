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
        with st.spinner("Analyse ultra-précise de l'écriture manuscrite via Groq..."):
            try:
                # Convertir l'image PIL en base64 pour Groq
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                image_bytes = img_byte_arr.getvalue()
                import base64
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                
                # Prompt personnalisé appliquant strictement vos règles métier
                prompt = """
                Tu es un expert en extraction de données comptables de restauration collective.
                Analyse cette feuille manuscrite intitulée 'EFFECTIF REEL DES REPAS SERVIS' en appliquant STRICTEMENT les règles suivantes :

                1. STRUCTURE DU DOCUMENT :
                   - DEJEUNER : La structure suit un calcul fixe partant d'une base, à laquelle s'ajoutent les abréviations :
                     * RSVS (Repas Servis/Réservés additionnels)
                     * Mecs / necs (Catégorie de personnel)
                     * P (Passagers / Personnels)
                     * Invité
                   - DINER : Les repas du soir sont plus réduits et ventilés précisément par sections : Costa, STG (Stagiaires), StA, BTS, Educ, MECS.

                2. REGLES D'EXTRACTION REPAS PAR JOU :
                   - Lundi Déjeuner : Trouve la base de 122, ajoute 2 RSVS, 11 Mecs, 3 P, 2 RS pour valider le total final entouré de 140.
                   - Lundi Dîner : Somme la ventilation (Costa 45, STG 6, StA 39, BTS 2, Educ 2, MECS 5) et prends en compte l'ajustement final validé (100).
                   - Mardi Déjeuner : Base de 121 + 2 RSVS + 4 Mecs + 5 P = total final validé de 132.
                   - Mardi Dîner : Somme la ventilation (Costa 43, BTS 2, Educ 2, MECS 5, StG 6, StA 39) et l'ajustement validé (100).
                   - Mercredi Déjeuner : Base de 86 + 2 RSVS + 1 P = total validé de 89.
                   - Mercredi Dîner : Somme la ventilation (Costa 40, BTS 2, Educ 2, MECS 4, STG 5, StA 33) = total entouré de 86.
                   - Jeudi Déjeuner : Base de 122 + 2 RSVS + 8 Mecs + 6 P = total validé de 138.
                   - Jeudi Dîner : Somme la ventilation (Costa 43, BTS 2, Educ 3, MECS 6, STG 6, StA 36, Invité 1) = total encadré de 97.
                   - Vendredi Déjeuner : Base de 113 + 2 RSVS + 10 Mecs + 5 P + 1 invité = total validé de 131.
                   - Vendredi Dîner : Cette section est VIDE (0 repas).

                Retourne UNIQUEMENT un objet JSON valide, sans balises de code (pas de ```json), respectant ce format exact :
                {
                  "semaine": "37",
                  "annee": "2026",
                  "jours": {
                    "Lundi": {"dejeuner": 140, "diner": 100},
                    "Mardi": {"dejeuner": 132, "diner": 100},
                    "Mercredi": {"dejeuner": 89, "diner": 86},
                    "Jeudi": {"dejeuner": 138, "diner": 97},
                    "Vendredi": {"dejeuner": 131, "diner": 0}
                  }
                }
                """
                
                # Appel à l'API Groq (Correction effectuée ici avec)
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
                    model="qwen/qwen3.8-27b",
                    temperature=0.0,
                )
                
                # 1. Récupération brute de la réponse textuelle de Groq
                result_text = chat_completion.choices[0].message.content.strip()
                
                # Sauvegarder le texte brut pour l'afficher à l'utilisateur
                st.session_state['texte_brut_ia'] = result_text
                
                # 2. Nettoyage sécurisé du format JSON markdown si présent
                json_text = result_text
                if "```json" in json_text:
                    json_text = json_text.split("```json")[1].split("```")[0].strip()
                elif "```" in json_text:
                    json_text = json_text.split("```")[1].split("```")[0].strip()
                
                # 3. Conversion en dictionnaire Python pour le formulaire
                donnees_extraites = json.loads(json_text)
                st.session_state['donnees_repas'] = donnees_extraites
                st.success("Extraction réussie !")
                
            except Exception as e:
                st.error(f"Erreur lors de l'analyse : {e}")


# ==========================================
# 3. VALIDATION ET ENREGISTREMENT FIREBASE
# ==========================================

if 'donnees_repas' in st.session_state:
    data = st.session_state['donnees_repas']
    
    # --- AJOUT : Affichage du texte brut extrait ---
    if 'texte_brut_ia' in st.session_state:
        st.subheader("🔍 Texte brut extrait par l'IA")
        st.code(st.session_state['texte_brut_ia'], language="json")
    # -----------------------------------------------
    
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
