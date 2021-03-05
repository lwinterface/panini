import pytest

from panini.test_client import TestClient
from panini import app as panini_app
from .helper import get_testing_logs_directory_path

from tests.helper import Global


def run_panini():
    app = panini_app.App(
        service_name="test_sync",
        host="127.0.0.1",
        port=4222,
        app_strategy="sync",
        logger_files_path=get_testing_logs_directory_path(),
        logger_in_separate_process=False,
    )

    @app.listen("foo")
    def subject_for_requests(msg):
        return {"test": msg.data["test"] + 1}

    @app.listen("foo.*.bar")
    def composite_subject_for_requests(msg):
        return {"test": msg.subject + str(msg.data["test"])}

    @app.listen("publish")
    def publish(msg):
        app.publish_sync(
            subject="publish.listener", message={"test": msg.data["test"] + 1}
        )

    @app.listen("publish.request")
    def publish_request(msg):
        response = app.request_sync(
            subject="publish.request.helper", message={"test": msg.data["test"] + 1}
        )
        app.publish_sync(
            subject="publish.request.listener", message={"test": response["test"] + 3}
        )

    @app.listen("publish.request.helper")
    def publish_request_helper(msg):
        return {"test": msg.data["test"] + 2}

    @app.listen("publish.request.reply")
    def publish_request(msg):
        app.publish_sync(
            subject="publish.request.reply.helper",
            message={"test": msg.data["test"] + 1},
            reply_to="publish.request.reply.replier",
        )

    @app.listen("publish.request.reply.helper")
    def publish_request_helper(msg):
        res = {"test": msg.data["test"] + 1}
        print("Send: ", res)
        return res

    @app.listen("publish.request.reply.replier")
    def publish_request_helper(msg):
        app.publish_sync(
            subject="publish.request.reply.listener",
            message={"test": msg.data["test"] + 1},
        )

    @app.listen("finish")
    def kill(msg):
        if hasattr(app.connector, "nats_listener_process"):
            app.connector.nats_listener_process.terminate()
        if hasattr(app.connector, "nats_sender_process"):
            app.connector.nats_sender_process.terminate()

    app.start()


client = TestClient(run_panini)

global_object = Global()


@client.listen("publish.listener")
def publish_listener(subject, message):
    global_object.public_variable = message["test"] + 1


@client.listen("publish.request.listener")
def publish_request_listener(subject, message):
    global_object.another_variable = message["test"] + 4


@client.listen("publish.request.reply.listener")
def publish_request_reply_listener(subject, message):
    print("message: ", message)
    global_object.additional_variable = message["test"] + 1


@pytest.fixture(scope="session", autouse=True)
def start_client():
    client.start(is_sync=True)


def test_listen_simple_subject_with_response():
    response = client.request("foo", {"test": 1})
    assert response["test"] == 2


def test_listen_composite_subject_with_response():
    subject1 = "foo.some.bar"
    subject2 = "foo.another.bar"
    response1 = client.request(subject1, {"test": 1})
    response2 = client.request(subject2, {"test": 2})
    assert response1["test"] == f"{subject1}1"
    assert response2["test"] == f"{subject2}2"


def test_publish():
    assert global_object.public_variable == 0
    client.publish("publish", {"test": 1})
    client.wait(1)
    assert global_object.public_variable == 3


def test_publish_request():
    assert global_object.another_variable == 0
    client.publish("publish.request", {"test": 0})
    client.wait(1)
    assert global_object.another_variable == 10


# NotImplemented - raises an error
# def test_publish_request_reply():
#     assert global_object.additional_variable == 0
#     client.publish("publish.request.reply", {"test": 0})
#     client.wait(1)
#     assert global_object.additional_variable == 4


def test_finish():
    # finalize
    client.publish("finish", {})
    import time

    time.sleep(1)
    client.panini_process.terminate()
