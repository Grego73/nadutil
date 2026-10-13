import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image, ImageOps
import io
import json
from groq import Groq
from docx import Document  # Génération Word
from docx.shared import Pt

# ==========================================
# 1. INITIALISATION DES APIS (PROPRE)
# ==========================================

# Connexion Groq
GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
client_groq = Groq(api_key=GROQ_API_KEY)

# Connexion Firebase (Récupère la clé existante de votre calculateur)
if not firebase_admin._apps:
    firebase_creds = dict(st.secrets["text_key"])
    if "private_key" in firebase_creds:
        firebase_creds["private_key"] = firebase_creds["private_key"].replace("\\n", "\n")
    cred = credentials.Certificate(firebase_creds)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ==========================================
# 2. FONCTION DE GENERATION DU FICHIER WORD
# ==========================================
def generer_fichier_word(semaine, date_facturation, donnees_jours):
    doc = Document()
    
    # Style de la police par défaut (Arial 11 comme le modèle)
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(11)
    
    # En-tête exact de votre modèle
    p_titre = doc.add_paragraph()
    run1 = p_titre.add_run(f"¨REEL POUR FACTURATION SEMAINE {semaine}\n")
    run1.bold = True
    p_titre.add_run(f"{date_facturation}")
    
    # Création du tableau propre (1 en-tête + 5 lignes de jours, 5 colonnes)
    table = doc.add_table(rows=1, cols=5)
    table.style = 'Table Grid'
    
    # Titres des colonnes
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'JOUR'
    hdr_cells[1].text = 'PETIT DEJEUNER'
    hdr_cells[2].text = 'MIDI'
    hdr_cells[3].text = 'GOUTER'
    hdr_cells[4].text = 'SOIR'
    
    # Mettre l'en-tête du tableau en gras
    for cell in hdr_cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
                
    # Ajout des données extraites jour par jour
    liste_jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]
    for j in liste_jours:
        repas = donnees_jours.get(j, {})
        row_cells = table.add_row().cells
        row_cells[0].text = j.upper()
        row_cells[1].text = str(repas.get('petit_dejeuner', '0'))
        row_cells[2].text = str(repas.get('midi', '0'))
        row_cells[3].text = str(repas.get('gouter', '0'))
        row_cells[4].text = str(repas.get('soir', '0'))
        
    # Sauvegarde du document Word en mémoire
    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    return doc_io

# ==========================================
# 3. INTERFACE GRAPHIQUE STREAMLIT
# ==========================================
st.title("📊 Générateur de Facturation Word")
st.write("Importez la photo de la semaine pour générer votre fichier Word.")

uploaded_file = st.file_uploader("Choisir une image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # Lecture et redressement de l'image si elle est à l'envers
    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image)
    st.image(image, caption="Feuille importée", use_column_width=True)
    
    if st.button("🪄 Extraire les données de facturation"):
        with st.spinner("Analyse de l'image en cours..."):
            try:
                # Encodage de la photo pour l'IA
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                base64_image = io.BytesIO(img_byte_arr.getvalue()).read()
                import base64
                encoded_img = base64.b64encode(image_bytes := img_byte_arr.getvalue()).decode('utf-8')
                
                # Le prompt qui impose le format de votre modèle de document
                prompt = """
                Analyse cette feuille de repas et extrais les données de facturation de la semaine.
                Regarde les calculs détaillés pour chaque case (Petit Déjeuner, Midi, Goûter, Soir).
                Formate le résultat pour chaque jour en mettant le total suivi du calcul entre parenthèses, exemple : "55 (37 + 1 RSVS + 10 MECS + 2P + 2 inv lycee + 3 RSM)".
                Si une case est vide ou égale à 0, mets simplement "0".
                
                Tu dois répondre UNIQUEMENT avec un code JSON qui respecte mot pour mot cette structure, sans texte avant ni après, et sans balises de code (pas de ```json) :
                {
                  "semaine": "26",
                  "dates": "Du 22 au 26 juin 2026",
                  "jours": {
                    "Lundi": {"petit_dejeuner": "0", "midi": "55 (37 + 1 RSVS + 10 MECS + 2P + 2 inv lycee + 3 RSM)", "gouter": "12", "soir": "15 (13 + 2 RSVS)"},
                    "Mardi": {"petit_dejeuner": "15 (13 + 2 RSVS)", "midi": "55 (33 + 3 RSVS + 5 MECS + 2P + 12 inv lycee)", "gouter": "12", "soir": "12 (10 + 2 RSVS)"},
                    "Mercredi": {"petit_dejeuner": "12 (10 + 2 RSVS)", "midi": "55 (30 + 2 RSVS + 9 Salesiens + 12 inv lycee + 2 RS)", "gouter": "12", "soir": "22 (11 + 2RSVS + 9 Salesiens)"},
                    "Jeudi": {"petit_dejeuner": "22 (11 + 2 RSVS + 9 Salesiens)", "midi": "55 (33 + 2 RSVS + 8 MECS + 3P + 9 Salesiens)", "gouter": "12", "soir": "22 (11 + 2 RSVS + 9 Salesiens)"},
                    "Vendredi": {"petit_dejeuner": "13 (11 + 2 RSVS)", "midi": "54 (38 + 2 RSVS + 2P + 9 Salesiens + 3 RSM)", "gouter": "0", "soir": "0"}
                  }
                }
                """
                
                # Appel à l'API Groq (Correction définitive de la liste de choix effectuée ici)
                completion = client_groq.chat.completions.create(
                    messages=[{
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}}
                        ]
                    }],
                    model="qwen/qwen3.8-27b",
                    temperature=0.0
                )
                
                # Extraction du texte de façon 100% sécurisée
                texte_ia = completion.choices[0].message.content.strip()
                
                # Nettoyage si jamais l'IA ajoute des balises de code de force
                if "```json" in texte_ia:
                    texte_ia = texte_ia.split("```json")[1].split("```")[0].strip()
                elif "```" in texte_ia:
                    texte_ia = texte_ia.split("```")[1].split("```")[0].strip()
                
                # Sauvegarde du résultat
                st.session_state['repas_extraits'] = json.loads(texte_ia)
                st.success("Données lues avec succès !")
                
            except Exception as e:
                st.error(f"Désolé, l'IA a eu un problème de lecture. Réessayez. Détail : {e}")

# ==========================================
# 4. AFFICHAGE DES RESULTATS ET TELECHARGEMENT
# ==========================================
if 'repas_extraits' in st.session_state:
    res = st.session_state['repas_extraits']
    sem = res.get('semaine', '26')
    dates = res.get('dates', 'Du 22 au 26 juin 2026')
    jours_dict = res.get('jours', {})
    
    st.subheader(f"📝 Vérification de la Semaine {sem}")
    st.info(f"📅 Période détectée : {dates}")
    
    # Formulaire visuel pour corriger rapidement les cases si besoin avant d'exporter
    donnees_finales = {}
    for j in ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]:
        repas_j = jours_dict.get(j, {})
        st.markdown(f"**{j}**")
        c1, col2, col3, col4 = st.columns(4)
        with c1:
            pd = st.text_input("Petit Déj", value=repas_j.get('petit_dejeuner', '0'), key=f"pd_{j}")
        with col2:
            m = st.text_input("Midi", value=repas_j.get('midi', '0'), key=f"m_{j}")
        with col3:
            g = st.text_input("Goûter", value=repas_j.get('gouter', '0'), key=f"g_{j}")
        with col4:
            s = st.text_input("Soir", value=repas_j.get('soir', '0'), key=f"s_{j}")
            
        donnees_finales[j] = {"petit_dejeuner": pd, "midi": m, "gouter": g, "soir": s}
        
    st.markdown("---")
    
    # Génération instantanée du fichier Word à partir des cases ci-dessus
    fichier_docx = generer_fichier_word(sem, dates, donnees_finales)
    
    # Le bouton de téléchargement direct
    st.download_button(
        label="📥 Télécharger votre fichier Word (.docx) conforme",
        data=fichier_docx,
        file_name=f"Facturation_Semaine_{sem}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
