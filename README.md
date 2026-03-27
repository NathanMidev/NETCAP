# NetCapt — Portail Captif & Analyse Comportementale

> Projet dirigé — Cours Python INFO3 — IFT Mahajanga  
> Durée : 5 semaines | Équipe : 5 étudiants | Niveau : 3ème année

---

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Architecture du système](#architecture-du-système)
3. [Installation](#installation)
4. [Démarrage des composants](#démarrage-des-composants)
5. [Structure du projet](#structure-du-projet)
6. [Progression par sprint](#progression-par-sprint)
7. [Guide de développement](#guide-de-développement)
8. [Tests](#tests)
9. [Cadre légal et éthique](#cadre-légal-et-éthique)

---

## Vue d'ensemble

NetCapt est un portail captif éducatif simulant le fonctionnement des systèmes
déployés dans les hôtels, universités et espaces publics. Il intercepte le trafic HTTP,
authentifie les utilisateurs, analyse leurs comportements de navigation et expose
les métriques via une API REST et un dashboard temps réel.

**⚠️ Ce système fonctionne EXCLUSIVEMENT sur un réseau local isolé (localhost / machines virtuelles).**

---

## Architecture du système

```
Client (navigateur configuré proxy:8080)
         │
         ▼
┌─────────────────────┐
│  Proxy HTTP (8080)  │  ← Gardien : intercepte et redirige
│  proxy/proxy_server │
└─────────┬───────────┘
          │ Non authentifié → HTTP 302
          ▼
┌─────────────────────┐
│  Portail Flask(5000)│  ← Authentification + consentement RGPD
│  portail/app.py     │
└─────────┬───────────┘
          │ Token de session → IP autorisée
          │
          ▼ (requêtes authentifiées)
    Queue partagée
          │
          ▼
┌─────────────────────┐
│  Pipeline Pandas    │  ← Analyse comportementale en continu
│  analyse/pipeline   │
└─────────┬───────────┘
          │ Métriques agrégées
          ▼
┌─────────────────────┐     ┌──────────────────────────┐
│  API FastAPI (8000) │────▶│  Dashboard Tkinter       │
│  api/main.py        │     │  dashboard/dashboard.py  │
└─────────────────────┘     └──────────────────────────┘
```

### Flux d'une connexion

1. Le client configure son navigateur → proxy `127.0.0.1:8080`
2. Le proxy reçoit la requête HTTP et vérifie la session
3. **Sans session** → redirection `HTTP 302` vers `http://127.0.0.1:5000/portail?redirect_url=...`
4. L'utilisateur remplit le formulaire et accepte les CGU (RGPD)
5. Flask valide, crée un token UUID et notifie le proxy
6. Les requêtes suivantes sont relayées vers Internet et loguées dans la Queue
7. Le pipeline consomme la Queue → DataFrame Pandas → métriques calculées
8. FastAPI expose les métriques → Dashboard Tkinter les affiche toutes les 5 secondes

---

## Installation

### Prérequis

- Python **3.11+** (vérifier : `python --version`)
- pip à jour : `pip install --upgrade pip`
- tkinter inclus avec Python (vérifier : `python -c "import tkinter"`)

### Installation des dépendances

```bash
# Cloner le projet
git clone <url-du-repo>
cd netcapt

# (Recommandé) Créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate           # Windows

# Installer les dépendances
pip install -r requirements.txt
```

### Vérification de l'installation

```bash
python -c "import fastapi, pydantic, flask, pandas, numpy, matplotlib; print('OK')"
```

---

## Démarrage des composants

**L'ordre de démarrage est obligatoire** (chaque composant dépend du précédent).

Ouvrir **6 terminaux** dans le répertoire `netcapt/` :

```bash
# Terminal 1 — Pipeline d'analyse (doit démarrer avant l'API)
python analyse/pipeline.py

# Terminal 2 — API FastAPI
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 3 — Portail Flask
python portail/app.py

# Terminal 4 — Proxy HTTP
python proxy/proxy_server.py

# Terminal 5 — Dashboard Tkinter
python dashboard/dashboard.py

# Terminal 6 — (optionnel) Vérification via curl
curl http://127.0.0.1:8000/health
```

### Configuration du navigateur client

- **Firefox** : Paramètres → Réseau → Paramètres de connexion → Proxy HTTP manuel
- **Chrome** : Lancer avec `--proxy-server="http://127.0.0.1:8080"`
- **curl** : `curl --proxy http://127.0.0.1:8080 http://example.com`

---

## Structure du projet

```
netcapt/
├── proxy/
│   ├── proxy_server.py        # Serveur TCP principal (Sprint 2)
│   ├── session_manager.py     # Gestion des sessions et tokens (Sprint 2)
│   └── http_parser.py         # Parsing des en-têtes HTTP (Sprint 2)
├── portail/
│   ├── app.py                 # Application Flask (Sprint 3)
│   └── templates/             # Pages HTML : login, CGU, logout (Sprint 3)
├── analyse/
│   ├── pipeline.py            # Thread consommateur + DataFrame (Sprint 3)
│   ├── categoriseur.py        # Dictionnaire et logique de catégorisation (Sprint 3)
│   └── detecteur_anomalies.py # Calculs Z-score NumPy (Sprint 4)
├── api/
│   ├── main.py                # Application FastAPI ✅ Sprint 1
│   ├── schemas.py             # Modèles Pydantic ✅ Sprint 1
│   └── routers/               # sessions.py, analytics.py, config.py (Sprint 4)
├── dashboard/
│   ├── dashboard.py           # Application Tkinter (Sprint 5)
│   └── widgets/               # Composants Tkinter réutilisables (Sprint 5)
├── shared/
│   └── state.py               # Structures partagées thread-safe ✅ Sprint 1
├── tests/
│   └── test_sprint1.py        # Tests unitaires Sprint 1 ✅ Sprint 1
├── config.py                  # Configuration centrale ✅ Sprint 1
├── requirements.txt           # Dépendances Python ✅ Sprint 1
└── README.md                  # Ce fichier ✅ Sprint 1
```

---

## Progression par sprint

| Sprint | Semaine | Objectif | Statut |
|--------|---------|----------|--------|
| **Sprint 1** | Sem. 1 | Fondations : `config.py`, `schemas.py`, `shared/state.py`, structure FastAPI, tests | ✅ **Terminé** |
| Sprint 2 | Sem. 2 | Proxy TCP, parsing HTTP, gestion sessions, redirection 302 | 🔲 À faire |
| Sprint 3 | Sem. 3 | Portail Flask RGPD, pipeline Pandas, catégorisation | 🔲 À faire |
| Sprint 4 | Sem. 4 | Endpoints FastAPI complets, Z-score NumPy, métriques | 🔲 À faire |
| Sprint 5 | Sem. 5 | Dashboard Tkinter, Matplotlib, intégration complète | 🔲 À faire |

---

## Guide de développement

### Conventions de code

```python
# ✅ BON — Docstring sur chaque module
"""
proxy/proxy_server.py — Proxy HTTP intercepteur de NetCapt
Écoute sur le port 8080, gère les connexions clients en parallèle.
"""

# ✅ BON — Constantes depuis config.py
from config import PROXY_PORT, PROXY_BUFFER_SIZE_BYTES

# ❌ MAUVAIS — Valeurs magiques
sock.listen(50)           # Qu'est-ce que 50 ?
time.sleep(30)            # Pourquoi 30 ?

# ✅ BON — Gestion explicite des exceptions
try:
    data = sock.recv(PROXY_BUFFER_SIZE_BYTES)
except ConnectionResetError:
    logger.info("Client %s a fermé la connexion", ip_client)
except OSError as e:
    logger.error("Erreur socket client %s : %s", ip_client, e)

# ❌ MAUVAIS — Crash silencieux
try:
    data = sock.recv(65536)
except:
    pass
```

### Thread-safety — Règle absolue

```python
# ✅ TOUJOURS utiliser le verrou pour accéder aux sessions
from shared.state import sessions_actives, sessions_lock

with sessions_lock:
    session = sessions_actives.get(ip_client)

# ❌ JAMAIS accéder directement sans verrou depuis un thread
session = sessions_actives.get(ip_client)  # Race condition !
```

### Convention de logging

```python
import logging
logger = logging.getLogger(__name__)  # Nom = module courant

logger.debug("Détail interne — %s", variable)      # Développement
logger.info("Événement normal — %s", info)          # Production
logger.warning("Situation anormale — %s", detail)   # Alerte non bloquante
logger.error("Erreur récupérée — %s", exc)          # Erreur gérée
logger.exception("Erreur inattendue")               # Avec stack trace complète
```

### Git — Workflow de l'équipe

```bash
# Une branche par fonctionnalité
git checkout -b feature/sprint2-proxy-tcp

# Commits atomiques et descriptifs
git commit -m "feat(proxy): parsing des en-têtes HTTP GET/POST"
git commit -m "test(proxy): tests unitaires du parseur HTTP"
git commit -m "fix(sessions): correction race condition sur le dictionnaire"

# Minimum 1 commit par fonctionnalité terminée
# Pull request / review avant merge sur main
```

---

## Tests

### Lancer les tests du Sprint 1

```bash
# Depuis le répertoire netcapt/
python -m pytest tests/test_sprint1.py -v

# Avec rapport de couverture (si pytest-cov installé)
python -m pytest tests/test_sprint1.py -v --tb=short

# Un test spécifique
python -m pytest tests/test_sprint1.py::TestFormulaireAuthentification::test_cgu_non_acceptees_rejetees -v
```

### Résultat attendu Sprint 1

```
tests/test_sprint1.py::TestConfig::test_ports_dans_plage_valide PASSED
tests/test_sprint1.py::TestConfig::test_ports_differents PASSED
...
tests/test_sprint1.py::TestSharedState::test_ajouter_et_obtenir_session PASSED
...
========================= XX passed in X.XXs =========================
```

### Vérification de l'API (Sprint 1)

```bash
# Démarrer l'API
uvicorn api.main:app --host 127.0.0.1 --port 8000

# Dans un autre terminal
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/docs  # Interface Swagger auto-générée
curl http://127.0.0.1:8000/config/seuils

# Test de l'authentification admin
curl -X POST http://127.0.0.1:8000/config/seuils \
  -H "Content-Type: application/json" \
  -H "X-Admin-Token: netcapt-admin-secret-changeme" \
  -d '{"zscore_seuil": 2.5, "volume_max_session_mb": 200, "duree_session_max_min": 60, "categories_bloquees": [], "requetes_par_minute_max": 200}'
```

---

## Cadre légal et éthique

> **Point obligatoire — compris et respecté par toute l'équipe**

### Contraintes strictes du projet

| Règle | Détail |
|-------|--------|
| **Consentement explicite** | Recueilli AVANT toute collecte, via la case CGU du formulaire |
| **Réseau isolé uniquement** | `localhost` ou machines virtuelles — jamais un réseau réel |
| **Métadonnées uniquement** | Domaine, volume, horodatage — JAMAIS le contenu des communications |
| **HTTPS respecté** | Les tunnels CONNECT ne sont pas déchiffrés |
| **Durée de rétention** | 30 jours maximum (configurable dans `config.py`) |
| **Pseudonymisation** | Les emails sont hachés SHA-256 avant stockage |

### Sanction

> Tout déploiement hors réseau local isolé, ou toute collecte de données réelles sans consentement,
> **entraîne l'annulation de la note du projet**, indépendamment de la qualité technique.

---

*Bonne conception et bon développement ! Ce projet vous prépare directement aux missions qui vous attendent en entreprise.*