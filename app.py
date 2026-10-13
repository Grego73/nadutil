import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image, ImageOps
import io
import json
import re
from groq import Groq
from docx import Document  # Génération Word
from docx.shared import Pt

# ==========================================
# 1. CONFIGURATION DE LA PAGE (TAILLE MAX DE L'ECRAN)
# ==========================================
st.set_page_config(
    page_title="Générateur & Vérificateur de Facturation",
    layout="wide",  # Force l'affichage sur toute la largeur de l'écran
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
# 3. FONCTION DE VERIFICATION TECHNIQUE DES CALCULS
# ==========================================
def verifier_calcul_formule(chaine_texte):
    """
    Analyse une chaîne comme '140 (122 + 2 RSVS + 11 Necs + 3 P)' 
    et vérifie si la somme à l'intérieur des parenthèses est égale au total affiché.
    """
    chaine_texte = str(chaine_texte).strip()
    if not chaine_texte or chaine_texte == "0":
        return True, 0, 0
        
    try:
        # Extraire le total écrit au début
        total_ecrit_match = re.match(r"^(\d+)", chaine_texte)
        if not total_ecrit_match:
            return False, 0, 0
        total_ecrit = int(total_ecrit_match.group(1))
        
        # Extraire tout ce qui est à l'intérieur des parenthèses (...)
        parentheses_content = re.search(r"\((.*?)\)", chaine_texte)
        if not parentheses_content:
            # S'il n'y a pas de parenthèses (ex: juste écrit "86"), on considère que c'est juste
            return True, total_ecrit, total_ecrit
            
        formule = parentheses_content.group(1)
        # Extraire uniquement les nombres présents dans l'addition
        nombres = [int(n) for n in re.findall(r"\d+", formule)]
        somme_reelle = sum(nombres)
        
        return (total_ecrit == somme_reelle), total_ecrit, somme_reelle
    except:
        return False, 0, 0

# ==========================================
# 4. FONCTION DE GENERATION DU FICHIER WORD
# ==========================================
def generer_fichier_word(semaine, date_facturation, donnees_jours):
    doc = Document()
    
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Arial'
    font.size = Pt(11)
    
    p_titre = doc.add_paragraph()
    run1 = p_titre.add_run(f"¨REEL POUR FACTURATION SEMAINE {semaine}\n")
    run1.bold = True
    p_titre.add_run(f"{date_facturation}")
    
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = 'JOUR'
    hdr_cells[1].text = 'MIDI'
    hdr_cells[2].text = 'SOIR'
    
    for cell in hdr_cells:
        for p in cell.paragraphs:
            for r in p.runs:
                r.bold = True
                
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
# 5. INTERFACE UTILISATEUR STREAMLIT
# ==========================================
st.title("📊 Numérisation, Audit de Calculs & Export Word")
st.write("Importez la photo de votre feuille pour auditer les additions et générer le document de facturation.")

uploaded_file = st.file_uploader("Choisir une image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image)
    st.image(image, caption="Feuille importée", width=400)
    
    if st.button("🪄 Lancer l'analyse et la vérification des additions"):
        with st.spinner("L'IA décrypte l'écriture manuscrite et extrait les formules de calcul..."):
            try:
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                import base64
                encoded_img = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                
                prompt = """
                Analyse cette feuille de repas et extrais les données de facturation pour le 'MIDI' (Déjeuner) et le 'SOIR' (Dîner).
                Ne confonds jamais le Midi et le Soir.
                
                Pour chaque case, écris le total validé suivi du calcul détaillé trouvé sur le document entre parenthèses.
                Exemple pour le Midi : "140 (122 + 2 RSVS + 11 Necs + 3 P + 2 RS)"
                Exemple pour le Soir : "100 (Costa 45 + StG 6 + StA 39 + BTS 2 + Educ 2 + NECS 5 + 2)"
                Note bien l'intégralité des additions manuscrites pour le Soir. Si une case est vide, mets "0".
                
                Réponds UNIQUEMENT avec un code JSON respectant exactement cette structure, sans texte avant ni après, et sans balises de code :
                {
                  "semaine": "37",
                  "dates": "Du 7 au 11 septembre 2026",
                  "jours": {
                    "Lundi": {"midi": "140 (122 + 2 RSVS + 11 Necs + 3 P + 2 RS)", "soir": "100 (Costa 45 + StG 6 + StA 39 + BTS 2 + Educ 2 + NECS 5 + 2)"},
                    "Mardi": {"midi": "132 (121 + 2 RSVS + 4 Mecs + 5 P)", "soir": "100 (Costa 43 + BTS 02 + Educ 02 + NECS 05 + StG 06 + StA 35 + 3)"},
                    "Mercredi": {"midi": "89 (86 + 2 RSVS + 1 P)", "soir": "86 (Costa 40 + BTS 2 + Educ 2 + NECS 4 + StG 5 + StA 33 + 2)"},
                    "Jeudi": {"midi": "138 (122 + 2 RSVS + 8 Necs + 6 P)", "soir": "97 (Costa 43 + BTS 02 + Educ 03 + NECS 06 + StG 06 + StA 36 + Invité 01)"},
                    "Vendredi": {"midi": "131 (113 + 2 RSVS + 10 Mecs + 5 P + 1 invité)", "soir": "0"}
                  }
                }
                """
                
                completion = client_groq.chat.completions.create(
                    messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}}]}],
                    model="qwen/qwen3.8-27b",
                    temperature=0.0
                )
                
                texte_ia = completion.choices[0].message.content.strip()
                if "```json" in texte_ia:
                    texte_ia = texte_ia.split("```json")[1].split("```")[0].strip()
                elif "```" in texte_ia:
                    texte_ia = texte_ia.split("```")[1].split("```")[0].strip()
                
                st.session_state['repas_extraits'] = json.loads(texte_ia)
                st.success("Données extraites avec succès !")
                
            except Exception as e:
                st.error(f"Erreur d'analyse. Détail : {e}")

# ==========================================
# 6. GRILLE D'AUDIT ET VOYANTS DE CONFORMITÉ
# ==========================================
if 'repas_extraits' in st.session_state:
    res = st.session_state['repas_extraits']
    sem = res.get('semaine', '37')
    dates = res.get('dates', 'Du 7 au 11 septembre 2026')
    jours_dict = res.get('jours', {})
    
    st.markdown("---")
    st.subheader(f"📝 Grille d'Audit et de Correction (Semaine {sem})")
    st.info(f"📅 Période : {dates}")
    
    donnees_finales = {}
    
    for j in ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi"]:
        repas_j = jours_dict.get(j, {})
        st.markdown(f"### 🗓️ {j.upper()}")
        
        col1, col2 = st.columns(2)
        
        # --- TRAITEMENT DU MIDI ---
        with col1:
            val_midi = st.text_input(f"Formule MIDI - {j}", value=repas_j.get('midi', '0'), key=f"midi_{j}")
            est_conforme_m, inscrit_m, somme_m = verifier_calcul_formule(val_midi)
            if val_midi != "0":
                if est_conforme_m:
                    st.success(f"🟢 Addition Conforme (Somme = {somme_m})")
                else:
                    st.error(f"🔴 Erreur d'Addition sur la feuille ! Écrit = {inscrit_m} vs Somme Réelle = {somme_m}")
                    
        # --- TRAITEMENT DU SOIR ---
        with col2:
            val_soir = st.text_input(f"Formule SOIR - {j}", value=repas_j.get('soir', '0'), key=f"soir_{j}")
            est_conforme_s, inscrit_s, somme_s = verifier_calcul_formule(val_soir)
            if val_soir != "0":
                if est_conforme_s:
                    st.success(f"🟢 Addition Conforme (Somme = {somme_s})")
                else:
                    st.error(f"🔴 Erreur d'Addition sur la feuille ! Écrit = {inscrit_s} vs Somme Réelle = {somme_s}")
            elif j == "Vendredi":
                st.info("🟢 Établissement fermé le vendredi soir (0 repas)")
                
        donnees_finales[j] = {"midi": val_midi, "soir": val_soir}
        st.markdown(" ")
        
    st.markdown("---")
    
    # Bouton de téléchargement Word
    fichier_docx = generer_fichier_word(sem, dates, donnees_finales)
    st.download_button(
        label="📥 Générer et Télécharger le fichier Word (.docx) de Facturation Vérifié",
        data=fichier_docx,
        file_name=f"Facturation_Semaine_{sem}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True
    )
