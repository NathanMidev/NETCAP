"""
Regroupe tous les endpoints analytiques.
Monté sur le préfixe /analytics dans api/main.py.

Sprint 1 : structure et documentation complète.
Sprint 4 : implémentation des calculs Pandas/NumPy.
"""

from __future__ import annotations

import logging
from datetime import datetime

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from api.schemas import (
    AlerteAnomalie,
    MetriqueTrafic,
    PeriodeAnalyse,
    StatUtilisateur,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["Analytique"])


@router.get(
    "/trafic",
    response_model=MetriqueTrafic,
    summary="Métriques agrégées du trafic",
    description=(
        "Retourne les métriques de navigation pour la période demandée : "
        "top domaines, répartition par catégorie, activité horaire, taux d'erreur."
    ),
)
async def analytics_trafic(
    periode: PeriodeAnalyse = Query(
        default=PeriodeAnalyse.UNE_HEURE,
        description="Fenêtre temporelle : 5m | 1h | 4h | 24h",
    ),
    format: str = Query(
        default="json",
        pattern="^(json|csv)$",
        description="Format de retour : json ou csv",
    ),
) -> MetriqueTrafic:
    """
    Sprint 4 : alimenté par le DataFrame Pandas du pipeline d'analyse.
    Sprint 1 : retourne une structure vide correctement typée.
    """
    now = datetime.utcnow()
    # TODO Sprint 4 : appeler pipeline.calculer_metriques(periode)
    return MetriqueTrafic(
        periode=periode,
        debut_periode=now,
        fin_periode=now,
        total_requetes=0,
        total_bytes=0,
        requetes_par_minute=0.0,
        taux_erreur_pct=0.0,
        top_domaines=[],
        repartition_categories={},
        utilisateurs_actifs=0,
    )


@router.get(
    "/utilisateurs",
    response_model=list[StatUtilisateur],
    summary="Statistiques par utilisateur",
    description=(
        "Retourne les métriques de navigation par utilisateur. "
        "Les données sont pseudonymisées par défaut (user_id = hash SHA-256)."
    ),
)
async def analytics_utilisateurs(
    anonymise: bool = Query(
        default=True,
        description="Si True, retourne uniquement les user_id pseudonymisés",
    ),
) -> list[StatUtilisateur]:
    """
    Sprint 4 : agrégation depuis le DataFrame Pandas par user_id.
    Sprint 1 : stub — retourne liste vide.
    """
    # TODO Sprint 4 : appeler pipeline.stats_par_utilisateur()
    return []


@router.get(
    "/anomalies",
    response_model=list[AlerteAnomalie],
    summary="Anomalies comportementales détectées",
    description=(
        "Retourne les utilisateurs dont le score Z-score dépasse le seuil configuré. "
        "Calculé par NumPy sur le volume de trafic de la session en cours."
    ),
)
async def analytics_anomalies(
    non_acquittees: bool = Query(
        default=False,
        description="Si True, retourne uniquement les alertes non encore acquittées",
    ),
) -> list[AlerteAnomalie]:
    """
    Sprint 4 : détection via detecteur_anomalies.py (Z-score NumPy).
    Sprint 1 : stub — retourne liste vide.
    """
    # TODO Sprint 4 : appeler detecteur.lister_anomalies(non_acquittees)
    return []


@router.get(
    "/tendances",
    summary="Évolution du trafic sur les dernières heures",
    description=(
        "Retourne la courbe de volume de trafic, les pics de connexions "
        "et les catégories dominantes par tranche horaire."
    ),
)
async def analytics_tendances(
    heures: int = Query(
        default=4,
        ge=1,
        le=24,
        description="Nombre d'heures d'historique à retourner",
    ),
) -> dict:
    """
    Sprint 4 : calculé depuis le DataFrame avec fenêtre glissante.
    Sprint 1 : stub — retourne structure vide.
    """
    # TODO Sprint 4 : appeler pipeline.calculer_tendances(heures)
    return {
        "heures_demandees": heures,
        "tranches": [],
        "pic_connexions": None,
        "categories_dominantes": {},
        "message": "Disponible au Sprint 4.",
    }


@router.get(
    "/alertes/{alerte_id}/acquitter",
    summary="Acquitter une alerte",
    description="Marque une alerte comme traitée par un administrateur.",
)
async def acquitter_alerte_endpoint(alerte_id: str) -> dict:
    """Acquitte une alerte par son UUID."""
    from shared.state import acquitter_alerte
    succes = acquitter_alerte(alerte_id)
    if not succes:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alerte '{alerte_id}' introuvable.",
        )
    return {"message": f"Alerte {alerte_id} acquittée.", "alerte_id": alerte_id}