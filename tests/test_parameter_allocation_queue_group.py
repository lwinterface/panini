import pytest

from panini.test_client import TestClient, get_logger_files_path
from panini import app as panini_app


def run_panini1():
    app = panini_app.App(
        service_name="test_allocation_queue_group1",
        host="127.0.0.1",
        port=4222,
        allocation_queue_group="group1",
        app_strategy="asyncio",
        logger_in_separate_process=False,
        logger_files_path=get_logger_files_path(),
    )

    @app.listen("test_parameter_allocation_queue_group.foo")
    async def foo(msg):
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
        logger_files_path=get_logger_files_path(),
    )

    @app.listen("test_parameter_allocation_queue_group.foo")
    async def foo(msg):
        return {"data": 2}

    app.start()


@pytest.fixture(scope="module")
def client():
    client1 = TestClient(run_panini1)
    client1.start()
    client2 = TestClient(run_panini2)
    client2.start()
    yield client2
    client1.stop()
    client2.stop()


def test_listen_subject_only_if_include_one_request(client):
    for _ in range(10):
        response = client.request("test_parameter_allocation_queue_group.foo", {})
        assert response["data"] in (1, 2)


def test_listen_subject_only_if_include_multiple_requests(client):
    """Tests that some requests are handled by first panini app and some by second"""
    results = set(
        client.request("test_parameter_allocation_queue_group.foo", {})["data"]
        for _ in range(10)
    )
    assert 1 in results
    assert 2 in results
