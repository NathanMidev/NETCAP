from api.schemas import SessionActive
from datetime import datetime


def test_session_active_creation():
    """
    Test simple pour vérifier la création d'une session valide.
    """

    session = SessionActive(
        ip_client="192.168.1.1",
        user_id="user@test.com",
        session_id="abc123",
        debut=datetime.now(),
        expiration=datetime.now(),
        nb_requetes=5,
        volume_bytes=2048,
        categorie_dominante="Streaming"
    )

    assert session.ip_client == "192.168.1.1"
    assert session.nb_requetes == 5