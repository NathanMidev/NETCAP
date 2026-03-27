"""
Regroupe tous les endpoints liés aux sessions utilisateurs.
Monté sur le préfixe /sessions dans api/main.py.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import config
from api.schemas import SessionActive, SessionDetail
from shared.state import lister_sessions_actives, revoquer_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


async def _verifier_token_admin(request: Request) -> str:
    """Vérifie le token admin dans les headers. Lève HTTP 401 si invalide."""
    token = request.headers.get(config.ADMIN_TOKEN_HEADER)
    if not token or token != config.ADMIN_TOKEN_SECRET:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token admin invalide. Header requis : {config.ADMIN_TOKEN_HEADER}",
        )
    return token


@router.get(
    "",
    response_model=list[SessionActive],
    summary="Lister les sessions actives",
    description="Retourne toutes les sessions en cours avec leurs métriques.",
)
async def lister_sessions() -> list[SessionActive]:
    """Retourne un snapshot thread-safe des sessions actives."""
    return lister_sessions_actives()


@router.get(
    "/{session_id}",
    response_model=SessionDetail,
    summary="Détail d'une session",
    description="Retourne les métadonnées complètes et les 50 dernières requêtes.",
)
async def detail_session(session_id: str) -> SessionDetail:
    """404 si la session est introuvable ou expirée."""
    sessions = lister_sessions_actives()
    session = next((s for s in sessions if s.session_id == session_id), None)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' introuvable ou expirée.",
        )
    return SessionDetail(**session.model_dump())


@router.delete(
    "/{session_id}",
    summary="Forcer la déconnexion d'un utilisateur",
    description="Révoque une session active. Requiert le token admin.",
    dependencies=[Depends(_verifier_token_admin)],
)
async def deconnecter_session(session_id: str) -> dict:
    """
    Révoque la session. La prochaine requête du client sera redirigée vers le portail.
    """
    sessions = lister_sessions_actives()
    session = next((s for s in sessions if s.session_id == session_id), None)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' introuvable.",
        )
    succes = revoquer_session(session.ip_client, raison="déconnexion forcée par admin")
    if not succes:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec de la révocation de session.",
        )
    logger.info("Session révoquée par admin — session_id=%s ip=%s", session_id, session.ip_client)
    return {
        "message": f"Session {session_id} révoquée avec succès.",
        "ip": session.ip_client,
        "user_id": session.user_id,
    }