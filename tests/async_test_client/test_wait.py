import pytest

from panini.async_test_client import AsyncTestClient


counter = 0
second_counter = 0


@pytest.fixture
async def client():
    global counter, second_counter
    counter = 0
    second_counter = 0
    client = AsyncTestClient()

    @client.listen("async_test_client.test_wait")
    async def listen(msg):
        global counter
        counter += 1

    @client.listen("async_test_client.test_wait_second")
    async def listen(msg):
        global second_counter
        second_counter += 1

    await client.start()
    yield client
    await client.stop()


@pytest.mark.asyncio
async def test_request(client: AsyncTestClient):
    subject = "async_test_client.test_wait"
    count_calls = 10
    for _ in range(count_calls):
        await client.publish(subject, {})
    await client.wait(
        count_calls, timeout=1
    )  # wait for at least 10 messages to be handled
    assert counter == count_calls


@pytest.mark.asyncio
async def test_request(client: AsyncTestClient):
    subject = "async_test_client.test_wait"
    count_calls = 15
    for _ in range(count_calls):
        await client.publish(subject, {})
    await client.wait(count_calls, subject=subject)  # only for this subject
    assert counter == count_calls


@pytest.mark.asyncio
async def test_request(client: AsyncTestClient):
    subject = "async_test_client.test_wait"
    subject_second = "async_test_client.test_wait_second"
    count_calls = 5
    for _ in range(count_calls):
        await client.publish(subject, {})
        await client.publish(subject_second, {})
    await client.wait(
        subjects={subject: count_calls, subject_second: count_calls}
    )  # for more than 1 subject
    assert counter == count_calls
    assert second_counter == count_calls
    assert client.count_subject_calls(subject) == count_calls
    assert client.count_subject_calls(subject_second) == count_calls
