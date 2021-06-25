import pytest

from panini.test_client import TestClient


def run_panini():
    from tests.separate_file.main import app

    app.start()


@pytest.fixture
def client():
    return TestClient(run_panini).start()


def test_request(client):
    subject = "separate_file.listen_request"
    response = client.request(subject, {})
    assert response["success"] is True
    assert response["message"] == subject
