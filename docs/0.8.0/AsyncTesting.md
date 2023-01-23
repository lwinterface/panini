# Async Testing

A more advanced way to proceed with testing the Panini application.
Please, proceed with simple "Panini Testing" for a better experience.

Ability to run async tests is required for using `AsyncTestClient`
(were tested only using [*pytest-async*](https://github.com/pytest-dev/pytest-asyncio) )

## Advantages vs TestClient

- Supports `>` and `*` in subjects;
- Advanced usage of `await client.wait()`;
- Similar interface as with `panini.nats_client`;
- Separate timeout for each `publish`, `request`, `wait`;
- Additional `count_subject_calls` function.

## Using AsyncTestClient

The process of working with `AsyncTestClient` is similar to simple `TestClient`

Import `AsyncTestClient`.

Create an `AsyncTestClient` object using [*pytest.fixture*](https://docs.pytest.org/en/latest/how-to/fixtures.html) (with async support) with passing to it the function that `runs panini`.

`AsyncTestClient` object `.start()` will start the panini app for testing.

Create `functions` with a name that starts with `test_` (this is standard `pytest` conventions).

Use `@pytest.mark.asyncio` for async support - pytest-asyncio feature.

Use the `AsyncTestClient` object for nats communication the same way as you do with `panini` (but with some limitations)

(The panini uses [*nats-io*](https://github.com/nats-io/nats.py) asynchronous NATS client for testing)

Write simple `assert` statements with the standard Python expressions that you need to check (`pytest` standard).

```python
import pytest
from panini import app as panini_app
from panini.async_test_client import AsyncTestClient

def run_panini():
    app = panini_app.App(
        service_name="test",
        host="127.0.0.1",
        port=4222
    )

    @app.listen("main.subject")
    async def main_subject(msg):
        return {"message": "Hello World!"}

    app.start()

@pytest.fixture
async def client():
    client = await AsyncTestClient(run_panini).start()
    yield client
    await client.stop()

@pytest.mark.asyncio
async def test_main_subject(client):
    response = await client.request("main.subject", {})
    assert response["message"] == "Hello World!"
```

Notice that the testing functions are normal `async def`, not common `def`.
And calls to the client are also using `await`.
This is allowed because of `pytest-asyncio`.

Notice that panini AsyncTestClient will run the panini app in a `different process`. 
The Windows and Mac platforms have limitations for transferring objects to different processes.
So we have to use `run_panini` function that will implement or import our app, and we must use `fixtures` to set up AsyncTestClient.

## Examples & use cases in code

Usage of `client.count_subject_calls()` example:

`main.py`

```python
from panini import app as panini_app

app = panini_app.App(
    service_name="test",
    host="127.0.0.1",
    port=4222
)

@app.listen("choose.table")
async def choose_table(msg):
    for table_id in range(10):
        response = await app.request("check.table.is.free", {"table_id": table_id})
        if response["is_free"] is True:
            await app.publish(f"reserve.table.{table_id}", {})
            return {"success": True, "table_id": table_id}

    return {"success": False}

if __name__ == '__main__':
    app.start()
```

`test_main.py`

```python
import pytest
from panini.async_test_client import AsyncTestClient

def run_panini():
    from main import app
    app.start()

@pytest.fixture
async def client():
    client = AsyncTestClient(run_panini)

    @client.listen("check.table.is.free")
    def check_table_is_free(msg):
        if msg.data["table_id"] == 4:
            return {"is_free": True}
        return {"is_free": False}

    @client.listen("reserve.table.*")
    def reserve_table(msg):
        pass

    await client.start()  # use after @client.listen
    yield client
    await client.stop()

@pytest.mark.asyncio
async def test_choose_table(client: AsyncTestClient):
    response = await client.request("choose.table", {})
    assert response["success"] is True
    assert response["table_id"] == 4
    assert client.count_subject_calls("check.table.is.free") == 5
    assert client.count_subject_calls("reserve.table.*") == 1
```

Usage of `client.wait()`:

`main.py`

```python
import time

from panini import app as panini_app

app = panini_app.App(
    service_name="test",
    host="127.0.0.1",
    port=4222
)

@app.task()
async def publish_data():
    for _ in range(5):
        await app.publish("data.1", {"data": "data1"})
        time.sleep(0.05)

    for _ in range(5):
        await app.publish("data.2", {"data": "data2"})
        time.sleep(0.05)

if __name__ == '__main__':
    app.start()
```

`test_main.py`

```python
import pytesawait client.wait(10, timeout=0.5)t
from panini.async_test_client import AsyncTestClient

def run_panini():
    from main import app
    app.start()

data = []

@pytest.fixture
async def client():
    client = AsyncTestClient(run_panini)

    @client.listen("data.*")
    def save_data(msg):
        data.append(msg.data)

    await client.start()
    yield client
    data.clear()
    await client.stop()

@pytest.mark.asyncio
async def test_task_publish_data_1(client: AsyncTestClient):
    await client.wait(10, timeout=0.5)
    assert len(data) == 10

@pytest.mark.asyncio
async def test_task_publish_data_2(client: AsyncTestClient):
    await client.wait(10, subject="data.*")
    assert len(data) == 10

@pytest.mark.asyncio
async def test_task_publish_data_3(client: AsyncTestClient):
    await client.wait(subjects={
        "data.1": 5,
        "data.2": 5,
    })
    assert len(data) == 10
```

All these 3 methods are suited to test this `main.py`, but the last one is the most concrete.