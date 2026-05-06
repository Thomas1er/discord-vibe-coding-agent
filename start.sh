#!/bin/bash
# Script de lancement automatique pour Vibe Pilot

# On récupère le dossier où se trouve le script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "🚀 Lancement de Vibe Pilot..."

# On utilise directement le python de l'environnement virtuel s'il existe
if [ -d "venv" ]; then
    ./venv/bin/python3 vibe_pilot.py
else
    # Sinon on tente avec python3 classique
    python3 vibe_pilot.py
fi
