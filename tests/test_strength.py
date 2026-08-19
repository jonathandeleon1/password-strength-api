from fastapi.testclient import TestClient

from app.main import app
from app.strength import analyze, character_pool_size, entropy_bits

client = TestClient(app)


def test_empty_password_has_no_entropy():
    assert entropy_bits("") == 0.0


def test_pool_grows_with_character_variety():
    assert character_pool_size("abc") == 26
    assert character_pool_size("abc123") == 36
    assert character_pool_size("Abc123!") == 94


def test_longer_password_scores_higher():
    assert entropy_bits("abcdefgh") > entropy_bits("abcd")


def test_analyze_returns_expected_keys():
    result = analyze("Tr0ub4dor&3")
    assert set(result) == {"length", "character_pool", "entropy_bits", "rating"}


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_analyze_endpoint_does_not_echo_input():
    """The API must never reflect a submitted password back to the caller."""
    response = client.post("/analyze", json={"password": "hunter2"})
    assert response.status_code == 200
    assert "hunter2" not in response.text