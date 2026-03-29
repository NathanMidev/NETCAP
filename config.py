

"""
Fichier de configuration global du projet NetCapt.
Toutes les constantes du système doivent être définies ici.
Cela permet d'éviter les valeurs en dur dans le code.
"""

# Ports des différents services
PROXY_PORT = 8080
FLASK_PORT = 5000
FASTAPI_PORT = 8000

# Durée de vie des sessions utilisateur (en minutes)
SESSION_DURATION_MIN = 30

# Taille de la fenêtre d'analyse (en heures)
WINDOW_SIZE_HOURS = 4

# Seuil de détection d'anomalie (Z-score)
ZSCORE_THRESHOLD = 3.0

# Volume maximum autorisé par session (en MB)
MAX_VOLUME_MB = 100

# Intervalle de rafraîchissement du dashboard (ms)
REFRESH_INTERVAL_MS = 5000