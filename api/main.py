"""
Point d'entrée de l'API d'administration REST.
Monte les routers séparés pour une architecture propre.

Démarrage :
    uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload

Documentation auto-générée :
    http://127.0.0.1:8000/docs   (Swagger UI)
    http://127.0.0.1:8000/redoc  (ReDoc)
"""

from __future__ import annotations

import logging
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import config
from api.schemas import HealthCheck, StatutComposant
from api.routers import sessions, analytics, config_router
from shared.state import events_queue, get_uptime_secondes, lister_sessions_actives

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format=config.LOG_FORMAT,
    datefmt=config.LOG_DATE_FORMAT,
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="NetCapt — API d'administration",
    description=(
        "API REST pour la supervision du portail captif NetCapt.\n\n"
        "**Authentification admin** : ajouter le header `X-Admin-Token: <token>` "
        "sur les endpoints sensibles.\n\n"
        "**Token par défaut (dev)** : `netcapt-admin-secret-changeme`"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "Équipe NetCapt — IFT Mahajanga"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[f"http://{config.API_HOST}", "http://localhost", "http://127.0.0.1"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

app.include_router(sessions.router)
app.include_router(analytics.router)
app.include_router(config_router.router)


@app.exception_handler(Exception)
async def gestionnaire_erreur_global(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Erreur interne non gérée sur %s : %s", request.url, exc)
    return JSONResponse(
        status_code=500,
        content={"erreur": "Erreur interne du serveur", "detail": str(exc)},
    )


@app.get("/", include_in_schema=False)
async def racine() -> dict:
    return {
        "service": "NetCapt API",
        "version": "1.0.0",
        "docs": f"http://{config.API_HOST}:{config.API_PORT}/docs",
        "health": f"http://{config.API_HOST}:{config.API_PORT}/health",
    }


@app.get(
    "/health",
    response_model=HealthCheck,
    summary="Statut global du système",
    description="Vérifie la disponibilité de chaque composant et retourne un bilan global.",
    tags=["Système"],
)
async def health_check() -> HealthCheck:
    import socket, time

    def _tester_port(host: str, port: int) -> tuple[bool, float]:
        debut = time.monotonic()
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True, round((time.monotonic() - debut) * 1000, 2)
        except (ConnectionRefusedError, OSError, TimeoutError):
            return False, 0.0

    actif_proxy, lat_proxy = _tester_port(config.PROXY_HOST, config.PROXY_PORT)
    actif_flask, lat_flask = _tester_port(config.PORTAIL_HOST, config.PORTAIL_PORT)

    composants = [
        StatutComposant(nom="Proxy HTTP", actif=actif_proxy, port=config.PROXY_PORT,
                        latence_ms=lat_proxy if actif_proxy else None),
        StatutComposant(nom="Portail Flask", actif=actif_flask, port=config.PORTAIL_PORT,
                        latence_ms=lat_flask if actif_flask else None),
        StatutComposant(nom="API FastAPI", actif=True, port=config.API_PORT, latence_ms=0.0),
        StatutComposant(nom="Pipeline Analyse", actif=False, port=0),
    ]

    nb_actifs = sum(1 for c in composants if c.actif)
    statut = "ok" if nb_actifs == len(composants) else ("dégradé" if nb_actifs >= 2 else "critique")

    sessions = lister_sessions_actives()
    return HealthCheck(
        statut=statut,
        uptime_secondes=round(get_uptime_secondes(), 1),
        sessions_actives=len(sessions),
        taille_dataframe=0,
        taille_queue=events_queue.qsize(),
        composants=composants,
        timestamp=datetime.utcnow(),
    )


if __name__ == "__main__":
    import uvicorn
    logger.info("Démarrage API NetCapt — http://%s:%d/docs", config.API_HOST, config.API_PORT)
    uvicorn.run("api.main:app", host=config.API_HOST, port=config.API_PORT, reload=False)