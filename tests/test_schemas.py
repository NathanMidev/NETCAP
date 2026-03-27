"""
tests/test_schemas.py
Tests unitaires pour les modèles Pydantic (api/schemas.py).
"""

import pytest
from datetime import datetime, timedelta
from api.schemas import (
    SessionActive, EvenementNavigation, MetriqueTrafic,
    AlerteAnomalie, ConfigSeuils, UserRegistration, HealthStatus
)


class TestSessionActive:
    """Tests pour SessionActive"""

    def test_creation_session(self):
        """Test de création d'une session"""
        session = SessionActive(
            ip_client='192.168.1.1',
            user_id='user@test.com',
            expiration=datetime.now() + timedelta(minutes=30)
        )
        assert session.ip_client == '192.168.1.1'
        assert session.user_id == 'user@test.com'
        assert session.nb_requetes == 0
        assert session.volume_bytes == 0
        assert session.session_id is not None

    def test_est_expiree(self):
        """Test de vérification d'expiration"""
        session_valide = SessionActive(
            ip_client='192.168.1.1',
            user_id='user@test.com',
            expiration=datetime.now() + timedelta(minutes=30)
        )
        assert session_valide.est_expiree is False

        session_expiree = SessionActive(
            ip_client='192.168.1.1',
            user_id='user@test.com',
            expiration=datetime.now() - timedelta(minutes=1)
        )
        assert session_expiree.est_expiree is True

    def test_temps_restant_minutes(self):
        """Test du calcul du temps restant"""
        session = SessionActive(
            ip_client='192.168.1.1',
            user_id='user@test.com',
            expiration=datetime.now() + timedelta(minutes=30)
        )
        assert 29 <= session.temps_restant_minutes <= 30

    def test_to_storage_dict(self):
        """Test de conversion en dictionnaire"""
        session = SessionActive(
            ip_client='192.168.1.1',
            user_id='user@test.com',
            expiration=datetime.now() + timedelta(minutes=30)
        )
        storage = session.to_storage_dict()
        assert isinstance(storage, dict)
        assert 'ip_client' in storage
        assert 'session_id' in storage
        assert isinstance(storage['expiration'], str)


class TestEvenementNavigation:
    """Tests pour EvenementNavigation"""

    def test_creation_evenement(self):
        """Test de création d'un événement"""
        event = EvenementNavigation(
            ip_client='192.168.1.1',
            user_id='user@test.com',
            session_id='test-session',
            methode='GET',
            domaine='github.com'
        )
        assert event.ip_client == '192.168.1.1'
        assert event.methode == 'GET'
        assert event.domaine == 'github.com'
        assert event.taille_bytes == 0
        assert event.statut_http == 200

    def test_normalisation_domaine(self):
        """Test de normalisation du domaine"""
        event = EvenementNavigation(
            ip_client='192.168.1.1',
            user_id='user@test.com',
            session_id='test-session',
            methode='GET',
            domaine='www.github.com'
        )
        assert event.domaine == 'github.com'

    def test_normalisation_domaine_majuscules(self):
        """Test de normalisation des majuscules"""
        event = EvenementNavigation(
            ip_client='192.168.1.1',
            user_id='user@test.com',
            session_id='test-session',
            methode='GET',
            domaine='GITHUB.COM'
        )
        assert event.domaine == 'github.com'

    def test_methode_invalide(self):
        """Test de validation de méthode invalide"""
        with pytest.raises(ValueError):
            EvenementNavigation(
                ip_client='192.168.1.1',
                user_id='user@test.com',
                session_id='test-session',
                methode='INVALID',
                domaine='github.com'
            )


class TestMetriqueTrafic:
    """Tests pour MetriqueTrafic"""

    def test_creation_metrique(self):
        """Test de création d'une métrique"""
        metrics = MetriqueTrafic(
            periode='1h',
            total_requetes=1000,
            total_bytes=10485760,
            top_domaines=['google.com', 'github.com'],
            repartition_categories={'Recherche': 500, 'Dev': 500}
        )
        assert metrics.periode == '1h'
        assert metrics.total_requetes == 1000
        assert metrics.total_bytes_mb == 10.0

    def test_valeurs_par_defaut(self):
        """Test des valeurs par défaut"""
        metrics = MetriqueTrafic(
            periode='1h',
            total_requetes=100,
            total_bytes=1024
        )
        assert metrics.top_domaines == []
        assert metrics.repartition_categories == {}


class TestAlerteAnomalie:
    """Tests pour AlerteAnomalie"""

    def test_creation_alerte(self):
        """Test de création d'une alerte"""
        alerte = AlerteAnomalie(
            user_id='user@test.com',
            score_zscore=3.5,
            volume_session=104857600,
            volume_moyen_groupe=20971520,
            details='Volume anormalement élevé'
        )
        assert alerte.user_id == 'user@test.com'
        assert alerte.score_zscore == 3.5
        assert alerte.volume_session_mb == 100.0
        assert alerte.volume_moyen_groupe_mb == 20.0
        assert alerte.acquittee is False
        assert alerte.alerte_id is not None


class TestConfigSeuils:
    """Tests pour ConfigSeuils"""

    def test_config_par_defaut(self):
        """Test de la configuration par défaut"""
        config = ConfigSeuils()
        assert config.zscore_seuil == 3.0
        assert config.volume_max_session_mb == 100
        assert config.duree_session_max_min == 30
        assert config.categories_bloquees == []

    def test_config_personnalisee(self):
        """Test de configuration personnalisée"""
        config = ConfigSeuils(
            zscore_seuil=2.5,
            volume_max_session_mb=200,
            duree_session_max_min=60,
            categories_bloquees=['Streaming vidéo', 'Réseaux sociaux']
        )
        assert config.zscore_seuil == 2.5
        assert config.volume_max_session_mb == 200
        assert len(config.categories_bloquees) == 2

    def test_categorie_invalide(self):
        """Test de validation de catégorie invalide"""
        with pytest.raises(ValueError):
            ConfigSeuils(
                categories_bloquees=['Catégorie inexistante']
            )


class TestUserRegistration:
    """Tests pour UserRegistration"""

    def test_creation_utilisateur_valide(self):
        """Test de création d'un utilisateur valide"""
        user = UserRegistration(
            first_name='Jean',
            last_name='Dupont',
            email='jean@example.com',
            accepts_cgu=True
        )
        assert user.first_name == 'Jean'
        assert user.last_name == 'Dupont'
        assert user.full_name == 'Jean Dupont'
        assert user.accepts_analytics is False

    def test_cgu_non_acceptee(self):
        """Test de refus des CGU"""
        with pytest.raises(ValueError) as exc_info:
            UserRegistration(
                first_name='Jean',
                last_name='Dupont',
                email='jean@example.com',
                accepts_cgu=False
            )
        assert 'Conditions Générales' in str(exc_info.value)

    def test_email_invalide(self):
        """Test d'email invalide"""
        with pytest.raises(ValueError):
            UserRegistration(
                first_name='Jean',
                last_name='Dupont',
                email='invalid-email',
                accepts_cgu=True
            )

    def test_accepte_analytics(self):
        """Test d'acceptation de l'analyse"""
        user = UserRegistration(
            first_name='Jean',
            last_name='Dupont',
            email='jean@example.com',
            accepts_cgu=True,
            accepts_analytics=True
        )
        assert user.accepts_analytics is True


class TestHealthStatus:
    """Tests pour HealthStatus"""

    def test_health_status(self):
        """Test du statut de santé"""
        health = HealthStatus(
            status='healthy',
            composants={'proxy': True, 'flask': True, 'api': True},
            sessions_actives=5,
            taille_dataframe=1000,
            taille_queue=42,
            uptime_secondes=3600
        )
        assert health.status == 'healthy'
        assert health.sessions_actives == 5
        assert health.taille_queue == 42
