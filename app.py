import streamlit as st
import pandas as pd
import io

# Configuration de la page Streamlit
st.set_page_config(page_title="Nadutil - Gestion Cantine", page_icon="📊", layout="wide")

st.title("📊 Bienvenue sur Nadutil")
st.subheader("Gestion de la Restauration Scolaire - Lycée Costa de Beauregard")

# --- CASE POUR COLLER LA FEUILLE DE SEMAINE ---
st.write("### 📅 1. Collez le contenu de votre feuille de semaine ci-dessous :")
texte_brut = st.text_area("Zone de collage (Format CSV / Texte brut) :", height=300, 
                          placeholder="Collez vos données ici (ex: NOM, PRENOM, REGIME...)")

# --- BOUTON DE TRAITEMENT ---
if st.button("⚙️ Analyser et Générer le fichier Excel"):
    if not texte_brut.strip():
        st.warning("⚠️ Veuillez coller des données avant de lancer l'analyse.")
    else:
        lignes = texte_brut.strip().split("\n")
        donnees_completes = []
        entete_jours = ["LUNDI_Midi", "LUNDI_Soir", "MARDI_Midi", "MARDI_Soir", 
                        "MERCREDI_Midi", "MERCREDI_Soir", "JEUDI_Midi", "JEUDI_Soir", 
                        "VENDREDI_Midi", "VENDREDI_Soir"]
        
        classe_actuelle = "Inconnue"
        
        # Algorithme d'analyse automatique (celui développé pour votre script)
        for ligne in lignes:
            ligne_nettoyee = ligne.strip()
            if not ligne_nettoyee:
                continue
                
            if any(c in ligne_nettoyee for c in ["4ème", "3ème", "CAPA", "2DE", "BAC PRO", "TERM", "BTS", "Ste ", "St "]):
                classe_actuelle = ligne_nettoyee.replace(",", "").strip()
                continue
                
            if "NOM" in ligne_nettoyee or "EFFECTIF" in ligne_nettoyee:
                continue
                
            elements = [e.strip() for e in ligne_nettoyee.split(",")]
            
            if len(elements) >= 3 and elements[2] in ["D", "P", "D/F", "APP"]:
                nom = elements[0]
                prenom = elements[1]
                regime = elements[2]
                
                repas_saisis = elements[3:13]
                while len(repas_saisis) < 10:
                    repas_saisis.append("")
                    
                repas_finals = []
                for i, case in enumerate(repas_saisis):
                    est_midi = (i % 2 == 0)
                    if case in ["PN", "EXC", "ABS", "REPAS"]:
                        repas_finals.append(case)
                    elif regime == "P":
                        repas_finals.append("X")
                    elif regime == "D" and est_midi:
                        repas_finals.append("X")
                    else:
                        repas_finals.append("")
                
                ligne_eleve = {"Classe/Section": classe_actuelle, "Nom": nom, "Prénom": prenom, "Régime": regime}
                for j, jour_repas in enumerate(entete_jours):
                    ligne_eleve[jour_repas] = repas_finals[j]
                    
                donnees_completes.append(ligne_eleve)
        
        if donnees_completes:
            df = pd.DataFrame(donnees_completes)
            
            # Affichage du tableau à l'écran dans Streamlit
            st.success("🟢 Analyse terminée avec succès ! Voici un aperçu des données :")
            st.dataframe(df, use_container_width=True)
            
            # Génération du fichier Excel en mémoire
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Suivi Cantine')
            buffer.seek(0)
            
            # --- BOUTON DE TELECHARGEMENT ---
            st.write("### 📥 2. Téléchargez votre fichier Excel mis à jour :")
            st.download_button(
                label="📥 TÉLÉCHARGER LE FICHIER EXCEL (.xlsx)",
                data=buffer,
                file_name="Suivi_Semaine_Cantine.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.error("🔴 Aucun élève valide détecté. Vérifiez le format du texte collé.")

# --- ZONE FUTURE FIREBASE ---
st.sidebar.write("### 🔒 Connexion Firebase")
st.sidebar.info("Prochaine étape : Liaison de la base de données Firebase pour sauvegarder l'historique des élèves.")
