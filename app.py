import re
import tkinter as tk
from tkinter import messagebox, scrolledtext
import pandas as pd


def analyser_et_generer():
    # 1. Récupération du texte collé par l'utilisateur
    texte_brut = zone_texte.get("1.0", tk.END).strip()

    if not texte_brut:
        messagebox.showwarning(
            "Champ vide", "Veuillez coller le contenu de la semaine avant de lancer l'analyse."
        )
        return

    lignes = texte_brut.split("\n")
    donnees_completes = []
    entete_jours = [
        "LUNDI_Midi",
        "LUNDI_Soir",
        "MARDI_Midi",
        "MARDI_Soir",
        "MERCREDI_Midi",
        "MERCREDI_Soir",
        "JEUDI_Midi",
        "JEUDI_Soir",
        "VENDREDI_Midi",
        "VENDREDI_Soir",
    ]

    classe_actuelle = "Inconnue"

    # 2. Analyse ligne par ligne du texte collé
    for ligne in lignes:
        ligne_nettoyee = ligne.strip()
        if not ligne_nettoyee:
            continue

        # Détection du changement de classe/section
        if (
            "4ème" in ligne_nettoyee
            or "3ème" in ligne_nettoyee
            or "CAPA" in ligne_nettoyee
            or "2DE" in ligne_nettoyee
            or "BAC PRO" in list(map(str.upper, [ligne_nettoyee]))[0]
            or "TERM" in ligne_nettoyee
            or "BTS" in ligne_nettoyee
            or "Ste " in ligne_nettoyee
            or "St " in ligne_nettoyee
        ):
            classe_actuelle = ligne_nettoyee.split(",")[0].replace("¨", "").strip()
            continue

        # Ignorer les lignes d'en-tête de colonnes ou de totaux globaux
        if "NOM" in ligne_nettoyee or "EFFECTIF" in ligne_nettoyee or "INTERNES" in ligne_nettoyee:
            continue

        # Découpage des colonnes par virgule (format CSV transmis)
        elements = [e.strip() for e in ligne_nettoyee.split(",")]

        # Vérification s'il s'agit bien d'une ligne élève (Nom, Prénom, Régime)
        if len(elements) >= 3 and elements[2] in ["D", "P", "D/F", "APP"]:
            nom = elements[0]
            prenom = elements[1]
            regime = elements[2]

            # Extraction des statuts déjà saisis (ex: PN, EXC, ABS)
            # On complète jusqu'à avoir les 10 cases de repas (5 jours x 2)
            repas_saisis = elements[3:13]
            while len(repas_saisis) < 10:
                repas_saisis.append("")

            repas_finals = []
            for i, case in enumerate(repas_saisis):
                est_midi = i % 2 == 0

                # Si une note spécifique existe (PN, ABS, EXC), on la garde précieusement
                if case in ["PN", "EXC", "ABS", "REPAS"]:
                    repas_finals.append(case)
                # Sinon, on applique les règles automatiques selon le régime de l'élève
                elif regime == "P":
                    repas_finals.append("X")  # Pensionnaire mange Midi ET Soir
                elif regime == "D" and est_midi:
                    repas_finals.append("X")  # Demi-pensionnaire mange uniquement le Midi
                else:
                    repas_finals.append("")  # Ne mange pas

            # Structuration de la ligne de données pour le tableau final
            ligne_eleve = {"Classe/Section": classe_actuelle, "Nom": nom, "Prénom": prenom, "Régime": regime}
            for j, jour_repas in enumerate(entete_jours):
                ligne_eleve[jour_repas] = repas_finals[j]

            donnees_completes.append(ligne_eleve)

    # 3. Conversion en DataFrame Pandas et Exportation Excel
    if donnees_completes:
        df = pd.DataFrame(donnees_completes)

        nom_fichier = "Suivi_Semaine_Complete.xlsx"
        # Sauvegarde brute propre avec des colonnes ordonnées
        colonnes_ordre = ["Classe/Section", "Nom", "Prénom", "Régime"] + entete_jours
        df[colonnes_ordre].to_excel(nom_fichier, index=False)

        messagebox.showinfo(
            "Succès !",
            f"Le fichier Excel '{nom_fichier}' a été généré avec succès en appliquant toutes les coche 'X' réglementaires !",
        )
    else:
        messagebox.showerror(
            "Erreur d'analyse", "Aucun élève valide n'a pu être détecté. Vérifiez le format de votre texte."
        )


# 4. Configuration de la Fenêtre Graphique (Interface Utilisateur)
root = tk.Tk()
root.title("Générateur Automatique de Présences Cantine - Lycée Costa")
root.geometry("850x650")
root.configure(bg="#f4f6f9")

# Titre principal de la fenêtre
label_titre = tk.Label(
    root,
    text="COLLEZ LE CONTENU DE VOTRE FEUILLE DE SEMAINE CI-DESSOUS :",
    font=("Arial", 12, "bold"),
    bg="#f4f6f9",
    fg="#2c3e50",
)
label_titre.pack(pady=15)

# Case géante pour coller le texte de la semaine (ScrolledText)
zone_texte = scrolledtext.ScrolledText(
    root, wrap=tk.WORD, width=95, height=22, font=("Courier New", 10), bd=2, relief=tk.SOLID
)
zone_texte.pack(padx=20, pady=5)

# Instructions rapides d'utilisation pour le secrétariat
label_aide = tk.Label(
    root,
    text="Astuce : Faites un CTRL+A puis CTRL+C dans votre fichier d'origine, puis CTRL+V dans la case ci-dessus.",
    font=("Arial", 9, "italic"),
    bg="#f4f6f9",
    fg="#7f8c8d",
)
label_aide.pack(pady=5)

# Bouton d'action principal pour lancer la génération
bouton_generer = tk.Button(
    root,
    text="⚙️ ANALYSER & GÉNÉRER LE FICHIER EXCEL COMPLET",
    font=("Arial", 11, "bold"),
    bg="#27ae60",
    fg="white",
    activebackground="#219653",
    activeforeground="white",
    padx=20,
    pady=10,
    cursor="hand2",
    command=analyser_et_generer,
)
bouton_generer.pack(pady=20)

# Lancement de la boucle de l'interface
root.mainloop()
