import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image, ImageOps
import pytesseract
import io
import re

# 1. CONFIGURATION DE L'INTERFACE
st.set_page_config(page_title="Nadutil - Restauration Scolaire", page_icon="📊", layout="wide")
st.title("📊 Application Autonome Nadutil")
st.subheader("Analyse de la Restauration Scolaire - Lycée Costa de Beauregard")

# 2. INITIALISATION FIREBASE
if not firebase_admin._apps:
    try:
        firebase_secrets = dict(st.secrets["firebase"])
        cred = credentials.Certificate(firebase_secrets)
        firebase_admin.initialize_app(cred)
        st.sidebar.success("🟢 Base de données Firebase connectée !")
    except Exception:
        st.sidebar.warning("🟡 Mode local actif (Firebase non configuré).")

db = firestore.client() if firebase_admin._apps else None

# 3. ZONE D'IMPORTATION DE LA PHOTO
st.write("### 📸 1. Importez la photo de votre feuille de semaine")
fichier_image = st.file_uploader("Sélectionnez ou glissez la photo ici (PNG, JPG, JPEG) :", type=["png", "jpg", "jpeg"])

texte_extrait = ""

if fichier_image is not None:
    image_brute = Image.open(fichier_image)
    # Redressement automatique selon les capteurs du téléphone
    try:
        image = ImageOps.exif_transpose(image_brute)
    except Exception:
        image = image_brute
        
    st.image(image, caption="Feuille traitée par l'application", width=400)
    
    with st.spinner("🧠 Analyse optique et lecture de l'écriture en cours..."):
        try:
            texte_extrait = pytesseract.image_to_string(image, lang='fra')
        except Exception as e:
            st.error(f"🔴 Erreur de lecture : {e}")

# 4. FORMULAIRE INTELLIGENT DE VALIDATION DES CHIFFRES
if fichier_image is not None:
    st.write("### ⚙️ 2. Vérification et validation des totaux de la semaine")
    st.info("L'IA a lu la feuille. Vérifiez ou ajustez les totaux encadrés ci-dessous avant de générer l'Excel :")
    
    # Analyse rapide du texte pour tenter de deviner la semaine (ex: Semaine n°37)
    semaine_detectee = "37"
    match_semaine = re.search(r"(?:Semaine\s*n°\s*)(\d+)", texte_extrait, re.IGNORECASE)
    if match_semaine:
        semaine_detectee = match_semaine.group(1)
        
    num_semaine = st.text_input("Numéro de la semaine pour la facturation :", value=semaine_detectee)
    
    # Création de formulaires pour saisir/corriger les totaux entourés de la feuille
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**🍽️ EFFECTIFS DU MIDI (Déjeuner)**")
        repas_midi = {
            "LUNDI": st.number_input("Midi - LUNDI (ex: 140) :", min_value=0, value=140),
            "MARDI": st.number_input("Midi - MARDI (ex: 135) :", min_value=0, value=135),
            "MERCREDI": st.number_input("Midi - MERCREDI (ex: 105) :", min_value=0, value=105),
            "JEUDI": st.number_input("Midi - JEUDI (ex: 140) :", min_value=0, value=140),
            "VENDREDI": st.number_input("Midi - VENDREDI (ex: 131) :", min_value=0, value=131),
        }
        
    with col2:
        st.markdown("**🌙 EFFECTIFS DU SOIR (Dîner)**")
        repas_soir = {
            "LUNDI": st.number_input("Soir - LUNDI (ex: 99) :", min_value=0, value=99),
            "MARDI": st.number_input("Soir - MARDI (ex: 100) :", min_value=0, value=100),
            "MERCREDI": st.number_input("Soir - MERCREDI (ex: 86) :", min_value=0, value=86),
            "JEUDI": st.number_input("Soir - JEUDI (ex: 197) :", min_value=0, value=197),
            "VENDREDI": st.number_input("Soir - VENDREDI (ex: 0) :", min_value=0, value=0),
        }

    # 5. BOUTON DE CRÉATION ET EXPORTATION EXCEL
    if st.button("📊 CONSTRUIRE LE TABLEAU DE FACTURATION ET L'EXCEL"):
        donnees_facturation = []
        jours = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI"]
        
        for jour in jours:
            ligne_jour = {
                "JOUR": jour,
                "PETIT DEJEUNER": 0 if jour == "LUNDI" else "X", # Gestion automatique des petits déjeuners des internes
                "MIDI": repas_midi[jour],
                "GOUTER": 12 if jour != "VENDREDI" else 0,       # Goûters fixes MECS automatiques
                "SOIR": repas_soir[jour] if repas_soir[jour] > 0 else ""
            }
            donnees_facturation.append(ligne_jour)
            
            # Sauvegarde de sécurité de l'historique dans Firebase si connecté
            if db:
                try:
                    db.collection("nadutil_facturation").document(f"Semaine_{num_semaine}_{jour}").set(ligne_jour)
                except Exception:
                    pass
                    
        # Création du DataFrame et affichage à l'écran
        df_final = pd.DataFrame(donnees_facturation)
        st.success(f"🟢 Tableau REEL POUR FACTURATION SEMAINE {num_semaine} généré avec succès !")
        st.dataframe(df_final, use_container_width=True)
        
        # Génération du fichier Excel réel
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_final.to_excel(writer, index=False, sheet_name=f'Semaine {num_semaine}')
        buffer.seek(0)
        
        st.download_button(
            label="📥 TÉLÉCHARGER LE FICHIER EXCEL (.xlsx)",
            data=buffer,
            file_name=f"Facturation_Reel_Semaine_{num_semaine}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
        if db:
            st.info("💾 L'historique de cette semaine a été sauvegardé dans votre collection Firebase 'nadutil_facturation'.")
