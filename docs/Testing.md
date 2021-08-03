#Testing
Panini testing is possible with various testing frameworks.
We will show testing based on [pytest](https://docs.pytest.org/) framework.

## Using TestClient

Import `TestClient`.

Create a `TestClient` using [pytest.fixture](https://docs.pytest.org/en/latest/how-to/fixtures.html) with passing to it the function that `runs panini`.

TestClient object `.start()` will start the panini app for testing.

Create `functions` with a name that starts with `test_` (this is standard `pytest` conventions).

Use the `TestClient` object for nats communication the same way as you do with `panini` 
(but with some limitations)

(The panini uses [nats-python](https://github.com/Gr1N/nats-python) synchronous NATS client for testing)

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
    async def main_subject(msg):
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
async def main_subject(msg):
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

## Advanced testing

Now, let's dig into more details to see how to test different parts.

### Error testing

Let's say we need to check that the subject always require the authorization.

```python
from panini import app as panini_app

app = panini_app.App(
    service_name="test",
    host="127.0.0.1",
    port=4222
)

@app.listen("subject.with.authorization")
async def get_secret(msg):
    if "authorization" not in msg.data:
        raise ValueError("You need to be authorized, to get the secret data!")
    return {"secret": "some meaningful data"}

if __name__ == '__main__':
    app.start()
```

Let's create a test for this example

```python
import pytest
from panini.test_client import TestClient

def run_panini():
    from main import app
    app.start()

@pytest.fixture(scope="module")
def client():
    client = TestClient(run_panini).start()
    yield client
    client.stop()

def test_secret_subject(client):
    response = client.request("subject.with.authorization", {"authorization": "token"})
    assert response["secret"] == "some meaningful data"

def test_unauthorized_secret_subject(client):
    with pytest.raises(OSError):
        client.request("subject.with.authorization", {})
```

We can use this method of testing, but if we look precisely here - it is strange, that we are getting `OSError` instead of `ValueError` which we raised (also the tests will run extremely long because of nats-timeout).

 The reason of this, that `TestClient` is a separate `nats` service, that perform in our case simple request, but did not get the response, because of the error on application side.

But still, let's modify a bit our functions, to get the more obvious result:

```python
@app.listen("subject.with.authorization")
async def get_secret(msg):
    if "authorization" not in msg.data:
        return {"success": False, "message": "You have to be authorized, to get the secret data!"}
    return {"success": True, "secret": "some meaningful data"}
```

And the test function will look like this:

```python
def test_unauthorized_secret_subject(client):
    response = client.request("subject.with.authorization", {})
    assert response["success"] is False
    assert response["message"] == "You have to be authorized, to get the secret data!"
```

So we get the results faster and in more obvious way.

### Testing microservice with dependencies

Let's say we want to test an **authorization application**, which **depends** on another panini application, that gets data from the DB.

But for our testing purpose, we don't want to create & support the database, because our application does not have direct dependency on DB.

Using `TestClient` we can `mock` the communication between those applications. 

Let's dive into the code:

```python
from panini import app as panini_app

app = panini_app.App(
    service_name="authorization_microservice",
    host="127.0.0.1",
    port=4222
)

@app.listen("get.token")
async def get_token(msg):
    if "email" not in msg.data or "password" not in msg.data:
        return {"message": "You should provide email & password to authorize"}
    response = await app.request("db.authorization", {"email": msg.data["email"], "password": msg.data["password"]})
    return {"token": response["db_token"]}

if __name__ == '__main__':
    app.start()
```

And then, apply `mocking` using TestClient object `.listen` function.

 

```python
import pytest
from panini.test_client import TestClient

def run_panini():
    from main import app
    app.start()

fake_db = {"test_email": "test_token"}

@pytest.fixture()
def client():
    client = TestClient(run_panini)

    @client.listen("db.authorization")  # mock db.authorization subject
    def authorize(msg):
        return {"db_token": fake_db[msg.data["email"]]}  # provide testing data

    client.start()
    yield client
    client.stop()

def test_get_token(client):
    response = client.request("get.token", {"email": "test_email", "password": "test_password"})
    assert response["token"] == "test_token"
```

Notice that you have to call `@client.listen` decorator before `client.start()`

### TestClient publish & wait

We **strongly recommend** using other tools for testing (like `client.request` & `client.listen` only), but sometimes we need a specific `client.publish` & `client.wait` functions to test the panini application.

**Example for `client.publish` & `client.wait`**:

```python
from panini import app as panini_app

app = panini_app.App(
    service_name="test",
    host="127.0.0.1",
    port=4222
)

@app.listen("start")
async def start(msg):
    await app.request("app.started", {"success": True})

if __name__ == '__main__':
    app.start()
```

And testing file:

```python
import pytest
from panini.test_client import TestClient

def run_panini():
    from main import app
    app.start()

is_app_started = False

@pytest.fixture()
def client():
    client = TestClient(run_panini)

    @client.listen("app.started")
    def app_started(msg):
        global is_app_started
        is_app_started = True

    client.start()
    yield client
    client.stop()

def test_get_token(client):
    assert is_app_started is False
    client.publish("start", {})
    client.wait(1)  # wait for @client.listen callback to work
    assert is_app_started is True
```

Use `client.publish` only, when `@client.listen` returns nothing or **subject**, you want to test returns nothing (but you will need another subject, to check, if the call was successful)

**Example for `client.wait`:**

Let's say you want to test `@app.task` job:

```python
from panini import app as panini_app

app = panini_app.App(
    service_name="test",
    host="127.0.0.1",
    port=4222
)

@app.task()
async def task():
    await app.publish("task.job", {"job": "test"})

if __name__ == '__main__':
    app.start()
```

You can use `@client.listen` and `client.wait` for this stuff:

```python
import pytest
from panini.test_client import TestClient

def run_panini():
    from main import app
    app.start()

task_data = None

@pytest.fixture()
def client():
    client = TestClient(run_panini)

    @client.listen("task.job")
    def app_started(msg):
        global task_data
        task_data = msg.data["job"]

    client.start()
    yield client
    client.stop()

def test_get_token(client):
    assert task_data is None
    client.wait(1)  # wait for @client.listen callback to work
    assert task_data == "test"
```