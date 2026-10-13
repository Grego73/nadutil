import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image, ImageOps
import io
import json
from groq import Groq
from docx import Document  # Bibliothèque pour créer le fichier Word
from docx.shared import Inches, Pt

# ==========================================
# 1. CONFIGURATION DES APIS & CONFIG
# ==========================================

GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
client_groq = Groq(api_key=GROQ_API_KEY)

if not firebase_admin._apps:
    firebase_creds = dict(st.secrets["text_key"])
    if "private_key" in firebase_creds:
        firebase_creds["private_key"] = firebase_creds["private_key"].replace("\\n", "\n")
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# Fonction interne pour fabriquer le fichier Word comme votre modèle
def generer_fichier_word(semaine, annee, donnees_jours):
    doc = Document()
    
    # Styles globaux du document
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(11)
    
    # Titre du document Word
    p_titre = doc.add_paragraph()
    run_titre = p_titre.add_run(f"REEL POUR FACTURATION SEMAINE {semaine}\n")
    run_titre.bold = True
    run_titre.font.size = Pt(14)
    
    p_titre.add_run(f"Année {annee}\nDocument généré automatiquement après certification.")
    
    # Création du tableau : 6 lignes (En-tête + 5 Jours) et 5 colonnes
    table = doc.add_table(rows=1, cols=5)
    table.style = 'Table Grid'  # Applique des bordures standard propres
    
    # En-tête du tableau
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'JOUR'
    hdr_cells[1].text = 'PETIT DEJEUNER'
    hdr_cells[2].text = 'MIDI'
    hdr_cells[3].text = 'GOUTER'
    hdr_cells[4].text = 'SOIR'
    
    # Rendre l'en-tête en gras
    for cell in hdr_cells:
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.bold = True
                
    # Remplissage des lignes par jour de la semaine
    for jour, repas in donnees_jours.items():
        row_cells = table.add_row().cells
        row_cells[0].text = jour.upper()
        
        # Petit déjeuner (0 par défaut si non spécifié)
        row_cells[1].text = str(repas.get('petit_dejeuner', '0'))
        
        # Midi (avec le détail du calcul si disponible)
        row_cells[2].text = str(repas.get('midi', '0'))
        
        # Goûter
        row_cells[3].text = str(repas.get('gouter', '0'))
        
        # Soir
        row_cells[4].text = str(repas.get('soir', '0'))
        
    # Sauvegarde dans un tampon mémoire pour le téléchargement Streamlit
    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    return doc_io

# ==========================================
# 2. INTERFACE UTILISATEUR (STREAMLIT)
# ==========================================

st.title("📊 Numérisation & Génération de Factures Word")
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
                
                # Prompt chirurgical exigeant le format JSON pour fabriquer le Word
                prompt = """
                Analyse cette feuille de restauration collective. Extrais toutes les données de la semaine.
                Décompose chaque ligne manuscrite en isolant la base et chaque abréviation pour le Midi et le Soir.
                Calcule ou récupère la chaîne explicative pour chaque case.
                
                Format exigé : Retourne UNIQUEMENT du JSON pur sans balise markdown avec cette structure :
                {
                  "semaine": "37",
                  "annee": "2026",
                  "jours": {
                    "Lundi": {"petit_dejeuner": "0", "midi": "140 (122 + 2 RSVS + 11 Mecs + 3 P + 2 RS)", "gouter": "0", "soir": "100 (Costa 45 + STG 6 + StA 39...)"},
                    "Mardi": {"petit_dejeuner": "15 (13 + 2 RSVS)", "midi": "132 (121 + 2 RSVS + 4 Mecs + 5 P)", "gouter": "12", "soir": "97 (Costa 43 + ...)"},
                    "Mercredi": {"petit_dejeuner": "12 (10 + 2 RSVS)", "midi": "89 (86 + 2 RSVS + 1 P)", "gouter": "12", "soir": "86"},
                    "Jeudi": {"petit_dejeuner": "22", "midi": "138 (122 + 2 RSVS + 8 Mecs + 6 P)", "gouter": "12", "soir": "97"},
                    "Vendredi": {"petit_dejeuner": "13", "midi": "131 (113 + 2 RSVS + 10 Mecs + 5 P + 1 inv)", "gouter": "", "soir": ""}
                  }
                }
                """
                
                chat_completion = client_groq.chat.completions.create(
                    messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}],
                    model="qwen/qwen3.8-27b",
                    temperature=0.0
                )
                
                json_text = chat_completion.choices.message.content.strip()
                if "```json" in json_text:
                    json_text = json_text.split("```json").split("```").strip()
                elif "```" in json_text:
                    json_text = json_text.split("```").split("```").strip()
                
                st.session_state['donnees_facturation_word'] = json.loads(json_text)
                st.success("Données extraites avec succès !")
            except Exception as e:
                st.error(f"Erreur d'analyse : {e}")

# ==========================================
# 3. INTERFACE DE TELECHARGEMENT ET FIREBASE
# ==========================================

if 'donnees_facturation_word' in st.session_state:
    data = st.session_state['donnees_facturation_word']
    semaine = data.get('semaine', '37')
    annee = data.get('annee', '2026')
    jours_data = data.get('jours', {})
    
    st.subheader(f"📝 Aperçu du Tableau de Facturation (Semaine {semaine})")
    
    # Formulaire interactif modifiable avant de générer le fichier Word
    valeurs_editees = {}
    for jour, repas in jours_data.items():
        st.markdown(f"#### 🗓️ {jour}")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            p_dej = st.text_input(f"P. Déj - {jour}", value=repas.get('petit_dejeuner', '0'), key=f"pdej_{jour}")
        with col2:
            midi = st.text_input(f"Midi - {jour}", value=repas.get('midi', '0'), key=f"midi_{jour}")
        with col3:
            gout = st.text_input(f"Goûter - {jour}", value=repas.get('gouter', '0'), key=f"gout_{jour}")
        with col4:
            soir = st.text_input(f"Soir - {jour}", value=repas.get('soir', '0'), key=f"soir_{jour}")
            
        valeurs_editees[jour] = {
            "petit_dejeuner": p_dej,
            "midi": midi,
            "gouter": gout,
            "soir": soir
        }
        
    st.markdown("---")
    
    # Génération du fichier Word en mémoire
    fichier_word_pret = generer_fichier_word(semaine, annee, valeurs_editees)
    
    # BOUTON DE TELECHARGEMENT WORD DIRECT !
    st.download_button(
        label="📥 Télécharger le fichier Word (.docx) conforme au modèle",
        data=fichier_word_pret,
        file_name=f"Facturation_Semaine_{semaine}_{annee}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    
    st.markdown(" ")
    
    if st.button("💾 Enregistrer une copie historique dans Firebase"):
        try:
            doc_id = f"facture_semaine_{semaine}_{annee}"
            db.collection("factures_word").document(doc_id).set({
                "semaine": int(semaine),
                "annee": int(annee),
                "tableau_donnees": valeurs_editees
            })
            st.balloons()
            st.success("Copie enregistrée dans Firestore !")
            del st.session_state['donnees_facturation_word']
            st.rerun()
        except Exception as e:
            st.error(f"Erreur Firebase : {e}")
