from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Dict


class SessionActive(BaseModel):
    """
    Représente une session active dans le système.
    """
    ip_client: str
    user_id: str
    session_id: str
    debut: datetime
    expiration: datetime
    nb_requetes: int
    volume_bytes: int
    categorie_dominante: str


class EvenementNavigation(BaseModel):
    """
    Représente un événement de navigation capturé par le proxy.
    """
    timestamp: datetime
    ip_client: str
    user_id: str
    session_id: str
    methode: str
    domaine: str
    categorie: str
    taille_bytes: int
    duree_ms: int
    statut_http: int
    est_https: bool


class MetriqueTrafic(BaseModel):
    """
    Contient les métriques globales de trafic.
    """
    periode: str
    total_requetes: int
    total_bytes: int
    top_domaines: List[str]
    repartition_categories: Dict[str, int]


class AlerteAnomalie(BaseModel):
    """
    Représente une alerte générée lors d'un comportement anormal.
    """
    user_id: str
    score_zscore: float
    volume_session: int
    volume_moyen_groupe: float
    timestamp_detection: datetime
    details: str


class ConfigSeuils(BaseModel):
    """
    Configuration dynamique des seuils du système.
    """
    zscore_seuil: float
    volume_max_session_mb: int
    duree_session_max_min: int
    categories_bloquees: List[str]