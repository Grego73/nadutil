import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image, ImageOps
import pytesseract
import io

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

# 3. INTERFACE : CHIX DES ENTRÉES
st.write("### 📅 Saisie des totaux réels de la semaine")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**🍽️ REPAS DU MIDI (Déjeuner)**")
    lundi_midi = st.number_input("LUNDI - Midi :", min_value=0, value=140)
    mardi_midi = st.number_input("MARDI - Midi :", min_value=0, value=135)
    mercredi_midi = st.number_input("MERCREDI - Midi :", min_value=0, value=105)
    jeudi_midi = st.number_input("JEUDI - Midi :", min_value=0, value=140)
    vendredi_midi = st.number_input("VENDREDI - Midi :", min_value=0, value=131)

with col2:
    st.markdown("**🌙 REPAS DU SOIR (Dîner)**")
    lundi_soir = st.number_input("LUNDI - Soir :", min_value=0, value=99)
    mardi_soir = st.number_input("MARDI - Soir :", min_value=0, value=100)
    mercredi_soir = st.number_input("MERCREDI - Soir :", min_value=0, value=86)
    jeudi_soir = st.number_input("JEUDI - Soir :", min_value=0, value=197)
    vendredi_soir = st.number_input("VENDREDI - Soir :", min_value=0, value=0)

# 4. CONSTRUCTION DU TABLEAU EXCEL SOUS LE BON FORMAT
if st.button("📊 CALCULER ET GÉNÉRER LE FICHIER EXCEL"):
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
    st.success("Analyse terminée ! Voici le tableau généré :")
    st.dataframe(df, use_container_width=True)
    
    # Création du classeur Excel avec OpenPyXL
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Facturation Réel"
    
    # Correction définitive du bug de la grille (Ligne 145 résolue)
    ws.sheet_view.showGridLines = True
    
    # Entêtes de titres
    ws["A1"] = "REEL POUR FACTURATION"
    ws["A1"].font = Font(name="Arial", size=14, bold=True, color="1F4E78")
    
    # En-têtes du tableau
    headers = ["JOUR", "PETIT DEJEUNER", "MIDI", "GOUTER", "SOIR"]
    ws.append([]) # Ligne vide de séparation
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
        
    # Écriture des lignes de totaux
    for item in donnees_facturation:
        ws.append([item["JOUR"], item["PETIT DEJEUNER"], item["MIDI"], item["GOUTER"], item["SOIR"]])
        current_row = ws.max_row
        for c in range(1, 6):
            cell = ws.cell(row=current_row, column=c)
            cell.font = Font(name="Arial", size=10)
            cell.border = thin_border
            cell.alignment = Alignment(horizontal="center", vertical="center")
            
    # Ajustement automatique des largeurs
    for col in ws.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col.column)
        ws.column_dimensions[col_letter].width = max(max_len + 5, 15)
        
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    st.write("### 📥 3. Téléchargez votre document")
    st.download_button(
        label="📥 TÉLÉCHARGER LE FICHIER EXCEL (.xlsx)",
        data=buffer,
        file_name="Facturation_Reel_Semaine.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
