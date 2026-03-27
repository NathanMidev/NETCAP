"""
shared/state.py
Point central de synchronisation entre le proxy, le portail Flask,
le pipeline d'analyse et l'API FastAPI.

RÈGLE DE SÉCURITÉ : toute lecture ou écriture sur sessions_actives
doit se faire dans un bloc `with sessions_lock:`. Ne jamais accéder
au dictionnaire directement depuis un thread sans verrou.

Usage :
    from shared.state import sessions_actives, sessions_lock, events_queue
"""

from __future__ import annotations

import logging
import time
from queue import Queue, Full, Empty
from threading import Lock, RLock
from typing import TYPE_CHECKING, Optional, Dict, List, Any
from datetime import datetime

from config import config

if TYPE_CHECKING:
    from api.schemas import SessionData

logger = logging.getLogger(__name__)

# ===========================================================================
# SESSIONS — Dictionnaire partagé proxy ↔ portail ↔ API
# ===========================================================================

# Structure : { ip_client (str) → dict }
# Accès concurrent depuis : proxy (lecture), portail (écriture), API (lecture/écriture)
sessions_actives: Dict[str, dict] = {}

# Verrou réentrant : permet à un même thread d'acquérir plusieurs fois le verrou
# sans deadlock (ex : nettoyage depuis le thread admin qui lit aussi les sessions)
sessions_lock: RLock = RLock()

# ===========================================================================
# QUEUE D'ÉVÉNEMENTS — Proxy → Pipeline d'analyse
# ===========================================================================

# Le proxy pose les événements bruts ici ; le thread consommateur les consomme.
# max_size empêche la consommation mémoire infinie si le pipeline est lent.
# Si la queue est pleine, proxy.put(block=False) lève queue.Full → log + drop.
events_queue: Queue = Queue(maxsize=config.QUEUE_MAX_SIZE)

# ===========================================================================
# ALERTES — Pipeline → Dashboard/API
# ===========================================================================

# Liste des alertes détectées. Protégée par son propre verrou.
alertes: List[dict] = []
alertes_lock: Lock = Lock()

# ===========================================================================
# MÉTRIQUES SYSTÈME — État global du système
# ===========================================================================

_start_time: float = time.monotonic()
_total_requests: int = 0
_total_bytes: int = 0
_stats_lock: Lock = Lock()


def get_uptime_secondes() -> float:
    """Retourne le temps écoulé depuis le démarrage du module (secondes)."""
    return time.monotonic() - _start_time


def get_uptime_formatted() -> str:
    """Retourne le temps écoulé formaté (HH:MM:SS)."""
    seconds = int(get_uptime_secondes())
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


# ===========================================================================
# HELPERS THREAD-SAFE
# ===========================================================================


def ajouter_session(session_data: dict) -> None:
    """
    Enregistre une nouvelle session dans le dictionnaire partagé.

    Args:
        session_data: Dictionnaire contenant les données de session
                      (token, user_id, user_name, expires_at, ip_client, etc.)

    Thread-safe : utilise sessions_lock.
    """
    ip_client = session_data.get('ip_client')
    if not ip_client:
        logger.error("Impossible d'ajouter une session sans ip_client")
        return

    with sessions_lock:
        sessions_actives[ip_client] = session_data
        logger.info(
            "✅ Session créée — IP=%s user=%s token=%s",
            ip_client,
            session_data.get('user_id', '?'),
            session_data.get('token', '?')[:8],
        )


def obtenir_session(ip_client: str) -> Optional[dict]:
    """
    Retourne la session active pour une IP donnée, ou None si inexistante.

    Args:
        ip_client: Adresse IP du client.

    Returns:
        Dictionnaire de session ou None.

    Thread-safe : utilise sessions_lock.
    """
    with sessions_lock:
        return sessions_actives.get(ip_client)


def revoquer_session(ip_client: str, raison: str = "révocation manuelle") -> bool:
    """
    Invalide la session d'une IP. Retourne True si une session existait.

    Args:
        ip_client: IP dont la session doit être révoquée.
        raison: Motif de révocation (pour les logs).

    Returns:
        True si la session existait et a été supprimée, False sinon.

    Thread-safe : utilise sessions_lock.
    """
    with sessions_lock:
        session = sessions_actives.pop(ip_client, None)
        if session:
            logger.info(
                "🔒 Session révoquée — IP=%s user=%s raison=%s",
                ip_client,
                session.get('user_id', '?'),
                raison,
            )
            return True
        logger.debug("Tentative de révocation — IP=%s : aucune session trouvée", ip_client)
        return False


def session_est_valide(ip_client: str) -> bool:
    """
    Vérifie si une IP possède une session active et non expirée.

    Args:
        ip_client: Adresse IP à vérifier.

    Returns:
        True si la session existe et n'est pas expirée.

    Thread-safe : utilise sessions_lock.
    """
    from datetime import datetime

    with sessions_lock:
        session = sessions_actives.get(ip_client)
        if session is None:
            return False

        expires_at = session.get('expires_at')
        if expires_at:
            # Support des strings ISO et des objets datetime
            if isinstance(expires_at, str):
                try:
                    expires_at = datetime.fromisoformat(expires_at)
                except ValueError:
                    return False
            if expires_at < datetime.now():
                # Nettoyage paresseux (lazy cleanup)
                sessions_actives.pop(ip_client, None)
                logger.debug("Session expirée nettoyée (lazy) — IP=%s", ip_client)
                return False
        return True


def lister_sessions_actives() -> List[dict]:
    """
    Retourne une copie de la liste des sessions non expirées.

    Returns:
        Liste de dictionnaires de session (snapshot thread-safe).

    Thread-safe : utilise sessions_lock.
    """
    from datetime import datetime

    now = datetime.now()
    with sessions_lock:
        sessions_valides = [
            s for s in sessions_actives.values()
            if not (s.get('expires_at') and
                    (isinstance(s['expires_at'], str) and
                     datetime.fromisoformat(s['expires_at']) < now) or
                    (isinstance(s['expires_at'], datetime) and s['expires_at'] < now))
        ]
    return sessions_valides


def purger_sessions_expirees() -> int:
    """
    Supprime toutes les sessions dont la date d'expiration est dépassée.
    Appelée périodiquement par le thread de surveillance du proxy.

    Returns:
        Nombre de sessions supprimées.

    Thread-safe : utilise sessions_lock.
    """
    from datetime import datetime

    now = datetime.now()
    ips_expirees = []

    with sessions_lock:
        for ip, session in sessions_actives.items():
            expires_at = session.get('expires_at')
            if expires_at:
                if isinstance(expires_at, str):
                    try:
                        expires_at = datetime.fromisoformat(expires_at)
                    except ValueError:
                        continue
                if expires_at < now:
                    ips_expirees.append(ip)

        for ip in ips_expirees:
            del sessions_actives[ip]

    if ips_expirees:
        logger.info(
            "🧹 Purge des sessions expirées — %d session(s) supprimée(s)",
            len(ips_expirees),
        )
    return len(ips_expirees)


# ===========================================================================
# HELPERS POUR LA FILE D'ÉVÉNEMENTS
# ===========================================================================


def ajouter_evenement(event: dict) -> bool:
    """
    Ajoute un événement dans la queue (non-bloquant).

    Args:
        event: Dictionnaire représentant l'événement de navigation

    Returns:
        True si ajouté, False si queue pleine

    Thread-safe : Queue native.
    """
    if 'timestamp' not in event:
        event['timestamp'] = datetime.now().isoformat()

    try:
        events_queue.put_nowait(event)
        # Mise à jour des statistiques
        with _stats_lock:
            global _total_requests, _total_bytes
            _total_requests += 1
            _total_bytes += event.get('size_bytes', 0)
        return True
    except Full:
        logger.warning("⚠️ Queue pleine, événement perdu")
        return False


def obtenir_evenement(timeout: float = 0.1) -> Optional[dict]:
    """
    Récupère un événement de la queue (bloquant avec timeout).

    Args:
        timeout: Temps d'attente maximum en secondes

    Returns:
        Événement ou None si timeout
    """
    try:
        return events_queue.get(timeout=timeout)
    except Empty:
        return None


def taille_queue() -> int:
    """Retourne le nombre d'événements en attente."""
    return events_queue.qsize()


# ===========================================================================
# HELPERS POUR LES ALERTES
# ===========================================================================


def ajouter_alerte(alerte: dict) -> None:
    """
    Ajoute une alerte d'anomalie à la liste partagée.

    Args:
        alerte: Dictionnaire représentant l'alerte (sera converti en AnomalyAlert).

    Thread-safe : utilise alertes_lock.
    """
    # Ajout d'un timestamp si absent
    if 'timestamp' not in alerte:
        alerte['timestamp'] = datetime.now().isoformat()

    with alertes_lock:
        alertes.append(alerte)
        logger.warning(
            "⚠️ Alerte anomalie — user=%s zscore=%.2f volume=%.1fMB",
            alerte.get('user_id', '?'),
            alerte.get('score_zscore', 0.0),
            alerte.get('volume_session_mb', 0.0),
        )


def lister_alertes(non_acquittees_seulement: bool = False) -> List[dict]:
    """
    Retourne une copie de la liste des alertes.

    Args:
        non_acquittees_seulement: Si True, filtre les alertes déjà acquittées.

    Returns:
        Liste de dictionnaires d'alerte (snapshot thread-safe).
    """
    with alertes_lock:
        if non_acquittees_seulement:
            return [a for a in alertes if not a.get("acquittee", False)]
        return list(alertes)


def acquitter_alerte(alerte_id: str) -> bool:
    """
    Marque une alerte comme acquittée par un administrateur.

    Args:
        alerte_id: Identifiant UUID de l'alerte.

    Returns:
        True si l'alerte a été trouvée et acquittée.
    """
    with alertes_lock:
        for alerte in alertes:
            if alerte.get("alerte_id") == alerte_id:
                alerte["acquittee"] = True
                alerte["acquittee_date"] = datetime.now().isoformat()
                logger.info("📌 Alerte acquittée — id=%s", alerte_id)
                return True
    return False


# ===========================================================================
# HELPERS STATISTIQUES
# ===========================================================================


def get_stats() -> dict:
    """
    Retourne les statistiques globales du système.

    Returns:
        Dictionnaire avec les métriques système.
    """
    with sessions_lock:
        active_sessions = len(sessions_actives)

    with _stats_lock:
        total_requests = _total_requests
        total_bytes = _total_bytes

    return {
        "active_sessions": active_sessions,
        "queue_size": taille_queue(),
        "total_requests": total_requests,
        "total_bytes": total_bytes,
        "total_bytes_mb": round(total_bytes / (1024 * 1024), 2),
        "uptime_seconds": get_uptime_secondes(),
        "uptime_formatted": get_uptime_formatted(),
        "total_alerts": len(alertes)
    }


def reset_stats() -> None:
    """Réinitialise les statistiques (pour les tests)."""
    with _stats_lock:
        global _total_requests, _total_bytes
        _total_requests = 0
        _total_bytes = 0
    with alertes_lock:
        alertes.clear()


# ===========================================================================
# INITIALISATION
# ===========================================================================

logger.info("🚀 État partagé initialisé — Queue maxsize=%d", config.QUEUE_MAX_SIZE)
