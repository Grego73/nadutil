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
    chaine_texte = str(chaine_texte).strip()
    if not chaine_texte or chaine_texte == "0":
        return True, 0, 0
        
    try:
        total_ecrit_match = re.match(r"^(\d+)", chaine_texte)
        if not total_ecrit_match:
            return False, 0, 0
        total_ecrit = int(total_ecrit_match.group(1))
        
        parentheses_content = re.search(r"\((.*?)\)", chaine_texte)
        if not parentheses_content:
            return True, total_ecrit, total_ecrit
            
        formule = parentheses_content.group(1)
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
        
        # Correction automatique Midi
        val_midi = str(repas.get('midi', '0')).strip()
        est_conforme_m, inscrit_m, somme_m = verifier_calcul_formule(val_midi)
        if not est_conforme_m and somme_m > 0:
            val_midi = re.sub(r"^\d+", str(somme_m), val_midi)
        row_cells[1].text = val_midi
        
        # Correction automatique Soir
        val_soir = str(repas.get('soir', '0')).strip()
        est_conforme_s, inscrit_s, somme_s = verifier_calcul_formule(val_soir)
        if not est_conforme_s and somme_s > 0:
            val_soir = re.sub(r"^\d+", str(somme_s), val_soir)
        row_cells[2].text = val_soir
        
    doc_io = io.BytesIO()
    doc.save(doc_io)
    doc_io.seek(0)
    return doc_io

# ==========================================
# 5. INTERFACE UTILISATEUR STREAMLIT
# ==========================================
st.title("📊 Numérisation, Audit de Calculs & Export Word")
st.write("Importez la photo de votre feuille pour auditer les additions.")

uploaded_file = st.file_uploader("Choisir une image...", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    image = ImageOps.exif_transpose(image)
    st.image(image, caption="Feuille importée", width=400)
    
    if st.button("🪄 Lancer l'analyse et la vérification des additions"):
        with st.spinner("L'IA décrypte l'écriture manuscrite et extrait les formules..."):
            try:
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='JPEG')
                import base64
                encoded_img = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
                
                # Prompt ultra-condensé avec clés courtes pour économiser les jetons
                prompt = """
                Analyse la feuille de repas. Extrais tous les jours de la semaine pour MIDI et SOIR.
                Pour chaque case, donne le total suivi du calcul complet entre parenthèses.
                Si une case est vide, mets "0". Ne coupe jamais avant vendredi.
                
                Format JSON attendu :
                {
                  "sem": "37",
                  "dates": "Du 7 au 11 septembre 2026",
                  "jours": {
                    "Lundi": {"m": "140 (122 + 2 RSVS + 11 Necs + 3 P + 2 RS)", "s": "100 (Costa 45 + StG 6 + StA 39 + BTS 2 + Educ 2 + NECS 5 + 2)"},
                    "Mardi": {"m": "132 (121 + 2 RSVS + 4 Mecs + 5 P)", "s": "100 (Costa 43 + BTS 02 + Educ 02 + NECS 05 + StG 06 + StA 35 + 3)"},
                    "Mercredi": {"m": "89 (86 + 2 RSVS + 1 P)", "s": "86 (Costa 40 + BTS 2 + Educ 2 + NECS 4 + StG 5 + StA 33 + 2)"},
                    "Jeudi": {"m": "138 (122 + 2 RSVS + 8 Necs + 6 P)", "s": "97 (Costa 43 + BTS 02 + Educ 03 + NECS 06 + StG 06 + StA 36 + Invité 01)"},
                    "Vendredi": {"m": "131 (113 + 2 RSVS + 10 Mecs + 5 P + 1 invité)", "s": "0"}
                  }
                }
                """
                
                # Appel API avec max_tokens augmenté pour inclure le vendredi au complet
                completion = client_groq.chat.completions.create(
                    messages=[{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_img}"}}]}],
                    model="qwen/qwen3.8-27b",
                    temperature=0.0,
                    max_tokens=500,  # <--- MODIFIEZ CETTE VALEUR ICI (Passez de 400 à 500)
                    response_format={"type": "json_object"}
                )
                
                # CORRECTION COMPLÈTE ICI : Ajout du [0] pour éviter l'erreur de liste
                texte_ia = completion.choices[0].message.content.strip()
                
                brut_data = json.loads(texte_ia)
                
                # Reconstruction des clés longues pour l'interface
                structure_propre = {
                    "semaine": brut_data.get("sem", "37"),
                    "dates": brut_data.get("dates", ""),
                    "jours": {}
                }
                
                for jour, valeurs in brut_data.get("jours", {}).items():
                    structure_propre["jours"][jour] = {
                        "midi": valeurs.get("m", "0"),
                        "soir": valeurs.get("s", "0")
                    }
                
                st.session_state['repas_extraits'] = structure_propre
                st.success("Données de la semaine complète extraites avec succès !")
                
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
        
        with col1:
            val_midi = st.text_input(f"Formule MIDI - {j}", value=repas_j.get('midi', '0'), key=f"midi_{j}")
            est_conforme_m, inscrit_m, somme_m = verifier_calcul_formule(val_midi)
            if val_midi != "0":
                if est_conforme_m:
                    st.success(f"🟢 Addition Conforme (Somme = {somme_m})")
                else:
                    st.error(f"🔴 Erreur d'Addition sur la feuille ! Écrit = {inscrit_m} vs Somme Réelle = {somme_m}")
                    
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
    
    fichier_docx = generer_fichier_word(sem, dates, donnees_finales)
    st.download_button(
        label="📥 Générer et Télécharger le fichier Word (.docx) de Facturation Vérifié",
        data=fichier_docx,
        file_name=f"Facturation_Semaine_{sem}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        use_container_width=True
    )
