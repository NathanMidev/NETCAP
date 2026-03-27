"""
api/schemas.py
Modèles Pydantic pour l'API NetCapt.

Ces modèles définissent la structure des données échangées entre les composants.
Tous les échanges sont validés automatiquement par Pydantic.

Auteur: Équipe NetCapt
Date: Sprint 1 - Mars 2026
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional
from datetime import datetime
from uuid import uuid4
import re


# ============================================================================
# MODÈLES POUR LES SESSIONS
# ============================================================================

class SessionActive(BaseModel):
    """
    Session active d'un utilisateur authentifié.
    Stockée dans shared.state.sessions_actives.
    """
    ip_client: str = Field(..., description="Adresse IP du client")
    user_id: str = Field(..., description="Identifiant unique de l'utilisateur (email)")
    session_id: str = Field(default_factory=lambda: str(uuid4()), description="UUID de session")
    debut: datetime = Field(default_factory=datetime.now, description="Début de la session")
    expiration: datetime = Field(..., description="Date d'expiration de la session")
    nb_requetes: int = Field(0, ge=0, description="Nombre de requêtes effectuées")
    volume_bytes: int = Field(0, ge=0, description="Volume total en octets")
    categorie_dominante: Optional[str] = Field(None, description="Catégorie la plus visitée")

    @property
    def est_expiree(self) -> bool:
        """Vérifie si la session a expiré."""
        return datetime.now() > self.expiration

    @property
    def duree_secondes(self) -> int:
        """Durée écoulée depuis le début de la session."""
        return int((datetime.now() - self.debut).total_seconds())

    @property
    def temps_restant_minutes(self) -> int:
        """Temps restant en minutes avant expiration."""
        if self.est_expiree:
            return 0
        return int((self.expiration - datetime.now()).total_seconds() // 60)

    def to_storage_dict(self) -> dict:
        """Convertit l'objet en dictionnaire pour stockage."""
        return {
            "ip_client": self.ip_client,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "debut": self.debut.isoformat(),
            "expiration": self.expiration.isoformat(),
            "nb_requetes": self.nb_requetes,
            "volume_bytes": self.volume_bytes,
            "categorie_dominante": self.categorie_dominante
        }


# ============================================================================
# MODÈLES POUR LES ÉVÉNEMENTS DE NAVIGATION
# ============================================================================

class EvenementNavigation(BaseModel):
    """
    Événement de navigation unique.
    Produit par le proxy, consommé par le pipeline d'analyse.
    """
    timestamp: datetime = Field(default_factory=datetime.now, description="Horodatage précis")
    ip_client: str = Field(..., description="Adresse IP du client")
    user_id: str = Field(..., description="Identifiant de l'utilisateur")
    session_id: str = Field(..., description="Identifiant de la session")
    methode: str = Field(..., description="Méthode HTTP (GET, POST, CONNECT, etc.)")
    domaine: str = Field(..., description="Domaine cible (ex: github.com)")
    url_path: Optional[str] = Field("/", description="Chemin de la ressource")
    categorie: Optional[str] = Field(None, description="Catégorie du domaine")
    taille_bytes: int = Field(0, ge=0, description="Volume en octets")
    duree_ms: int = Field(0, ge=0, description="Temps de réponse en millisecondes")
    statut_http: int = Field(200, ge=100, lt=600, description="Code HTTP")
    est_https: bool = Field(False, description="True si requête HTTPS (méthode CONNECT)")

    @field_validator('domaine', mode='before')
    @classmethod
    def normaliser_domaine(cls, v: str) -> str:
        """Normalise le domaine : minuscules, suppression www."""
        if not v:
            return ""
        v = v.lower().strip()
        if v.startswith('www.'):
            v = v[4:]
        return v

    @field_validator('methode')
    @classmethod
    def valider_methode(cls, v: str) -> str:
        """Valide la méthode HTTP."""
        methodes_valides = {'GET', 'POST', 'PUT', 'DELETE', 'CONNECT', 'HEAD', 'OPTIONS', 'PATCH'}
        v_upper = v.upper()
        if v_upper not in methodes_valides:
            raise ValueError(f"Méthode HTTP invalide: {v}")
        return v_upper


# ============================================================================
# MODÈLES POUR LES MÉTRIQUES DE TRAFIC
# ============================================================================

class MetriqueTrafic(BaseModel):
    """
    Métriques agrégées du trafic pour une période donnée.
    Utilisé par l'API /analytics/traffic.
    """
    periode: str = Field(..., description="Période (5m, 1h, 4h)")
    total_requetes: int = Field(..., ge=0, description="Nombre total de requêtes")
    total_bytes: int = Field(..., ge=0, description="Volume total en octets")
    top_domaines: List[str] = Field(default_factory=list, description="Top 10 domaines")
    repartition_categories: Dict[str, int] = Field(default_factory=dict, description="Répartition par catégorie")

    @property
    def total_bytes_mb(self) -> float:
        """Volume total en mégaoctets."""
        return round(self.total_bytes / (1024 * 1024), 2)


# ============================================================================
# MODÈLES POUR LES ALERTES D'ANOMALIES
# ============================================================================

class AlerteAnomalie(BaseModel):
    """
    Alerte déclenchée lors de la détection d'une anomalie comportementale.
    Utilisé par l'API /analytics/anomalies.
    """
    user_id: str = Field(..., description="Identifiant de l'utilisateur")
    score_zscore: float = Field(..., description="Score Z-score calculé")
    volume_session: int = Field(..., ge=0, description="Volume de la session en octets")
    volume_moyen_groupe: float = Field(..., ge=0, description="Volume moyen du groupe en octets")
    timestamp_detection: datetime = Field(default_factory=datetime.now, description="Date de détection")
    details: str = Field(..., description="Description détaillée de l'anomalie")
    acquittee: bool = Field(False, description="Alerte acquittée par un admin")
    alerte_id: str = Field(default_factory=lambda: str(uuid4()), description="Identifiant unique de l'alerte")

    @property
    def volume_session_mb(self) -> float:
        """Volume de la session en mégaoctets."""
        return round(self.volume_session / (1024 * 1024), 2)

    @property
    def volume_moyen_groupe_mb(self) -> float:
        """Volume moyen du groupe en mégaoctets."""
        return round(self.volume_moyen_groupe / (1024 * 1024), 2)


# ============================================================================
# MODÈLES POUR LA CONFIGURATION DES SEUILS
# ============================================================================

class ConfigSeuils(BaseModel):
    """
    Configuration des seuils d'alerte et de blocage.
    Utilisé par l'API /config/thresholds.
    """
    zscore_seuil: float = Field(3.0, ge=0, le=10, description="Seuil Z-score pour déclencher une alerte")
    volume_max_session_mb: int = Field(100, ge=0, description="Volume max par session en mégaoctets")
    duree_session_max_min: int = Field(30, ge=1, description="Durée max de session en minutes")
    categories_bloquees: List[str] = Field(default_factory=list, description="Catégories de sites à bloquer")

    @field_validator('categories_bloquees')
    @classmethod
    def valider_categories(cls, v: List[str]) -> List[str]:
        """Valide les catégories bloquées."""
        categories_valides = {
            "Réseaux sociaux", "Streaming vidéo", "Streaming audio",
            "Développement", "Actualités", "Moteurs de recherche",
            "Messagerie", "E-commerce", "Éducation", "Autre / Inconnu"
        }
        for cat in v:
            if cat not in categories_valides:
                raise ValueError(f"Catégorie invalide: {cat}")
        return v


# ============================================================================
# MODÈLES POUR LE PORTAIL D'AUTHENTIFICATION
# ============================================================================

class UserRegistration(BaseModel):
    """
    Formulaire d'inscription utilisateur.
    Reçu du portail Flask.
    """
    first_name: str = Field(..., min_length=1, max_length=50, description="Prénom")
    last_name: str = Field(..., min_length=1, max_length=50, description="Nom")
    email: str = Field(..., description="Adresse email")
    accepts_cgu: bool = Field(..., description="Acceptation des CGU (obligatoire)")
    accepts_analytics: bool = Field(False, description="Acceptation de l'analyse (optionnel)")

    @field_validator('email')
    @classmethod
    def valider_email(cls, v: str) -> str:
        """Validation simple de l'email."""
        if '@' not in v or '.' not in v:
            raise ValueError("Email invalide")
        return v.lower()

    @field_validator('accepts_cgu')
    @classmethod
    def must_accept_cgu(cls, v: bool) -> bool:
        """Valide que les CGU sont acceptées."""
        if not v:
            raise ValueError("Vous devez accepter les Conditions Générales d'Utilisation")
        return v

    @property
    def full_name(self) -> str:
        """Nom complet formaté."""
        return f"{self.first_name} {self.last_name}"


# ============================================================================
# MODÈLES POUR LES RÉPONSES API
# ============================================================================

class HealthStatus(BaseModel):
    """
    Statut du système pour l'endpoint /health.
    """
    status: str = Field(..., description="healthy, degraded, unhealthy")
    composants: Dict[str, bool] = Field(..., description="État des composants")
    sessions_actives: int = Field(..., ge=0, description="Nombre de sessions actives")
    taille_dataframe: int = Field(..., ge=0, description="Taille du DataFrame en mémoire")
    taille_queue: int = Field(..., ge=0, description="Nombre d'événements en attente")
    uptime_secondes: float = Field(..., ge=0, description="Temps d'activité en secondes")


class ErrorResponse(BaseModel):
    """
    Réponse d'erreur standardisée pour l'API.
    """
    error: str = Field(..., description="Message d'erreur")
    detail: Optional[str] = Field(None, description="Détails supplémentaires")
    status_code: int = Field(..., description="Code HTTP")
    timestamp: datetime = Field(default_factory=datetime.now, description="Horodatage de l'erreur")


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    'SessionActive',
    'EvenementNavigation',
    'MetriqueTrafic',
    'AlerteAnomalie',
    'ConfigSeuils',
    'UserRegistration',
    'HealthStatus',
    'ErrorResponse',
]
