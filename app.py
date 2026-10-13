import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image
import pytesseract
import io

# 1. CONFIGURATION DE L'INTERFACE
st.set_page_config(page_title="Nadutil Autonome", page_icon="📊", layout="wide")
st.title("📊 Application Autonome Nadutil")
st.subheader("Analyse Automatique par Photo - Lycée Costa de Beauregard")

# 2. INITIALISATION SECURISEE DE FIREBASE
if not firebase_admin._apps:
    try:
        firebase_secrets = dict(st.secrets["firebase"])
        cred = credentials.Certificate(firebase_secrets)
        firebase_admin.initialize_app(cred)
        st.sidebar.success("🟢 Base de données Firebase connectée !")
    except Exception:
        st.sidebar.warning("橫 Mode local actif (Firebase non configuré).")

db = firestore.client() if firebase_admin._apps else None

# 3. ZONE AUTONOME : IMPORTATION DE LA PHOTO OU DU SCAN
st.write("### 📸 1. Importez la photo ou le scan de votre feuille de semaine")
fichier_image = st.file_uploader(
    "Glissez-déposez votre image ici (Format PNG, JPG, JPEG) :", 
    type=["png", "jpg", "jpeg"]
)

texte_analyse = ""

if fichier_image is not None:
    # 1. Ouverture de l'image
    image_brute = Image.open(fichier_image)
    
    # 2. REDRESSEMENT AUTOMATIQUE DE L'IMAGE SI ELLE EST DE CÔTÉ OU À L'ENVERS
    try:
        from PIL import ImageOps
        image = ImageOps.exif_transpose(image_brute)
    except Exception:
        image = image_brute
        
    # Affichage de l'image remise droite à l'écran
    st.image(image, caption="Feuille remise à l'endroit automatiquement", width=450)
    
    with st.spinner("🧠 Lecture de l'image par l'IA en cours... Veuillez patienter..."):
        try:
            # 3. Extraction du texte via Tesseract OCR
            texte_analyse = pytesseract.image_to_string(image, lang='fra')
            
            if texte_analyse.strip():
                st.success("📝 Lecture de l'image terminée ! Texte extrait avec succès.")
            else:
                st.error("🔴 L'image a été lue mais aucun texte n'a pu être extrait. Assurez-vous qu'elle est bien nette.")
        except Exception as e:
            st.error(f"🔴 Erreur lors de la lecture de l'image : {e}")

# 4. ALGORITHME D'ANALYSE ET GENERATION EXCEL
if texte_analyse:
    st.write("### ⚙️ 2. Traitement des effectifs de la restauration")
    
    # Petite zone de texte optionnelle pour permettre à l'utilisateur de corriger le texte lu si besoin
    texte_analyse = st.text_area("Texte extrait (Vous pouvez le corriger manuellement si l'IA a fait une faute) :", value=texte_analyse, height=200)
    
    if st.button("📊 CALCULER LES EFFECTIFS ET CRÉER LE FICHIER EXCEL"):
        lignes = texte_analyse.split("\n")
        donnees_completes = []
        entete_jours = [
            "LUNDI_Midi", "LUNDI_Soir", "MARDI_Midi", "MARDI_Soir", 
            "MERCREDI_Midi", "MERCREDI_Soir", "JEUDI_Midi", "JEUDI_Soir", 
            "VENDREDI_Midi", "VENDREDI_Soir"
        ]
        
        classe_actuelle = "Inconnue"
        
        for ligne in lignes:
            ligne_nettoyee = ligne.strip()
            if not ligne_nettoyee:
                continue
                
            # Détection automatique de la classe/section
            if any(c in ligne_nettoyee for c in ["4ème", "3ème", "CAPA", "2DE", "BAC PRO", "TERM", "BTS", "Ste ", "St "]):
                classe_actuelle = ligne_nettoyee.replace(",", "").strip()
                continue
                
            if "NOM" in ligne_nettoyee or "EFFECTIF" in ligne_nettoyee:
                continue
                
            # Nettoyage et découpage de la ligne d'élève détectée
            elements = [e.strip() for e in ligne_nettoyee.split(",")]
            
            if len(elements) >= 3 and any(r in elements for r in ["D", "P", "D/F", "APP"]):
                nom = elements[0]
                prenom = elements[1]
                regime = elements[2]
                
                repas_saisis = elements[3:13]
                while len(repas_saisis) < 10:
                    repas_saisis.append("")
                    
                repas_finals = []
                for i, case in enumerate(repas_saisis):
                    est_midi = (i % 2 == 0)
                    if case in ["PN", "EXC", "ABS", "REPAS"]:
                        repas_finals.append(case)
                    elif regime == "P":
                        repas_finals.append("X")
                    elif regime == "D" and est_midi:
                        repas_finals.append("X")
                    else:
                        repas_finals.append("")
                
                ligne_eleve = {
                    "Classe/Section": classe_actuelle, 
                    "Nom": nom, 
                    "Prénom": prenom, 
                    "Régime": regime
                }
                for j, jour_repas in enumerate(entete_jours):
                    ligne_eleve[jour_repas] = repas_finals[j]
                    
                donnees_completes.append(ligne_eleve)
                
                # Sauvegarde dans Firestore (Firebase) si actif
                if db:
                    try:
                        db.collection("nadutil_eleves").document(f"{classe_actuelle}_{nom}_{prenom}").set(ligne_eleve)
                    except Exception:
                        pass

        if donnees_completes:
            df = pd.DataFrame(donnees_completes)
            st.dataframe(df, use_container_width=True)
            
            # Création du fichier Excel téléchargeable
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Facturation Cantine')
            buffer.seek(0)
            
            st.download_button(
                label="📥 TÉLÉCHARGER LE FICHIER EXCEL COMPLET (.xlsx)",
                data=buffer,
                file_name="Suivi_Semaine_Cantine.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("⚠️ Le texte extrait de l'image ne contient pas de lignes au format attendu (NOM, PRENOM, REGIME). Vous pouvez ajuster le texte ci-dessus pour correspondre à ce format (séparé par des virgules).")
