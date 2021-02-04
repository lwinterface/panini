from anthill.test_client import TestClient
from anthill import app as ant_app


def run_anthill():
    app = ant_app.App(
        service_name="test_publish_request",
        host="127.0.0.1",
        port=4222,
        app_strategy="asyncio",
        logger_required=False,
    )

    @app.listen("start")
    async def publish_request(topic, message):
        response = await app.aio_publish_request({"data": 1}, topic="foo")
        return response

    app.start()


client = TestClient(run_anthill)


@client.listen("foo")
def foo_listener(topic, message):
    message["data"] += 1
    return message


# should be placed after all @client.listen
client.start()


def test_publish_request():
    response = client.request("start", {})
    assert response["data"] == 2
