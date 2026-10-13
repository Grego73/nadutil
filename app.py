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
# 1. CONFIGURATION DE LA PAGE (TAILLE MAX DE L'ECRAN)
# ==========================================
st.set_page_config(
    page_title="Générateur de Facturation Word",
    layout="wide",  # Force l'affichage à s'adapter à la largeur maximale de l'écran
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. INITIALISATION DES APIS
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

# ==========================================
# 3. FONCTION DE GENERATION DU FICHIER WORD
# ==========================================
def generer_fichier_word(semaine, date_facturation, donnees_jours):
    doc = Document()
    
    # Style de la police par défaut (Arial 11)
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(11)
    
    # En-tête exact de votre modèle
    p_titre = doc.add_paragraph()
    run1 = p_titre.add_run(f"¨REEL POUR FACTURATION SEMAINE {semaine}\n")
    run1.bold = True
    p_titre.add_run(f"{date_facturation}")
    
    # Création du tableau quadrillé (1 en-tête + 5 lignes de jours, 3 colonnes : JOUR, MIDI, SOIR)
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    
    # CORRECTION ICI : On cible la première ligne avec [0]
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'JOUR'
    hdr_cells[1].text = 'MIDI'
    hdr_cells[2].text = 'SOIR'
    
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
        row_cells[1].text = str(repas.get('midi', '0'))
        row_cells[2].text = str(repas.get('soir', '0'))
        
    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    return doc_io

# ==========================================
# 4. INTERFACE GRAPHIQUE STREAMLIT
# ==========================================
st.title("📊 Générateur de Facturation Word - Version Large")
st.write("Importez la photo de la semaine pour générer votre fichier Word.")

uploaded_file = st.file_uploader("Choisir une image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image)
    
    # Affichage de l'image redimensionnée de manière plus discrète pour gagner de la place
    st.image(image, caption="Feuille importée", width=500)
    
    if st.button("🪄 Extraire et structurer les données de facturation"):
        with st.spinner("Analyse approfondie de l'image en cours..."):
            try:
                # Encodage de la photo
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                import base64
                encoded_img = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                
                # Prompt réajusté pour éviter les inversions et capturer TOUS les détails du Midi et du Soir
                prompt = """
                Analyse cette feuille de repas et extrais les données de facturation pour le 'MIDI' (Déjeuner) et le 'SOIR' (Dîner).
                Sois extrêmement vigilant à ne pas inverser le Midi et le Soir.
                
                Pour chaque case, écris le total validé suivi du calcul détaillé complet trouvé sur le document entre parenthèses.
                Exemple pour le Midi (Déjeuner) : "140 (122 + 2 RSVS + 11 Necs + 3 P + 2 RS)"
                Exemple pour le Soir (Dîner) : "100 (Costa 45 + StG 6 + StA 39 + BTS 2 + Educ 2 + NECS 5 + 2)"
                Inclus impérativement TOUTE la décomposition des groupes (Costa, StG, StA, BTS, Educ, Necs) et les petits ajouts (+2, +3, etc.) pour le Soir.
                Si une section est vide (comme le vendredi soir), mets "0".
                
                Réponds UNIQUEMENT avec un code JSON respectant exactement cette structure, sans texte avant ni après, et sans balises de code (pas de ```json) :
                {
                  "semaine": "37",
                  "dates": "Du 7 au 11 septembre 2026",
                  "jours": {
                    "Lundi": {
                      "midi": "140 (122 + 2 RSVS + 11 Necs + 3 P + 2 RS)",
                      "soir": "100 (Costa 45 + StG 6 + StA 39 + BTS 2 + Educ 2 + NECS 5 + 2)"
                    },
                    "Mardi": {
                      "midi": "132 (121 + 2 RSVS + 4 Mecs + 5 P)",
                      "soir": "100 (Costa 43 + BTS 02 + Educ 02 + NECS 05 + StG 06 + StA 35 + 3)"
                    },
                    "Mercredi": {
                      "midi": "89 (86 + 2 RSVS + 1 P)",
                      "soir": "86 (Costa 40 + BTS 2 + Educ 2 + NECS 4 + StG 5 + StA 33 + 2)"
                    },
                    "Jeudi": {
                      "midi": "138 (122 + 2 RSVS + 8 Necs + 6 P)",
                      "soir": "97 (Costa 43 + BTS 02 + Educ 03 + NECS 06 + StG 06 + StA 36 + Invité 01)"
                    },
                    "Vendredi": {
                      "midi": "131 (113 + 2 RSVS + 10 Mecs + 5 P + 1 invité)",
                      "soir": "0"
                    }
                  }
                }
                """
                
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
                
                texte_ia = completion.choices[0].message.content.strip()
                
                if "```json" in texte_ia:
                    texte_ia = texte_ia.split("```json")[1].split("```")[0].strip()
                elif "```" in texte_ia:
                    texte_ia = texte_ia.split("```")[1].split("```")[0].strip()
                
                st.session_state['repas_extraits'] = json.loads(texte_ia)
                st.success("Données lues et redressées avec succès !")
                
            except Exception as e:
                st.error(f"Erreur de traitement. Réessayez. Détail : {e}")

# ==========================================
# 5. AFFICHAGE ET TELECHARGEMENT (MÉTHODE LARGE)
# ==========================================
if 'repas_extraits' in st.session_state:
    res = st.session_state['repas_extraits']
    sem = res.get('semaine', '37')
    dates = res.get('dates', 'Du 7 au 11 septembre 2026')
    jours_dict = res.get('jours', {})
    
    st.markdown("---")
    st.subheader(f"📝 Grille de Révision de la Semaine {sem}")
    st.info(f"📅 Période détectée : {dates}")
    
    donnees_finales = {}
    
    # Affichage en colonnes larges et claires (JOUR | CALCUL MIDI | CALCUL SOIR)
    for j in ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]:
        repas_j = jours_dict.get(j, {})
        
        st.markdown(f"### 🗓️ {j.upper()}")
        col1, col2 = st.columns(2)  # Découpe l'écran en deux colonnes géantes pour le confort visuel
        
        with col1:
            m = st.text_input(f"Repas du MIDI - {j}", value=repas_j.get('midi', '0'), key=f"midi_{j}")
        with col2:
            s = st.text_input(f"Repas du SOIR - {j}", value=repas_j.get('soir', '0'), key=f"soir_{j}")
            
        donnees_finales[j] = {"midi": m, "soir": s}
        st.markdown(" ")
        
    st.markdown("---")
    
    # Préparation et bouton de téléchargement du fichier Word
    fichier_docx = generer_fichier_word(sem, dates, donnees_finales)
    
    st.download_button(
        label="📥 Générer et Télécharger le fichier Word (.docx) de Facturation",
        data=fichier_docx,
        file_name=f"Facturation_Semaine_{sem}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True  # Le bouton prend toute la largeur pour être bien visible
    )
