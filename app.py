import io
import pandas as pd
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side


def generer_excel_presence(donnees_brutes):
    # 1. Analyse et découpage du fichier brut
    lignes = donnees_brutes.strip().split("\n")

    titre_principal = "LYCEE COSTA DE BEAUREGARD"
    sous_titre = "SEMAINE N° 41 du 05 septembre au 09 octobre 2026"

    jours_colonnes = [
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

    donnees_propres = []
    classe_actuelle = "Inconnue"

    for ligne in lignes:
        ligne_nettoyee = ligne.strip()
        if not ligne_nettoyee or ligne_nettoyee.startswith(",,,,"):
            continue

        # Détection du changement de section / classe
        if any(
            c in ligne_nettoyee
            for c in [
                "4ème",
                "3ème",
                "CAPA",
                "2DE",
                "BAC PRO",
                "TERM",
                "BTS",
                "Ste ",
                "St ",
                "SECONDES",
                "PREMIERES",
                "TERMINALES",
            ]
        ):
            classe_actuelle = ligne_nettoyee.replace(",", "").strip()
            continue

        # Ignorer les lignes de structure ou de résumé
        if (
            "NOM" in ligne_nettoyee
            or "EFFECTIF" in ligne_nettoyee
            or "INTERNES" in ligne_nettoyee
            or "COSTA" in ligne_nettoyee
        ):
            continue

        elements = [e.strip() for e in ligne_nettoyee.split(",")]

        # Vérification qu'il s'agit d'une ligne d'un élève ou personnel valide
        if len(elements) >= 3 and any(
            r in elements[2] for r in ["D", "P", "D/F", "APP", "Rég"]
        ):
            nom = elements[0]
            prenom = elements[1]
            regime = elements[2]

            # Extraction des notes spécifiques (PN, EXC, ABS) déjà présentes
            repas_existants = elements[3:13]
            while len(repas_existants) < 10:
                repas_existants.append("")

            repas_calcules = []
            for idx, case in enumerate(repas_existants):
                est_midi = idx % 2 == 0

                # Si une note explicite existe, on la conserve précieusement
                if case in ["PN", "EXC", "ABS", "REPAS"]:
                    repas_calcules.append(case)
                # Application de la règle automatique selon le régime de l'élève
                elif "P" in regime:
                    repas_calcules.append(
                        "X"
                    )  # Pensionnaire / Interne mange Midi et Soir
                elif "D" in regime and est_midi:
                    repas_calcules.append(
                        "X"
                    )  # Demi-pensionnaire mange uniquement le Midi
                else:
                    repas_calcules.append("")  # Pas de repas

            # Structuration finale de la ligne
            ligne_eleve = {
                "Classe / Section": classe_actuelle,
                "Nom": nom,
                "Prénom": prenom,
                "Régime": regime,
            }
            for j, jour_label in enumerate(jours_colonnes):
                ligne_eleve[jour_label] = repas_calcules[j]

            donnees_propres.append(ligne_eleve)

    # Convertir en DataFrame Pandas
    df = pd.DataFrame(donnees_propres)

    # 2. Construction et mise en page stylisée de l'Excel avec OpenPyXL
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Suivi Rentrée"
    ws.views.sheetView[0].showGridLines = True

    # Ajout des titres
    ws["A1"] = titre_principal
    ws["A1"].font = Font(name="Arial", size=14, bold=True, color="1F4E78")
    ws.merge_cells("A1:N1")

    ws["A2"] = sous_titre
    ws["A2"].font = Font(name="Arial", size=11, italic=True, color="595959")
    ws.merge_cells("A2:N2")

    # Création de la double ligne d'en-tête (Jours et Repas)
    jours_header = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI"]
    ws.append([])  # Ligne 3 vide de séparation

    # En-têtes fixes
    headers_principaux = ["Classe / Section", "Nom", "Prénom", "Régime"]
    for col_num, header in enumerate(headers_principaux, 1):
        cell = ws.cell(row=4, column=col_num, value=header)
        ws.merge_cells(
            start_row=4, start_column=col_num, end_row=5, end_column=col_num
        )

    # En-têtes dynamiques de jours fusionnés
    current_col = 5
    for jour in jours_header:
        ws.cell(row=4, column=current_col, value=jour)
        ws.merge_cells(
            start_row=4,
            start_column=current_col,
            end_row=4,
            end_column=current_col + 1,
        )
        ws.cell(row=5, column=current_col, value="Midi")
        ws.cell(row=5, column=current_col + 1, value="Soir")
        current_col += 2

    # Style des en-têtes (Lignes 4 et 5)
    fill_header = PatternFill(
        start_color="D9E1F2", end_color="D9E1F2", fill_type="solid"
    )
    font_header = Font(name="Arial", size=10, bold=True, color="000000")
    thin_border = Border(
        left=Side(style="thin", color="A6A6A6"),
        right=Side(style="thin", color="A6A6A6"),
        top=Side(style="thin", color="A6A6A6"),
        bottom=Side(style="thin", color="A6A6A6"),
    )

    for r in:
        for c in range(1, 15):
            cell = ws.cell(row=r, column=c)
            cell.fill = fill_header
            cell.font = font_header
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border

    # 3. Remplissage des lignes d'élèves
    for index, row in df.iterrows():
        row_data = [
            row["Classe / Section"],
            row["Nom"],
            row["Prénom"],
            row["Régime"],
            row["LUNDI_Midi"],
            row["LUNDI_Soir"],
            row["MARDI_Midi"],
            row["MARDI_Soir"],
            row["MERCREDI_Midi"],
            row["MERCREDI_Soir"],
            row["JEUDI_Midi"],
            row["JEUDI_Soir"],
            row["VENDREDI_Midi"],
            row["VENDREDI_Soir"],
        ]
        ws.append(row_data)

        # Appliquer les bordures et centrer les cases de repas
        current_row = ws.max_row
        for c in range(1, 15):
            cell = ws.cell(row=current_row, column=c)
            cell.font = Font(name="Arial", size=10)
            cell.border = thin_border
            if c > 4:
                cell.alignment = Alignment(
                    horizontal="center", vertical="center"
                )
                # Coloration légère des notes spécifiques pour la visibilité
                if cell.value in ["PN", "EXC", "ABS"]:
                    cell.font = Font(name="Arial", size=10, bold=True)

    # Ajustement automatique de la largeur des colonnes pour éviter les coupures de texte
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = openpyxl.utils.get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 3, 10)

    # Sauvegarde du fichier dans un flux de bytes utilisable pour le téléchargement
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output
