"""
tests/test_shared.py
Tests unitaires pour l'état partagé (shared/state.py).
"""

import pytest
from datetime import datetime, timedelta
from shared.state import (
    ajouter_session, obtenir_session, revoquer_session,
    session_est_valide, lister_sessions_actives, purger_sessions_expirees,
    ajouter_evenement, obtenir_evenement, taille_queue,
    ajouter_alerte, lister_alertes, acquitter_alerte,
    get_stats, reset_stats
)


class TestGestionSessions:
    """Tests pour la gestion des sessions"""

    def setup_method(self):
        """Réinitialise l'état avant chaque test"""
        reset_stats()
        # Nettoyer les sessions existantes
        purger_sessions_expirees()

    def test_ajouter_et_obtenir_session(self):
        """Test d'ajout et récupération d'une session"""
        session = {
            'token': 'test-123',
            'user_id': 'user@test.com',
            'user_name': 'Test User',
            'ip_client': '192.168.1.1',
            'expires_at': (datetime.now() + timedelta(minutes=30)).isoformat()
        }
        ajouter_session(session)
        
        retrieved = obtenir_session('192.168.1.1')
        assert retrieved is not None
        assert retrieved['user_id'] == 'user@test.com'
        assert retrieved['token'] == 'test-123'

    def test_session_est_valide(self):
        """Test de validation de session"""
        session = {
            'token': 'test-123',
            'user_id': 'user@test.com',
            'ip_client': '192.168.1.1',
            'expires_at': (datetime.now() + timedelta(minutes=30)).isoformat()
        }
        ajouter_session(session)
        
        assert session_est_valide('192.168.1.1') is True

    def test_session_expiree(self):
        """Test de session expirée"""
        session = {
            'token': 'test-123',
            'user_id': 'user@test.com',
            'ip_client': '192.168.1.1',
            'expires_at': (datetime.now() - timedelta(minutes=1)).isoformat()
        }
        ajouter_session(session)
        
        assert session_est_valide('192.168.1.1') is False

    def test_revoquer_session(self):
        """Test de révocation de session"""
        session = {
            'token': 'test-123',
            'user_id': 'user@test.com',
            'ip_client': '192.168.1.1',
            'expires_at': (datetime.now() + timedelta(minutes=30)).isoformat()
        }
        ajouter_session(session)
        
        result = revoquer_session('192.168.1.1', 'test')
        assert result is True
        assert obtenir_session('192.168.1.1') is None

    def test_lister_sessions_actives(self):
        """Test de listage des sessions actives"""
        session1 = {
            'token': 'token1',
            'user_id': 'user1@test.com',
            'ip_client': '192.168.1.1',
            'expires_at': (datetime.now() + timedelta(minutes=30)).isoformat()
        }
        session2 = {
            'token': 'token2',
            'user_id': 'user2@test.com',
            'ip_client': '192.168.1.2',
            'expires_at': (datetime.now() + timedelta(minutes=30)).isoformat()
        }
        ajouter_session(session1)
        ajouter_session(session2)
        
        sessions = lister_sessions_actives()
        assert len(sessions) == 2

    def test_purger_sessions_expirees(self):
        """Test de purge des sessions expirées"""
        session_valide = {
            'token': 'valid',
            'user_id': 'user1@test.com',
            'ip_client': '192.168.1.1',
            'expires_at': (datetime.now() + timedelta(minutes=30)).isoformat()
        }
        session_expiree = {
            'token': 'expired',
            'user_id': 'user2@test.com',
            'ip_client': '192.168.1.2',
            'expires_at': (datetime.now() - timedelta(minutes=1)).isoformat()
        }
        ajouter_session(session_valide)
        ajouter_session(session_expiree)
        
        count = purger_sessions_expirees()
        assert count == 1
        assert obtenir_session('192.168.1.1') is not None
        assert obtenir_session('192.168.1.2') is None


class TestFileEvenements:
    """Tests pour la file d'événements"""

    def setup_method(self):
        reset_stats()

    def test_ajouter_et_obtenir_evenement(self):
        """Test d'ajout et récupération d'événement"""
        event = {
            'ip_client': '192.168.1.1',
            'domain': 'google.com',
            'method': 'GET'
        }
        result = ajouter_evenement(event)
        assert result is True
        
        retrieved = obtenir_evenement(timeout=0.1)
        assert retrieved is not None
        assert retrieved['domain'] == 'google.com'

    def test_taille_queue(self):
        """Test de la taille de la queue"""
        assert taille_queue() == 0
        
        ajouter_evenement({'domain': 'test1.com'})
        ajouter_evenement({'domain': 'test2.com'})
        
        assert taille_queue() == 2


class TestAlertes:
    """Tests pour la gestion des alertes"""

    def setup_method(self):
        reset_stats()

    def test_ajouter_alerte(self):
        """Test d'ajout d'alerte"""
        alerte = {
            'user_id': 'user@test.com',
            'score_zscore': 3.5,
            'volume_session_mb': 100,
            'details': 'Volume anormal'
        }
        ajouter_alerte(alerte)
        
        alertes = lister_alertes()
        assert len(alertes) == 1
        assert alertes[0]['user_id'] == 'user@test.com'

    def test_acquitter_alerte(self):
        """Test d'acquittement d'alerte"""
        alerte = {
            'alerte_id': 'test-alerte-123',
            'user_id': 'user@test.com',
            'score_zscore': 3.5,
            'details': 'Volume anormal',
            'acquittee': False
        }
        ajouter_alerte(alerte)
        
        result = acquitter_alerte('test-alerte-123')
        assert result is True
        
        alertes = lister_alertes()
        assert alertes[0]['acquittee'] is True


class TestStats:
    """Tests pour les statistiques"""

    def setup_method(self):
        reset_stats()

    def test_get_stats(self):
        """Test de récupération des statistiques"""
        stats = get_stats()
        assert 'active_sessions' in stats
        assert 'queue_size' in stats
        assert 'total_requests' in stats
        assert 'uptime_seconds' in stats

    def test_reset_stats(self):
        """Test de réinitialisation des statistiques"""
        ajouter_evenement({'domain': 'test.com'})
        ajouter_evenement({'domain': 'test2.com'})
        
        stats_avant = get_stats()
        assert stats_avant['total_requests'] == 2
        
        reset_stats()
        stats_apres = get_stats()
        assert stats_apres['total_requests'] == 0
