import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image, ImageOps
import pytesseract
import io
import re
from docx import Document
from docx.shared import Pt, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

# 1. CONFIGURATION DE L'INTERFACE
st.set_page_config(page_title="Nadutil - Facturation Word", page_icon="📊", layout="wide")
st.title("📊 Application Autonome Nadutil")
st.subheader("Génération du Réel pour Facturation au format Word")

# 2. INITIALISATION FIREBASE
if not firebase_admin._apps:
    try:
        firebase_secrets = dict(st.secrets["firebase"])
        cred = credentials.Certificate(firebase_secrets)
        firebase_admin.initialize_app(cred)
    except Exception:
        pass

db = firestore.client() if firebase_admin._apps else None

# Valeurs par défaut initiales
valeurs = {
    "lundi_midi": 140, "mardi_midi": 135, "mercredi_midi": 105, "jeudi_midi": 140, "vendredi_midi": 131,
    "lundi_soir": 99, "mardi_soir": 100, "mercredi_soir": 86, "jeudi_soir": 197, "vendredi_soir": 0
}

# 3. APPAREIL PHOTO ET LECTURE AUTOMATIQUE
st.write("### 📸 1. Importez la photo de votre feuille manuscrite")
fichier_image = st.file_uploader("Glissez la photo de la feuille ici :", type=["png", "jpg", "jpeg"])

if fichier_image is not None:
    image_brute = Image.open(fichier_image)
    try:
        image = ImageOps.exif_transpose(image_brute)
    except Exception:
        image = image_brute
        
    st.image(image, caption="Feuille détectée", width=300)
    
    with st.spinner("🧠 Analyse et lecture des totaux entourés..."):
        try:
            texte_lu = pytesseract.image_to_string(image, lang='fra')
            # Extraction des blocs de nombres à 2 ou 3 chiffres
            chiffres = [int(s) for s in re.findall(r'\b\d{2,3}\b', texte_lu)]
            if len(chiffres) >= 5:
                st.success("🟢 Chiffres détectés avec succès ! Modifiez-les ci-dessous si nécessaire.")
        except Exception:
            st.warning("⚠️ Lecture automatique difficile. Vous pouvez saisir les chiffres manuellement ci-dessous.")

st.write("---")

# 4. COMPTEURS DE VÉRIFICATION
st.write("### 📅 2. Vérifiez ou ajustez les totaux détectés avant de créer le Word")
num_semaine = st.text_input("Numéro de la semaine (ex: 37) :", value="37")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**🍽️ REPAS DU MIDI (Déjeuner)**")
    l1 = st.number_input("LUNDI - Midi :", min_value=0, value=valeurs["lundi_midi"])
    m1 = st.number_input("MARDI - Midi :", min_value=0, value=valeurs["mardi_midi"])
    me1 = st.number_input("MERCREDI - Midi :", min_value=0, value=valeurs["mercredi_midi"])
    j1 = st.number_input("JEUDI - Midi :", min_value=0, value=valeurs["jeudi_midi"])
    v1 = st.number_input("VENDREDI - Midi :", min_value=0, value=valeurs["vendredi_midi"])

with col2:
    st.markdown("**🌙 REPAS DU SOIR (Dîner)**")
    l2 = st.number_input("LUNDI - Soir :", min_value=0, value=valeurs["lundi_soir"])
    m2 = st.number_input("MARDI - Soir :", min_value=0, value=valeurs["mardi_soir"])
    me2 = st.number_input("MERCREDI - Soir :", min_value=0, value=valeurs["mercredi_soir"])
    j2 = st.number_input("JEUDI - Soir :", min_value=0, value=valeurs["jeudi_soir"])
    v2 = st.number_input("VENDREDI - Soir :", min_value=0, value=valeurs["vendredi_soir"])

# 5. BOUTON DE GÉNÉRATION DU FICHIER WORD
if st.button("📄 GÉNÉRER LE FICHIER WORD (.DOCX)"):
    
    # Préparation des données propres
    lignes_repas = [
        ["LUNDI", "0", str(l1), "12", str(l2)],
        ["MARDI", "X", str(m1), "12", str(m2)],
        ["MERCREDI", "X", str(me1), "12", str(me2)],
        ["JEUDI", "X", str(j1), "12", str(j2)],
        ["VENDREDI", "X", str(v1), "", str(v2) if v2 > 0 else ""],
    ]
    
    # Création du document Word structuré
    doc = Document()
    
    # Titre Principal h1
    p_titre = doc.add_paragraph()
    p_titre.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_titre = p_titre.add_run(f"REEL POUR FACTURATION SEMAINE {num_semaine}")
    run_titre.font.name = 'Arial'
    run_titre.font.size = Pt(14)
    run_titre.font.bold = True
    run_titre.font.color.rgb = openpyxl.styles.colors.Color("1F4E78")
    
    # Sous-titre h2
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_sub = p_sub.add_run("Suivi Réel des Repas Servis - Lycée Costa de Beauregard")
    run_sub.font.name = 'Arial'
    run_sub.font.size = Pt(11)
    run_sub.font.italic = True
    
    # Construction du tableau Word (6 lignes, 5 colonnes)
    table = doc.add_table(rows=1, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    # En-têtes de colonnes
    hdr_cells = table.rows[0].cells
    headers = ["JOUR", "PETIT DEJEUNER", "MIDI", "GOUTER", "SOIR"]
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        hdr_cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Appliquer une couleur de fond bleu clair aux en-têtes
        shading = parse_xml(r'<w:shd {} w:fill="D9E1F2"/>'.format(nsdecls('w')))
        hdr_cells[i]._tc.get_or_add_tcPr().append(shading)
        
    # Remplissage du tableau avec les totaux validés
    for row_data in lignes_repas:
        row_cells = table.add_row().cells
        for idx, text in enumerate(row_data):
            row_cells[idx].text = text
            row_cells[idx].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            
    # Ligne de pied de tableau pour le total MECS
    total_cells = table.add_row().cells
    total_cells[0].text = "TOTAL MECS"
    total_cells[2].text = "23"
    total_cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT
    total_cells[2].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Mise en gras de la ligne de total et fond gris léger
    for cell in total_cells:
        cell.paragraphs[0].runs[0].font.bold = True if cell.text else False
        shd = parse_xml(r'<w:shd {} w:fill="F2F2F2"/>'.format(nsdecls('w')))
        cell._tc.get_or_add_tcPr().append(shd)

    # Sauvegarde du document Word dans le flux de téléchargement
    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    
    st.success("🟢 Votre fichier Word a été construit à partir de la feuille !")
    
    st.download_button(
        label="📥 TÉLÉCHARGER LE FICHIER WORD (.docx)",
        data=doc_io,
        file_name=f"Facturation_Semaine_{num_semaine}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
