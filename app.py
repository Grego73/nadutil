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
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls

# 1. CONFIGURATION DE L'INTERFACE
st.set_page_config(page_title="Nadutil - Facturation Détaillée", page_icon="📝", layout="wide")
st.title("📊 Application Autonome Nadutil")
st.subheader("Génération Avancée du Réel pour Facturation au format Word (Avec Détails)")

# 2. INITIALISATION SECURISEE DE FIREBASE
if not firebase_admin._apps:
    try:
        firebase_secrets = dict(st.secrets["firebase"])
        cred = credentials.Certificate(firebase_secrets)
        firebase_admin.initialize_app(cred)
    except Exception:
        pass

db = firestore.client() if firebase_admin._apps else None

# 3. APPAREIL PHOTO ET LECTURE AUTOMATIQUE
st.write("### 📸 1. Importez la photo de votre feuille manuscrite pour analyse")
fichier_image = st.file_uploader("Glissez la photo de la feuille ici (PNG, JPG, JPEG) :", type=["png", "jpg", "jpeg"])

texte_lu = ""
if fichier_image is not None:
    image_brute = Image.open(fichier_image)
    try:
        image = ImageOps.exif_transpose(image_brute)
    except Exception:
        image = image_brute
        
    st.image(image, caption="Feuille détectée par l'application", width=300)
    
    with st.spinner("🧠 Analyse optique et extraction des données en cours..."):
        try:
            texte_lu = pytesseract.image_to_string(image, lang='fra')
            st.success("🟢 L'IA a fini d'analyser l'image. Utilisez les formulaires ci-dessous pour valider les blocs.")
        except Exception as e:
            st.error(f"🔴 Erreur de lecture de l'image : {e}")

st.write("---")

# 4. FORMULAIRES DE CONFIGURATION ULTRA-DÉTAILLÉS JOUR PAR JOUR
st.write("### 📅 2. Complétez ou ajustez les totaux et les détails des calculs")

num_semaine = st.text_input("Numéro de la semaine pour l'en-tête (ex: 26 ou 37) :", value="26")
dates_semaine = st.text_input("Dates de la semaine (ex: Du 22 au 26 juin 2026) :", value="Du 22 au 26 juin 2026")

# Initialisation des structures de données pour stocker les détails saisis
jours = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI"]
data_midi_totaux = {}
data_midi_details = {}
data_soir_totaux = {}
data_soir_details = {}
data_pdej_totaux = {}
data_pdej_details = {}

# Création d'onglets pour chaque jour pour une navigation claire et lisible
onglets = st.tabs(jours)

for i, jour in enumerate(jours):
    with onglets[i]:
        st.markdown(f"### 🗓️ Configuration du {jour}")
        
        c1, c2, c3 = st.columns(3)
        
        with c1:
            st.markdown("**☕ PETIT DÉJEUNER**")
            val_pdej = 0 if jour == "LUNDI" else (15 if jour == "MARDI" else (12 if jour == "MERCREDI" else (22 if jour == "JEUDI" else 13)))
            det_pdej = "" if jour == "LUNDI" else (f"13 + 2 RSVS" if jour in ["MARDI", "VENDREDI"] else (f"10 + 2 RSVS" if jour == "MERCREDI" else "11 + 2 RSVS + 9 Salesiens"))
            
            data_pdej_totaux[jour] = st.number_input(f"Total P.Dej {jour} :", min_value=0, value=val_pdej, key=f"pdej_val_{jour}")
            data_pdej_details[jour] = st.text_input(f"Détail P.Dej {jour} (Parenthèses) :", value=det_pdej, key=f"pdej_det_{jour}")
            
        with c2:
            st.markdown("**🍽️ REPAS DU MIDI (Déjeuner)**")
            val_midi = 55 if jour != "VENDREDI" else 54
            det_midi = "37 + 1 RSVS + 10 MECS + 2P + 2 inv lycee + 3 RSM" if jour == "LUNDI" else \
                       ("33 + 3 RSVS + 5 MECS + 2P + 12 inv lycee" if jour == "MARDI" else \
                       ("30 + 2 RSVS + 9 Salesiens + 12 inv lycee + 2 RS (XDR/ChM)" if jour == "MERCREDI" else \
                       ("33 + 2 RSVS + 8 MECS + 3P + 9 Salesiens" if jour == "JEUDI" else "38 + 2 RSVS + 2P + 9 Salesiens + 3 RSM")))
                       
            data_midi_totaux[jour] = st.number_input(f"Total Midi {jour} :", min_value=0, value=val_midi, key=f"midi_val_{jour}")
            data_midi_details[jour] = st.text_input(f"Détail Midi {jour} (Parenthèses) :", value=det_midi, key=f"midi_det_{jour}")
            
        with c3:
            st.markdown("**🌙 REPAS DU SOIR (Dîner)**")
            val_soir = 15 if jour == "LUNDI" else (12 if jour == "MARDI" else (22 if jour in ["MERCREDI", "JEUDI"] else 0))
            det_soir = "13 + 2 RSVS" if jour == "LUNDI" else \
                       ("12 (10 + 2 RSVS)" if jour == "MARDI" else \
                       ("11 + 2RSVS + 9 Salesiens" if jour == "MERCREDI" else \
                       ("11 + 2 RSVS + 9 Salesiens" if jour == "JEUDI" else "")))
                       
            data_soir_totaux[jour] = st.number_input(f"Total Soir {jour} :", min_value=0, value=val_soir, key=f"soir_val_{jour}")
            data_soir_details[jour] = st.text_input(f"Détail Soir {jour} (Parenthèses) :", value=det_soir, key=f"soir_det_{jour}")

st.write("---")
total_mecs_input = st.number_input("Total cumulé MECS de la semaine (affiché en pied de page) :", min_value=0, value=23)

# 5. LOGIQUE DE CRÉATION DU DOCUMENT WORD DÉTAILLÉ
if st.button("📄 GÉNÉRER LE DOCUMENT WORD COMPLET (.DOCX)"):
    
    doc = Document()
    
    # 1. En-tête principal stylisé h1
    p_titre = doc.add_paragraph()
    p_titre.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_titre = p_titre.add_run(f"REEL POUR FACTURATION SEMAINE {num_semaine}\n")
    run_titre.font.name = 'Arial'
    run_titre.font.size = Pt(14)
    run_titre.font.bold = True
    
    # Dates de la semaine h2
    p_dates = doc.add_paragraph()
    p_dates.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_dates = p_dates.add_run(f"{dates_semaine}")
    run_dates.font.name = 'Arial'
    run_dates.font.size = Pt(11)
    run_dates.font.italic = True
    
    # 2. Construction du Tableau principal (6 lignes, 5 colonnes)
    table = doc.add_table(rows=1, cols=5)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    
    # Création des en-têtes de colonnes
    hdr_cells = table.rows[0].cells
    headers = ["", "PETIT DEJEUNER", "MIDI", "GOUTER", "SOIR"]
    for i, title in enumerate(headers):
        hdr_cells[i].text = title
        hdr_cells[i].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        hdr_cells[i].paragraphs[0].runs[0].font.bold = True
        hdr_cells[i].paragraphs[0].runs[0].font.name = 'Arial'
        hdr_cells[i].paragraphs[0].runs[0].font.size = Pt(10)
        # Application d'un fond bleu clair pastel sur les cellules d'en-tête
        shading = parse_xml(r'<w:shd {} w:fill="D9E1F2"/>'.format(nsdecls('w')))
        hdr_cells[i]._tc.get_or_add_tcPr().append(shading)
        
    # 3. Remplissage intelligent des lignes du lundi au vendredi
    for jour in jours:
        row_cells = table.add_row().cells
        
        # Colonne 1 : Jour
        row_cells[0].text = jour
        
        # Colonne 2 : Petit Déjeuner (Formate la valeur + son détail s'il existe)
        pdej_txt = f"{data_pdej_totaux[jour]}"
        if data_pdej_details[jour].strip():
            pdej_txt += f" ({data_pdej_details[jour].strip()})"
        row_cells[1].text = pdej_txt if data_pdej_totaux[jour] > 0 else "0"
        
        # Colonne 3 : Midi
        midi_txt = f"{data_midi_totaux[jour]}"
        if data_midi_details[jour].strip():
            midi_txt += f" ({data_midi_details[jour].strip()})"
        row_cells[2].text = midi_txt
        
        # Colonne 4 : Goûter
        row_cells[3].text = "12" if jour != "VENDREDI" else ""
        
        # Colonne 5 : Soir
        soir_txt = f"{data_soir_totaux[jour]}"
        if data_soir_details[jour].strip():
            soir_txt += f" ({data_soir_details[jour].strip()})"
        row_cells[4].text = soir_txt if data_soir_totaux[jour] > 0 else ""
        
        # Centrer tous les textes à l'intérieur des lignes de données du tableau
        for cell in row_cells:
            cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            if len(cell.paragraphs[0].runs) > 0:
                cell.paragraphs[0].runs[0].font.name = 'Arial'
                cell.paragraphs[0].runs[0].font.size = Pt(9.5)
                
    # 4. Ajout de la ligne récapitulative finale pour le Total MECS
    total_cells = table.add_row().cells
    total_cells[0].text = "TOTAL MECS"
    total_cells[2].text = f"{total_mecs_input}"
    
    # Style de la ligne de total (Gras + Fond gris léger)
    for idx, cell in enumerate(total_cells):
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER if idx != 0 else WD_ALIGN_PARAGRAPH.LEFT
        if len(cell.paragraphs[0].runs) > 0:
            cell.paragraphs[0].runs[0].font.bold = True
            cell.paragraphs[0].runs[0].font.name = 'Arial'
            cell.paragraphs[0].runs[0].font.size = Pt(10)
        shd = parse_xml(r'<w:shd {} w:fill="F2F2F2"/>'.format(nsdecls('w')))
        cell._tc.get_or_add_tcPr().append(shd)

    # 5. Conversion et envoi du fichier Docx fini vers le bouton de téléchargement
    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    
    # Sauvegarde optionnelle dans Firebase pour archivage
    if db:
        try:
            db.collection("nadutil_word_history").document(f"Semaine_{num_semaine}").set({
                "semaine": num_semaine, "dates": dates_semaine, "total_mecs": total_mecs_input
            })
        except Exception:
            pass
            
    st.success("🟢 Document Word complet construit avec l'intégralité de vos détails de parenthèses !")
    
    st.download_button(
        label="📥 TÉLÉCHARGER LE FICHIER WORD DÉTAILLÉ (.docx)",
        data=doc_io,
        file_name=f"Facturation_Detaillee_Semaine_{num_semaine}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
