#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import mysql.connector
from wsgiref.simple_server import make_server

# Configuration de votre base MySQL Alwaysdata
config_db = {
    'host': 'mysql-nadutil.alwaysdata.net',
    'user': 'nadutil',
    'password': 'Nadou73',
    'database': 'nadutil_db'
}

def application(environ, start_response):
    status = '200 OK'
    headers = [('Content-Type', 'text/html; charset=utf-8')]
    start_response(status, headers)
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Suivi Cantine - Nadutil</title>
        <style>
            body { font-family: Arial, sans-serif; background-color: #f4f6f9; color: #2c3e50; text-align: center; padding: 50px; }
            .card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: inline-block; max-width: 600px; }
            h1 { color: #e85693; }
            .status { font-weight: bold; padding: 10px; border-radius: 5px; }
            .success { background-color: #d4edda; color: #155724; }
            .error { background-color: #f8d7da; color: #721c24; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Bienvenue sur Nadutil</h1>
            <h3>Gestion de la Restauration Scolaire</h3>
    """
    
    try:
        # Test de connexion à la base de données
        connexion = mysql.connector.connect(**config_db)
        cursor = connexion.cursor()
        
        # Création automatique de la table de stockage des repas
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS feuilles_semaines (
            id INT AUTO_INCREMENT PRIMARY KEY,
            date_import TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            contenu_brut LONGTEXT
        );
        """)
        
        html += "<p class='status success'>🟢 Connexion réussie à la base MySQL Alwaysdata !</p>"
        html += "<p>La table de stockage des données est opérationnelle.</p>"
        
        cursor.close()
        connexion.close()
        
    except mysql.connector.Error as err:
        html += f"<p class='status error'>🔴 Erreur de connexion MySQL : {err}</p>"
        
    html += """
        </div>
    </body>
    </html>
    """
    return [html.encode('utf-8')]

if __name__ == '__main__':
    # Récupération du port dynamique attribué par Alwaysdata
    port = int(os.environ.get("PORT", 8100))
    server = make_server('0.0.0.0', port, application)
    print(f"Serveur démarré sur le port {port}...")
    server.serve_forever()
