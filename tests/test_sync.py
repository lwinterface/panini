import pytest

from panini.test_client import TestClient
from panini import app as panini_app

from tests.helper import Global


def run_panini():
    app = panini_app.App(
        service_name="test_sync",
        host="127.0.0.1",
        port=4222,
        app_strategy="sync",
        logger_in_separate_process=False,
    )

    @app.listen("test_sync.foo")
    def subject_for_requests(msg):
        return {"test": msg.data["test"] + 1}

    @app.listen("test_sync.foo.*.bar")
    def composite_subject_for_requests(msg):
        return {"test": msg.subject + str(msg.data["test"])}

    @app.listen("test_sync.publish")
    def publish(msg):
        app.publish_sync(
            subject="test_sync.publish.listener", message={"test": msg.data["test"] + 1}
        )

    @app.listen("test_sync.publish.request")
    def publish_request(msg):
        response = app.request_sync(
            subject="test_sync.publish.request.helper",
            message={"test": msg.data["test"] + 1},
        )
        app.publish_sync(
            subject="test_sync.publish.request.listener",
            message={"test": response["test"] + 3},
        )

    @app.listen("test_sync.publish.request.helper")
    def publish_request_helper(msg):
        return {"test": msg.data["test"] + 2}

    @app.listen("test_sync.publish.request.reply")
    def publish_request(msg):
        app.publish_sync(
            subject="test_sync.publish.request.reply.helper",
            message={"test": msg.data["test"] + 1},
            reply_to="test_sync.publish.request.reply.replier",
        )

    @app.listen("test_sync.publish.request.reply.helper")
    def publish_request_helper(msg):
        res = {"test": msg.data["test"] + 1}
        print("Send: ", res)
        return res

    @app.listen("test_sync.publish.request.reply.replier")
    def publish_request_helper(msg):
        app.publish_sync(
            subject="test_sync.publish.request.reply.listener",
            message={"test": msg.data["test"] + 1},
        )

    @app.listen("test_sync.finish")
    def kill(msg):
        if hasattr(app.connector, "nats_listener_process"):
            app.connector.nats_listener_process.terminate()
        if hasattr(app.connector, "nats_sender_process"):
            app.connector.nats_sender_process.terminate()

    app.start()


global_object = Global()


@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini)

    @client.listen("test_sync.publish.listener")
    def publish_listener(msg):
        global_object.public_variable = msg.data["test"] + 1

    @client.listen("test_sync.publish.request.listener")
    def publish_request_listener(msg):
        global_object.another_variable = msg.data["test"] + 4

    @client.listen("test_sync.publish.request.reply.listener")
    def publish_request_reply_listener(msg):
        global_object.additional_variable = msg.data["test"] + 1

    client.start(is_sync=True)
    yield client
    client.stop()


def test_listen_simple_subject_with_response(client):
    response = client.request("test_sync.foo", {"test": 1})
    assert response["test"] == 2


def test_listen_composite_subject_with_response(client):
    subject1 = "test_sync.foo.some.bar"
    subject2 = "test_sync.foo.another.bar"
    response1 = client.request(subject1, {"test": 1})
    response2 = client.request(subject2, {"test": 2})
    assert response1["test"] == f"{subject1}1"
    assert response2["test"] == f"{subject2}2"


# NotImplemented - raises an error
# def test_publish(client):
#     assert global_object.public_variable == 0
#     client.publish("test_sync.publish", {"test": 1})
#     client.wait(1)
#     assert global_object.public_variable == 3
#
#
# NotImplemented - raises an error
# def test_publish_request(client):
#     assert global_object.another_variable == 0
#     client.publish("test_sync.publish.request", {"test": 0})
#     client.wait(1)
#     assert global_object.another_variable == 10
#
#
# NotImplemented - raises an error
# def test_publish_request_reply(client):
#     assert global_object.additional_variable == 0
#     client.publish("publish.request.reply", {"test": 0})
#     client.wait(1)
#     assert global_object.additional_variable == 4


def test_finish(client):
    # finalize
    client.publish("test_sync.finish", {})
    import time

    time.sleep(1)
    client.panini_process.terminate()
