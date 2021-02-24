import time
import pytest

from panini.test_client import TestClient
from panini import app as panini_app
from .helper import get_testing_logs_directory_path

from panini.utils.helper import start_process


def run_panini1():
    app = panini_app.App(
        service_name="test_allocation_queue_group1",
        host="127.0.0.1",
        port=4222,
        allocation_queue_group="group1",
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.listen("foo")
    async def foo(subject, message):
        return {"data": 1}

    app.start()


def run_panini2():
    app = panini_app.App(
        service_name="test_allocation_queue_group2",
        host="127.0.0.1",
        port=4222,
        allocation_queue_group="group1",
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_testing_logs_directory_path(),
    )

    @app.listen("foo")
    async def foo(subject, message):
        return {"data": 2}

    app.start()


@pytest.fixture(scope="session", autouse=True)
def start_client():
    # if you want to run more that 1 panini app in testing, please use start_process function for each app
    start_process(run_panini1)
    start_process(run_panini2)
    # wait for panini apps to setup
    time.sleep(2)


# after that, no need to run client.start(), because panini already running
client = TestClient()


def test_listen_subject_only_if_include_one_request():
    response = client.request("foo", {})
    assert response["data"] in (1, 2)


def test_listen_subject_only_if_include_multiple_requests():
    """Tests that some requests are handled by first panini app and some by second"""
    results = set(client.request("foo", {})["data"] for _ in range(10))
    assert 1 in results
    assert 2 in results
