import pytest

from panini.test_client import TestClient
from panini import app as panini_app
from .helper import get_testing_logs_directory_path


def run_panini():
    app = panini_app.App(
        service_name="test_timeout",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.listen("test_timeout.publish.request.not.existing.subject")
    async def publish_request(msg):
        return await app.request(
            subject="test_timeout.not-existing-subject", message={"data": 1}
        )

    app.start()


client = TestClient(run_panini)


@pytest.fixture(scope="session", autouse=True)
def start_client():
    client.start()


def test_publish_request_timeout():
    with pytest.raises(OSError):
        client.request("test_timeout.publish.request.not.existing.subject", {})
