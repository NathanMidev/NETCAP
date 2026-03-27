"""
Endpoints de lecture et modification de la configuration en temps réel.
Monté sur le préfixe /config dans api/main.py.

Tous les endpoints de modification nécessitent le token admin.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config
from api.schemas import ConfigSeuils, ParametresExport

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["Configuration"])

# État mutable de la configuration — partagé avec main.py via import
# Initialisé avec les valeurs de config.py
_config_courante = ConfigSeuils(
    zscore_seuil=config.ANOMALIE_ZSCORE_SEUIL,
    volume_max_session_mb=config.ANOMALIE_VOLUME_MAX_SESSION_MB,
    duree_session_max_min=config.ANOMALIE_DUREE_SESSION_MAX_MIN,
    categories_bloquees=list(config.CATEGORIES_BLOQUEES),
    requetes_par_minute_max=config.ANOMALIE_REQUETES_PAR_MINUTE_MAX,
)


async def _verifier_token_admin(request: Request) -> str:
    """Dépendance : vérifie le token admin dans les headers."""
    token = request.headers.get(config.ADMIN_TOKEN_HEADER)
    if not token or token != config.ADMIN_TOKEN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token admin invalide. Header requis : {config.ADMIN_TOKEN_HEADER}",
        )
    return token


def get_config_courante() -> ConfigSeuils:
    """Retourne la configuration actuellement active. Utilisable comme dépendance."""
    return _config_courante


@router.get(
    "/seuils",
    response_model=ConfigSeuils,
    summary="Lire la configuration courante",
    description="Retourne les seuils d'alerte et paramètres actuellement actifs.",
)
async def lire_seuils() -> ConfigSeuils:
    """Retourne la configuration en mémoire, initialisée depuis config.py."""
    return _config_courante


@router.post(
    "/seuils",
    response_model=ConfigSeuils,
    summary="Mettre à jour les seuils d'alerte",
    description=(
        "Modifie les seuils de détection d'anomalies en temps réel. "
        "Les modifications prennent effet immédiatement. Requiert le token admin."
    ),
    dependencies=[Depends(_verifier_token_admin)],
)
async def mettre_a_jour_seuils(nouveaux_seuils: ConfigSeuils) -> ConfigSeuils:
    """
    Met à jour la configuration en mémoire. Pas de persistance disque (Sprint 1).
    Sprint 4 : sauvegarder dans un fichier JSON pour survie au redémarrage.
    """
    global _config_courante
    _config_courante = nouveaux_seuils
    logger.info(
        "Seuils mis à jour par admin — zscore=%.1f volume_max=%dMo durée_max=%dmin",
        nouveaux_seuils.zscore_seuil,
        nouveaux_seuils.volume_max_session_mb,
        nouveaux_seuils.duree_session_max_min,
    )
    return _config_courante


@router.get(
    "/export/csv",
    summary="Exporter les données en CSV",
    description=(
        "Exporte les événements de navigation de la période demandée au format CSV. "
        "Paramètres : debut (ISO datetime), fin (ISO datetime), colonnes (liste séparée par virgules)."
    ),
)
async def export_csv(
    debut: str | None = None,
    fin: str | None = None,
    colonnes: str | None = None,
) -> dict:
    """
    Sprint 4 : génération du CSV depuis le DataFrame Pandas.
    Sprint 1 : stub documenté.
    """
    # TODO Sprint 4 : pipeline.exporter_csv(debut, fin, colonnes)
    return {
        "message": "Export CSV disponible au Sprint 4.",
        "parametres_recus": {
            "debut": debut,
            "fin": fin,
            "colonnes": colonnes.split(",") if colonnes else None,
        },
    }