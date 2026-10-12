#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mysql.connector
import sys

# Forcer l'affichage en HTML pour le navigateur web
print("Content-Type: text/html; charset=utf-8\n")

# Configuration de votre base MySQL Alwaysdata
config = {
    'host': 'mysql-nadutil.alwaysdata.net',
    'user': 'nadutil',
    'password': 'Nadou73', # Votre mot de passe de connexion
    'database': 'nadutil_db'
}

print("<html><head><title>Suivi Cantine - Nadutil</title></head><body>")
print("<h1>Bienvenue sur Nadutil - Gestion de la Cantine</h1>")

try:
    # Connexion à la base de données
    connexion = mysql.connector.connect(**config)
    cursor = connexion.cursor()
    
    # Création automatique d'une table d'exemple pour tester
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS eleves (
        id INT AUTO_INCREMENT PRIMARY KEY,
        classe VARCHAR(50),
        nom VARCHAR(100),
        prenom VARCHAR(100),
        regime VARCHAR(10)
    );
    """)
    
    print("<p style='color: green;'>🟢 Connexion réussie à la base MySQL Alwaysdata !</p>")
    print("<p>La table 'eleves' est prête à recevoir les données.</p>")
    
    cursor.close()
    connexion.close()

except mysql.connector.Error as err:
    print(f"<p style='color: red;'>🔴 Erreur de connexion : {err}</p>")

print("</body></html>")
