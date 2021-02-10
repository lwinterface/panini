from anthill.test_client import TestClient
from anthill import app as ant_app
from .helper import get_testing_logs_directory_path

from tests.helper import Global


def run_anthill():
    app = ant_app.App(
        service_name="test_sync",
        host="127.0.0.1",
        port=4222,
        app_strategy="sync",
        logger_files_path=get_testing_logs_directory_path(),
        logger_in_separate_process=False,
    )

    @app.listen("foo")
    def topic_for_requests(topic, message):
        return {"test": message["test"] + 1}

    @app.listen("foo.*.bar")
    def composite_topic_for_requests(topic, message):
        return {"test": topic + str(message["test"])}

    @app.listen("publish")
    def publish(topic, message):
        app.publish_sync(
            topic="publish.listener", message={"test": message["test"] + 1}
        )

    @app.listen("publish.request")
    def publish_request(topic, message):
        response = app.request_sync(
            topic="publish.request.helper", message={"test": message["test"] + 1}
        )
        app.publish_sync(
            topic="publish.request.listener", message={"test": response["test"] + 3}
        )

    @app.listen("publish.request.helper")
    def publish_request_helper(topic, message):
        return {"test": message["test"] + 2}

    @app.listen("publish.request.reply")
    def publish_request(topic, message):
        app.publish_sync(
            topic="publish.request.reply.helper",
            message={"test": message["test"] + 1},
            reply_to="publish.request.reply.replier",
        )

    @app.listen("publish.request.reply.helper")
    def publish_request_helper(topic, message):
        res = {"test": message["test"] + 1}
        print("Send: ", res)
        return res

    @app.listen("publish.request.reply.replier")
    def publish_request_helper(topic, message):
        app.publish_sync(
            topic="publish.request.reply.listener",
            message={"test": message["test"] + 1},
        )

    @app.listen("finish")
    def kill(topic, message):
        if hasattr(app.connector, "nats_listener_process"):
            app.connector.nats_listener_process.terminate()
        if hasattr(app.connector, "nats_sender_process"):
            app.connector.nats_sender_process.terminate()

    app.start()


client = TestClient(run_anthill)

global_object = Global()


@client.listen("publish.listener")
def publish_listener(topic, message):
    global_object.public_variable = message["test"] + 1


@client.listen("publish.request.listener")
def publish_request_listener(topic, message):
    global_object.another_variable = message["test"] + 4


@client.listen("publish.request.reply.listener")
def publish_request_reply_listener(topic, message):
    print("message: ", message)
    global_object.additional_variable = message["test"] + 1


client.start(is_sync=True)


def test_listen_simple_topic_with_response():
    response = client.request("foo", {"test": 1})
    assert response["test"] == 2


def test_listen_composite_topic_with_response():
    topic1 = "foo.some.bar"
    topic2 = "foo.another.bar"
    response1 = client.request(topic1, {"test": 1})
    response2 = client.request(topic2, {"test": 2})
    assert response1["test"] == f"{topic1}1"
    assert response2["test"] == f"{topic2}2"


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
    client.anthill_process.terminate()
