import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image, ImageOps
import io
import json
from groq import Groq

# ==========================================
# 1. CONFIGURATION DES APIS & CONFIG
# ==========================================

# Initialisation Groq
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
client_groq = Groq(api_key=GROQ_API_KEY)

# Initialisation Firebase
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

st.title("📊 Numérisation & Vérification des Repas")
st.write("Prenez en photo ou téléversez la feuille de la semaine.")

uploaded_file = st.file_uploader("Choisir une image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    try:
        image = Image.open(uploaded_file)
        image = ImageOps.exif_transpose(image)
        st.image(image, caption="Feuille importée (remise à l'endroit)", use_column_width=True)
    except Exception as e:
        st.error(f"Impossible de traiter l'affichage de l'image : {e}")
    
    if st.button("🪄 Analyser, extraire et vérifier les calculs"):
        with st.spinner("Analyse approfondie de la feuille en cours..."):
            try:
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                image_bytes = img_byte_arr.getvalue()
                import base64
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                
                # Prompt chirurgical demandant le détail de TOUTES les variables manuscrites
                prompt = """
                Analyse cette feuille de restauration intitulée 'EFFECTIF REEL DES REPAS SERVIS'.
                Tu dois décomposer chaque ligne manuscrite en extrayant individuellement chaque nombre associé à son abréviation ou sa section.
                Si un élément n'est pas présent pour un jour, attribue-lui la valeur 0.
                Prends également le total écrit par l'auteur sur la feuille (le chiffre final écrit ou entouré).

                Format de réponse exigé : Retourne UNIQUEMENT un objet JSON valide, sans aucune balise markdown (pas de ```json), respectant cette structure exacte :
                {
                  "semaine": "37",
                  "annee": "2026",
                  "jours": {
                    "Lundi": {
                      "dejeuner": {"base": 122, "rsvs": 2, "mecs": 11, "p": 3, "rs": 2, "invite": 0, "total_feuille": 140},
                      "diner": {"costa": 45, "stg": 6, "sta": 39, "bts": 2, "educ": 2, "mecs": 5, "ajustement": 2, "total_feuille": 101}
                    },
                    "Mardi": {
                      "dejeuner": {"base": 121, "rsvs": 2, "mecs": 4, "p": 5, "rs": 0, "invite": 0, "total_feuille": 132},
                      "diner": {"costa": 43, "stg": 6, "sta": 35, "bts": 2, "educ": 2, "mecs": 5, "ajustement": 0, "total_feuille": 93}
                    },
                    "Mercredi": {
                      "dejeuner": {"base": 86, "rsvs": 2, "mecs": 0, "p": 1, "rs": 0, "invite": 0, "total_feuille": 89},
                      "diner": {"costa": 40, "stg": 5, "sta": 33, "bts": 2, "educ": 2, "mecs": 4, "ajustement": 2, "total_feuille": 86}
                    },
                    "Jeudi": {
                      "dejeuner": {"base": 122, "rsvs": 2, "mecs": 8, "p": 6, "rs": 0, "invite": 0, "total_feuille": 138},
                      "diner": {"costa": 43, "stg": 6, "sta": 36, "bts": 2, "educ": 3, "mecs": 6, "ajustement": 0, "total_feuille": 97}
                    },
                    "Vendredi": {
                      "dejeuner": {"base": 113, "rsvs": 2, "mecs": 10, "p": 5, "rs": 0, "invite": 1, "total_feuille": 131},
                      "diner": {"costa": 0, "stg": 0, "sta": 0, "bts": 0, "educ": 0, "mecs": 0, "ajustement": 0, "total_feuille": 0}
                    }
                  }
                }
                """
                
                chat_completion = client_groq.chat.completions.create(
                    messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
                    model="qwen/qwen3.8-27b",
                    temperature=0.0
                )
                
                json_text = chat_completion.choices[0].message.content.strip()
                if "```json" in json_text:
                    json_text = json_text.split("```json")[1].split("```")[0].strip()
                elif "```" in json_text:
                    json_text = json_text.split("```")[1].split("```")[0].strip()
                
                st.session_state['donnees_repas_complexes'] = json.loads(json_text)
                st.success("Extraction brute des données effectuée !")
            except Exception as e:
                st.error(f"Erreur d'analyse : {e}")

# ==========================================
# 3. VERIFICATEUR DE CALCULS & FORMULAIRE
# ==========================================

if 'donnees_repas_complexes' in st.session_state:
    data = st.session_state['donnees_repas_complexes']
    st.subheader(f"📝 Rapport de Vérification Automatique (Semaine {data.get('semaine', '??')})")
    
    valeurs_finales_sauvegarde = {}
    
    for jour, repas_du_jour in data.get('jours', {}).items():
        st.markdown(f"### 🗓️ {jour}")
        
        # --- TRAITEMENT DU DEJEUNER ---
        dej = repas_du_jour.get('dejeuner', {})
        # Calcul automatique Python
        dej_reel = int(dej.get('base', 0)) + int(dej.get('rsvs', 0)) + int(dej.get('mecs', 0)) + int(dej.get('p', 0)) + int(dej.get('rs', 0)) + int(dej.get('invite', 0))
        dej_feuille = int(dej.get('total_feuille', 0))
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Déjeuner (Détail extrait)**")
            st.write(f"Base: {dej.get('base',0)} | RSVS: {dej.get('rsvs',0)} | Mecs: {dej.get('mecs',0)} | P: {dej.get('p',0)} | RS: {dej.get('rs',0)} | Invité: {dej.get('invite',0)}")
        with col2:
            if dej_reel == dej_feuille:
                st.success(f"🟢 Déjeuner Conforme : {dej_reel}")
            else:
                st.error(f"🔴 Erreur Déjeuner ! Calcul Réel = {dej_reel} vs Feuille = {dej_feuille}")
        
        # --- TRAITEMENT DU DINER ---
        din = repas_du_jour.get('diner', {})
        # Calcul automatique Python
        din_reel = int(din.get('costa', 0)) + int(din.get('stg', 0)) + int(din.get('sta', 0)) + int(din.get('bts', 0)) + int(din.get('educ', 0)) + int(din.get('mecs', 0)) + int(din.get('ajustement', 0))
        din_feuille = int(din.get('total_feuille', 0))
        
        col3, col4 = st.columns(2)
        with col3:
            st.markdown("**Dîner (Détail extrait)**")
            if jour == "Vendredi" and din_feuille == 0:
                st.write("*Fermé le vendredi soir*")
            else:
                st.write(f"Costa: {din.get('costa',0)} | STG: {din.get('stg',0)} | StA: {din.get('sta',0)} | BTS: {din.get('bts',0)} | Educ: {din.get('educ',0)} | MECS: {din.get('mecs',0)}")
        with col4:
            if jour == "Vendredi" and din_feuille == 0:
                st.info("🟢 Repas: 0")
            elif din_reel == din_feuille:
                st.success(f"🟢 Dîner Conforme : {din_reel}")
            else:
                st.error(f"🔴 Erreur Dîner ! Calcul Réel = {din_reel} vs Feuille = {din_feuille}")
                
        st.markdown("---")
        
        # Préparation du dictionnaire pour Firebase (on enregistre le calcul mathématique exact et corrigé)
        valeurs_finales_sauvegarde[jour.lower()] = {
            "dejeuner": dej_reel,
            "diner": din_reel
        }

    # Bouton d'envoi final vers votre base Firestore existante
    if st.button("💾 Valider et Envoyer les totaux certifiés à Firebase"):
        try:
            doc_id = f"semaine_{data.get('semaine', '37')}_{data.get('annee', '2026')}"
            doc_ref = db.collection("repas_servis").document(doc_id)
            
            doc_ref.set({
                "numero_semaine": int(data.get('semaine', 37)),
                "annee": int(data.get('annee', 2026)),
                "donnees": valeurs_finales_sauvegarde,
                "statut_verification": "verifie_et_certifie"
            })
            st.balloons()
            st.success(f"Données certifiées enregistrées dans Firestore ! (ID: {doc_id})")
            del st.session_state['donnees_repas_complexes']
            st.rerun()
        except Exception as e:
            st.error(f"Erreur d'enregistrement Firebase : {e}")
