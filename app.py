import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from PIL import Image, ImageOps
import pytesseract
import io

# 1. CONFIGURATION DE L'INTERFACE
st.set_page_config(page_title="Nadutil - Restauration Scolaire", page_icon="📊", layout="wide")
st.title("📊 Application Autonome Nadutil")
st.subheader("Analyse de la Restauration Scolaire - Lycée Costa de Beauregard")

# 2. INITIALISATION SECURISEE DE FIREBASE
if not firebase_admin._apps:
    try:
        firebase_secrets = dict(st.secrets["firebase"])
        cred = credentials.Certificate(firebase_secrets)
        firebase_admin.initialize_app(cred)
        st.sidebar.success("🟢 Base de données Firebase connectée !")
    except Exception:
        st.sidebar.warning("🟡 Mode local actif ou Firebase non configuré dans les Secrets.")

db = firestore.client() if firebase_admin._apps else None

# 3. ZONE D'IMPORTATION DE LA PHOTO
st.write("### 📸 Option A : Importez la photo ou le scan de votre feuille de semaine")
fichier_image = st.file_uploader("Sélectionnez ou glissez la photo ici (PNG, JPG, JPEG) :", type=["png", "jpg", "jpeg"])

texte_extrait = ""

if fichier_image is not None:
    image_brute = Image.open(fichier_image)
    try:
        image = ImageOps.exif_transpose(image_brute)
    except Exception:
        image = image_brute
        
    st.image(image, caption="Feuille traitée par l'application", width=400)
    
    with st.spinner("🧠 Analyse optique et lecture de la feuille en cours..."):
        try:
            texte_extrait = pytesseract.image_to_string(image, lang='fra')
        except Exception as e:
            st.error(f"🔴 Erreur de lecture de l'image : {e}")

# ZONE DE SECOURS PAR COPIER-COLLER TEXTE
st.write("---")
st.write("### 📝 Option B (Secours) : Ou collez directement le format texte/CSV de la semaine")
texte_colle = st.text_area("Zone de collage direct (Si la photo est illisible ou raturée) :", height=200, placeholder="Collez vos données brutes ici...")

if texte_colle.strip():
    texte_extrait = texte_colle

# 4. TRAITEMENT DES DONNÉES ET GÉNÉRATION DU FICHIER EXCEL STYLISÉ
if texte_extrait.strip():
    st.write("### ⚙️ 2. Traitement des lignes d'élèves et génération du pointage")
    
    import openpyxl
    from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
    
    lignes = texte_extrait.strip().split("\n")
    donnees_propres = []
    jours_colonnes = ["LUNDI_Midi", "LUNDI_Soir", "MARDI_Midi", "MARDI_Soir", "MERCREDI_Midi", "MERCREDI_Soir", "JEUDI_Midi", "JEUDI_Soir", "VENDREDI_Midi", "VENDREDI_Soir"]
    classe_actuelle = "Inconnue"
    
    for ligne in lignes:
        ligne_nettoyee = ligne.strip()
        if not ligne_nettoyee or ligne_nettoyee.startswith(",,,,"):
            continue
            
        # Détection de la classe / section
        if any(c in ligne_nettoyee for c in ["4ème", "3ème", "CAPA", "2DE", "BAC PRO", "TERM", "BTS", "Ste ", "St ", "SECONDES", "PREMIERES", "TERMINALES"]):
            classe_actuelle = ligne_nettoyee.replace(",", " ").strip()
            continue
            
        # Ignorer les lignes de structure de l'en-tête ou totaux
        if "NOM" in ligne_nettoyee or "EFFECTIF" in ligne_nettoyee or "INTERNES" in ligne_nettoyee or "COSTA" in ligne_nettoyee:
            continue
            
        # Découpage intelligent (gère les virgules ou les espaces multiples dus à l'OCR)
        if "," in ligne_nettoyee:
            elements = [e.strip() for e in ligne_nettoyee.split(",")]
        else:
            elements = [e.strip() for e in ligne_nettoyee.split() if e.strip()]
            
        # Validation d'une ligne élève : Recherche d'un indicateur de régime (D, P, APP)
        regime_trouve = None
        idx_regime = -1
        for idx, r in enumerate(elements):
            if r in ["D", "P", "D/F", "APP"]:
                regime_trouve = r
                idx_regime = idx
                break
                
        if regime_trouve and idx_regime >= 2:
            nom = " ".join(elements[:idx_regime-1]) if idx_regime > 2 else elements[0]
            prenom = elements[idx_regime-1]
            regime = regime_trouve
            
            # Extraction des notes de présences spécifiques (PN, EXC, ABS)
            repas_existants = elements[idx_regime+1:idx_regime+11]
            while len(repas_existants) < 10:
                repas_existants.append("")
                
            repas_calcules = []
            for idx_rep, case in enumerate(repas_existants):
                est_midi = (idx_rep % 2 == 0)
                
                # Conserver les statuts spécifiques de la feuille
                if case in ["PN", "EXC", "ABS", "REPAS"]:
                    repas_calcules.append(case)
                # Attribution automatique des coches X
                elif "P" in regime:
                    repas_calcules.append("X")  # Pensionnaire / Interne mange Midi et Soir
                elif "D" in regime and est_midi:
                    repas_calcules.append("X")  # Demi-pensionnaire mange uniquement le Midi
                else:
                    repas_calcules.append("")
            
            # Structuration finale de l'élève
            ligne_eleve = {"Classe / Section": classe_actuelle, "Nom": nom, "Prénom": prenom, "Régime": regime}
            for j, jour_label in enumerate(jours_colonnes):
                ligne_eleve[jour_label] = repas_calcules[j]
                
            donnees_propres.append(ligne_eleve)
            
            # Sauvegarde automatique dans la collection Firebase nadutil_eleves
            if db:
                try:
                    db.collection("nadutil_eleves").document(f"{classe_actuelle}_{nom}_{prenom}").set(ligne_eleve)
                except Exception:
                    pass

    # 5. CONSTRUCTION DU TABLEAU EXCEL
    if donnees_propres:
        df = pd.DataFrame(donnees_propres)
        st.success("🟢 Analyse terminée ! Voici le tableau complet généré automatiquement :")
        st.dataframe(df, use_container_width=True)
        
        # Création du classeur Excel stylisé avec OpenPyXL
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Suivi Présence"
        ws.views.sheetView.showGridLines = True
        
        # Titres de la feuille
        ws["A1"] = "LYCEE COSTA DE BEAUREGARD"
        ws["A1"].font = Font(name="Arial", size=14, bold=True, color="1F4E78")
        ws.merge_cells("A1:N1")
        
        ws["A2"] = "Suivi Automatisé des Présences de Restauration Scolaire"
        ws["A2"].font = Font(name="Arial", size=11, italic=True, color="595959")
        ws.merge_cells("A2:N2")
        
        headers_principaux = ["Classe / Section", "Nom", "Prénom", "Régime"]
        for col_num, header in enumerate(headers_principaux, 1):
            ws.cell(row=4, column=col_num, value=header)
            ws.merge_cells(start_row=4, start_column=col_num, end_row=5, end_column=col_num)
            
        jours_header = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI"]
        current_col = 5
        for jour in jours_header:
            ws.cell(row=4, column=current_col, value=jour)
            ws.merge_cells(start_row=4, start_column=current_col, end_row=4, end_column=current_col+1)
            ws.cell(row=5, column=current_col, value="Midi")
            ws.cell(row=5, column=current_col+1, value="Soir")
            current_col += 2
            
        fill_header = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        font_header = Font(name="Arial", size=10, bold=True)
        thin_border = Border(left=Side(style='thin', color='A6A6A6'), right=Side(style='thin', color='A6A6A6'), top=Side(style='thin', color='A6A6A6'), bottom=Side(style='thin', color='A6A6A6'))
        
        # Style des en-têtes
        for r in:
            for c in range(1, 15):
                cell = ws.cell(row=r, column=c)
                cell.fill = fill_header
                cell.font = font_header
                cell.alignment = Alignment(horizontal="center", vertical="center")
                cell.border = thin_border
                
        # Écriture des données
        for index, row in df.iterrows():
            row_data = [row["Classe / Section"], row["Nom"], row["Prénom"], row["Régime"], row["LUNDI_Midi"], row["LUNDI_Soir"], row["MARDI_Midi"], row["MARDI_Soir"], row["MERCREDI_Midi"], row["MERCREDI_Soir"], row["JEUDI_Midi"], row["JEUDI_Soir"], row["VENDREDI_Midi"], row["VENDREDI_Soir"]]
            ws.append(row_data)
            current_row = ws.max_row
            for c in range(1, 15):
                cell = ws.cell(row=current_row, column=c)
                cell.font = Font(name="Arial", size=10)
                cell.border = thin_border
                if c > 4:
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    if cell.value in ["PN", "EXC", "ABS"]:
                        cell.font = Font(name="Arial", size=10, bold=True)
                        
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col.column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 10)
            
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        st.write("### 📥 3. Récupérez votre document")
        st.download_button(
            label="📥 TÉLÉCHARGER LE FICHIER EXCEL (.xlsx)",
            data=buffer,
            file_name="Suivi_Rentrée_Cantine_Complete.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.warning("⚠️ Aucun élève valide détecté. Vérifiez la structure de votre texte ou utilisez l'Option B pour copier-coller votre liste.")
