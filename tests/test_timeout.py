import pytest

from panini.test_client import TestClient, get_logger_files_path
from panini import app as panini_app


def run_panini():
    app = panini_app.App(
        service_name="test_timeout",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_logger_files_path(),
    )

    @app.listen("test_timeout.publish.request.not.existing.subject")
    async def publish_request(msg):
        return await app.request(
            subject="test_timeout.not-existing-subject", message={"data": 1}
        )

    app.start()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini)
    client.start()
    yield client
    client.stop()


def test_publish_request_timeout(client):
    with pytest.raises(OSError):
        client.request("test_timeout.publish.request.not.existing.subject", {})
