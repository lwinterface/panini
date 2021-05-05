Panini testing is possible with various testing frameworks.
We will show testing based on [pytest](https://docs.pytest.org/) framework.

## Using TestClient

Import `TestClient`.

Create a `TestClient` using [pytest.fixture](https://docs.pytest.org/en/latest/how-to/fixtures.html) with passing to it the function that `runs panini`.

TestClient object `.start()` will start the panini app for testing.

Create `functions` with a name that starts with `test_` (this is standard `pytest` conventions).

Use the `TestClient` object the same way as you do with `nats-client`

> The panini uses nats-python nats client for testing

(The panini uses [nats-python](https://github.com/Gr1N/nats-python) nats client for testing)

Write simple `assert` statements with the standard Python expressions that you need to check (`pytest` standard).

```python
import pytest
from panini import app as panini_app
from panini.test_client import TestClient

def run_panini():
    app = panini_app.App(
        service_name="test",
        host="127.0.0.1",
        port=4222
    )

    @app.listen("main.subject")
    def main_subject(msg):
        return {"message": "Hello World!"}

    app.start()

@pytest.fixture
def client():
    client = TestClient(run_panini).start()
    yield client
    client.stop()

def test_main_subject(client):
    response = client.request("main.subject", {})
    assert response["message"] == "Hello World!"
```

Notice that the testing functions are normal `def`, not `async def`.
And the calls to the client are also normal calls, not using `await`.
This allows you to use `pytest` directly without complications.

Notice that panini TestClient will run panini app in the `different process`. 
The Windows and Mac platforms have limitations for transferring objects to different process.
So we have to use `run_panini` function that will implement or import our app, and we must use `fixtures` to setup TestClient.

Notice that if you use pytest.fixture without `scope` the panini App will setup and teardown for each test.
If you don't want this - please use `pytest.fixture(scope="module)`

## Separating tests

In a real application, you mostly would have your tests in a different file.

And you **Panini** app can be also in different files or modules.

### Panini **app file**

Let's say you have a file `[main.py](http://main.py)` with your **Panini** app:

```python
from panini import app as panini_app

app = panini_app.App(
    service_name="test",
    host="127.0.0.1",
    port=4222
)

@app.listen("main.subject")
def main_subject(msg):
    return {"message": "Hello World!"}

if __name__ == '__main__':
    app.start()
```

### Testing file

Then you could have a file `test_main.py` with your tests, and import your `app` from the `main` module (`main.py`):

```python
import pytest
from panini.test_client import TestClient

def run_panini():
    from .main import app
    app.start()

@pytest.fixture
def client():
    client = TestClient(run_panini).start()
    yield client
    client.stop()

def test_main_subject(client):
    response = client.request("main.subject", {})
    assert response["message"] == "Hello World!"
```