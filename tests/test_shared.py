"""
Tests unitaires pour l'état partagé (shared/state.py).
"""

import pytest
from datetime import datetime, timedelta
from shared.state import (
    ajouter_session,
    get_session,
    obtenir_session,
    supprimer_session,
    session_valide,
    event_queue,
    sessions,
    lock
)


class TestGestionSessions:
    """Tests pour la gestion des sessions"""

    def setup_method(self):
        """Nettoie les sessions avant chaque test"""
        with lock:
            sessions.clear()
        # Vider la queue
        while not event_queue.empty():
            try:
                event_queue.get_nowait()
            except:
                break

    def test_ajouter_et_get_session(self):
        """Test d'ajout et récupération d'une session"""
        session_id = ajouter_session("192.168.1.1", "user@test.com", 30)
        
        session = get_session("192.168.1.1")
        assert session is not None
        assert session["user_id"] == "user@test.com"
        assert session["session_id"] == session_id
        assert session["nb_requetes"] == 0
        assert session["volume_bytes"] == 0

    def test_obtenir_session_alias(self):
        """Test de l'alias obtenir_session"""
        ajouter_session("192.168.1.2", "alice@test.com", 30)
        
        session = obtenir_session("192.168.1.2")
        assert session is not None
        assert session["user_id"] == "alice@test.com"

    def test_session_valide(self):
        """Test de validation de session (non expirée)"""
        ajouter_session("192.168.1.1", "user@test.com", 30)
        
        assert session_valide("192.168.1.1") is True

    def test_session_expiree(self):
        """Test de session expirée"""
        # Créer une session avec expiration dans le passé
        with lock:
            sessions["192.168.1.1"] = {
                "session_id": "test-id",
                "user_id": "user@test.com",
                "expiration": datetime.now() - timedelta(minutes=1),
                "nb_requetes": 0,
                "volume_bytes": 0
            }
        
        assert session_valide("192.168.1.1") is False
        # La session doit être supprimée
        assert get_session("192.168.1.1") is None

    def test_session_inexistante(self):
        """Test avec une IP qui n'a pas de session"""
        assert session_valide("10.0.0.1") is False
        assert get_session("10.0.0.1") is None

    def test_supprimer_session(self):
        """Test de suppression de session"""
        ajouter_session("192.168.1.1", "user@test.com", 30)
        assert get_session("192.168.1.1") is not None
        
        supprimer_session("192.168.1.1")
        assert get_session("192.168.1.1") is None

    def test_supprimer_session_inexistante(self):
        """Supprimer une session qui n'existe pas ne doit pas planter"""
        supprimer_session("10.0.0.99")  # Ne doit pas lever d'erreur

    def test_multiple_sessions(self):
        """Test avec plusieurs sessions simultanées"""
        ajouter_session("192.168.1.1", "user1@test.com", 30)
        ajouter_session("192.168.1.2", "user2@test.com", 30)
        ajouter_session("192.168.1.3", "user3@test.com", 30)
        
        with lock:
            assert len(sessions) == 3
        
        assert get_session("192.168.1.1")["user_id"] == "user1@test.com"
        assert get_session("192.168.1.2")["user_id"] == "user2@test.com"
        assert get_session("192.168.1.3")["user_id"] == "user3@test.com"

    def test_session_nb_requetes_initial(self):
        """Vérifie que nb_requetes commence à 0"""
        ajouter_session("192.168.1.1", "user@test.com", 30)
        session = get_session("192.168.1.1")
        assert session["nb_requetes"] == 0

    def test_session_volume_bytes_initial(self):
        """Vérifie que volume_bytes commence à 0"""
        ajouter_session("192.168.1.1", "user@test.com", 30)
        session = get_session("192.168.1.1")
        assert session["volume_bytes"] == 0

    def test_session_id_est_unique(self):
        """Vérifie que chaque session a un ID unique"""
        id1 = ajouter_session("192.168.1.1", "user1@test.com", 30)
        id2 = ajouter_session("192.168.1.2", "user2@test.com", 30)
        
        assert id1 != id2
        assert len(id1) == 36  # UUID standard
        assert len(id2) == 36


class TestFileEvenements:
    """Tests pour la file d'événements"""

    def setup_method(self):
        with lock:
            sessions.clear()
        while not event_queue.empty():
            try:
                event_queue.get_nowait()
            except:
                break

    def test_queue_est_vide_initialement(self):
        """La file d'événements doit être vide au départ"""
        assert event_queue.empty() is True

    def test_ajouter_dans_queue(self):
        """Ajouter un événement dans la queue"""
        event_queue.put({"domain": "google.com", "method": "GET"})
        assert event_queue.qsize() == 1

    def test_queue_peut_contenir_plusieurs_evenements(self):
        """La queue peut contenir plusieurs événements"""
        event_queue.put({"domain": "google.com"})
        event_queue.put({"domain": "github.com"})
        event_queue.put({"domain": "stackoverflow.com"})
        
        assert event_queue.qsize() == 3