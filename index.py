#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Forcer l'affichage en HTML pour le navigateur
print("Content-Type: text/html; charset=utf-8")
print()

print("""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Suivi Cantine - Nadutil</title>
    <style>
        body { font-family: Arial, sans-serif; background-color: #f4f6f9; color: #2c3e50; text-align: center; padding: 50px; }
        .card { background: white; padding: 30px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); display: inline-block; max-width: 600px; }
        h1 { color: #e85693; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Bienvenue sur Nadutil</h1>
        <h3>Gestion de la Restauration Scolaire</h3>
        <p style='color: green;'>🟢 Le serveur Python CGI fonctionne parfaitement !</p>
    </div>
</body>
</html>
""")
