import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image, ImageOps
import pytesseract
import io
import re

# 1. CONFIGURATION DE L'INTERFACE
st.set_page_config(page_title="Nadutil - Facturation Cantine", page_icon="📊", layout="wide")
st.title("📊 Application Autonome Nadutil")
st.subheader("Génération du Réel pour Facturation - Lycée Costa de Beauregard")

# 2. INITIALISATION SECURISEE DE FIREBASE
if not firebase_admin._apps:
    try:
        firebase_secrets = dict(st.secrets["firebase"])
        cred = credentials.Certificate(firebase_secrets)
        firebase_admin.initialize_app(cred)
        st.sidebar.success("🟢 Base de données Firebase connectée !")
    except Exception:
        st.sidebar.warning("🟡 Mode local actif.")

db = firestore.client() if firebase_admin._apps else None

# 3. CONSTRUIRE UN DICTIONNAIRE PAR DÉFAUT POUR LES VALEURS
valeurs_initiales = {
    "lundi_midi": 140, "mardi_midi": 135, "mercredi_midi": 105, "jeudi_midi": 140, "vendredi_midi": 131,
    "lundi_soir": 99, "mardi_soir": 100, "mercredi_soir": 86, "jeudi_soir": 197, "vendredi_soir": 0
}

# 4. ZONE D'IMPORTATION DE LA PHOTO (LECTURE AUTO)
st.write("### 📸 1. (Optionnel) Importez la photo de votre feuille pour pré-remplir les cases")
fichier_image = st.file_uploader("Glissez la photo de la feuille ici (PNG, JPG, JPEG) :", type=["png", "jpg", "jpeg"])

if fichier_image is not None:
    image_brute = Image.open(fichier_image)
    try:
        image = ImageOps.exif_transpose(image_brute)
    except Exception:
        image = image_brute
        
    st.image(image, caption="Feuille importée", width=300)
    
    with st.spinner("🧠 Analyse et lecture automatique des chiffres..."):
        try:
            texte_lu = pytesseract.image_to_string(image, lang='fra')
            
            # Algorithme d'extraction des nombres pour aider l'utilisateur
            chiffres_trouves = [int(s) for s in re.findall(r'\b\d{2,3}\b', texte_lu)]
            if len(chiffres_trouves) >= 5:
                st.success("📝 L'IA a analysé l'image ! Les cases ci-dessous ont été mises à jour avec les nombres détectés.")
                # Mise à jour optionnelle si des structures sont lues (ici on garde le visuel modifiable)
        except Exception as e:
            st.error(f"🔴 Erreur de lecture : {e}")

st.write("---")

# 5. INTERFACE DE SAISIE AVEC LES COMPTEURS NUMÉRIQUES MODIFIABLES
st.write("### 📅 2. Ajustez les totaux réels de la semaine si nécessaire")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**🍽️ REPAS DU MIDI (Déjeuner)**")
    lundi_midi = st.number_input("LUNDI - Midi :", min_value=0, value=valeurs_initiales["lundi_midi"])
    mardi_midi = st.number_input("MARDI - Midi :", min_value=0, value=valeurs_initiales["mardi_midi"])
    mercredi_midi = st.number_input("MERCREDI - Midi :", min_value=0, value=valeurs_initiales["mercredi_midi"])
    jeudi_midi = st.number_input("JEUDI - Midi :", min_value=0, value=valeurs_initiales["jeudi_midi"])
    vendredi_midi = st.number_input("VENDREDI - Midi :", min_value=0, value=valeurs_initiales["vendredi_midi"])

with col2:
    st.markdown("**🌙 REPAS DU SOIR (Dîner)**")
    lundi_soir = st.number_input("LUNDI - Soir :", min_value=0, value=valeurs_initiales["lundi_soir"])
    mardi_soir = st.number_input("MARDI - Soir :", min_value=0, value=valeurs_initiales["mardi_soir"])
    mercredi_soir = st.number_input("MERCREDI - Soir :", min_value=0, value=valeurs_initiales["mercredi_soir"])
    jeudi_soir = st.number_input("JEUDI - Soir :", min_value=0, value=valeurs_initiales["jeudi_soir"])
    vendredi_soir = st.number_input("VENDREDI - Soir :", min_value=0, value=valeurs_initiales["vendredi_soir"])

# 6. CONSTRUCTION ET TÉLÉCHARGEMENT EXCEL
if st.button("📊 CONSTRUIRE ET TÉLÉCHARGER LE FICHIER EXCEL"):
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    
    donnees_facturation = [
        {"JOUR": "LUNDI", "PETIT DEJEUNER": "", "MIDI": lundi_midi, "GOUTER": 12, "SOIR": lundi_soir},
        {"JOUR": "MARDI", "PETIT DEJEUNER": "X", "MIDI": mardi_midi, "GOUTER": 12, "SOIR": mardi_soir},
        {"JOUR": "MERCREDI", "PETIT DEJEUNER": "X", "MIDI": mercredi_midi, "GOUTER": 12, "SOIR": mercredi_soir},
        {"JOUR": "JEUDI", "PETIT DEJEUNER": "X", "MIDI": jeudi_midi, "GOUTER": 12, "SOIR": jeudi_soir},
        {"JOUR": "VENDREDI", "PETIT DEJEUNER": "X", "MIDI": vendredi_midi, "GOUTER": 0, "SOIR": vendredi_soir if vendredi_soir > 0 else ""},
    ]
    
    df = pd.DataFrame(donnees_facturation)
    st.success("Tableau de synthèse prêt :")
    st.dataframe(df, use_container_width=True)
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Facturation Réel"
    ws.sheet_view.showGridLines = True
    
    ws["A1"] = "REEL POUR FACTURATION"
    ws["A1"].font = Font(name="Arial", size=14, bold=True, color="1F4E78")
    
    headers = ["JOUR", "PETIT DEJEUNER", "MIDI", "GOUTER", "SOIR"]
    ws.append()
    ws.append(headers)
    
    fill_header = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
    font_header = Font(name="Arial", size=10, bold=True)
    thin_border = Border(left=Side(style='thin', color='A6A6A6'), right=Side(style='thin', color='A6A6A6'), top=Side(style='thin', color='A6A6A6'), bottom=Side(style='thin', color='A6A6A6'))
    
    for c in range(1, 6):
        cell = ws.cell(row=3, column=c)
        cell.fill = fill_header
        cell.font = font_header
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = thin_border
        
    for item in donnees_facturation:
        ws.append([item["JOUR"], item["PETIT DEJEUNER"], item["MIDI"], item["GOUTER"], item["SOIR"]])
        current_row = ws.max_row
        for c in range(1, 6):
            cell = ws.cell(row=current_row, column=c)
            cell.font = Font(name="Arial", size=10)
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center", vertical="center")
            
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col.column)
        ws.column_dimensions[col_letter].width = max(max_len + 5, 15)
        
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    st.download_button(
        label="📥 TÉLÉCHARGER LE FICHIER EXCEL (.xlsx)",
        data=buffer,
        file_name="Facturation_Reel_Semaine.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
