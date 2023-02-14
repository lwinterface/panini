Panini testing is possible with various testing frameworks. 
Here we will show testing based on [pytest](https://docs.pytest.org/) framework.

## Using TestClient

Import <span class="red">`TestClient`</span>.

Create a <span class="red">`TestClient`</span> using [pytest.fixture](https://docs.pytest.org/en/latest/how-to/fixtures.html) by passing it to the function that runs panini.

TestClient object <span class="red">`.start()`</span> will start the panini app for testing.

Create <span class="red">`functions`</span> with a name that starts with <span class="red">`test_`</span> (this is standard <span class="red">`pytest`</span> convention).

Use the <span class="red">`TestClient`</span> object for NATS communication the same way you would do with <span class="red">`panini`</span> 

Panini uses [nats-python](https://github.com/Gr1N/nats-python) synchronous NATS client for testing

Write simple <span class="red">`assert`</span> statements with the standard Python expressions that you need to check (<span class="red">`pytest`</span> standard).

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
<div class="attention">
<p class="attention__emoji-icon">🔥</p><p> Notice that the testing functions are normal <span class="red">def</span>, not <span class="red">async def</span>.
Also, the calls to the client are also normal calls, not using <span class="red">await</span>.
This allows you to use <span class="red">pytest</span> directly without complications.</p>
</div>


<div class="attention">
<p class="attention__emoji-icon">🛠</p><p> Notice that panini TestClient will run a panini app in a  <span class="red">different process</span>. 
The Windows and Mac platforms have limitations for transferring objects to a different process.
So we have to use  <span class="red">run_panini</span> function that will implement or import our app, and we must use  <span class="red">fixtures</span> to setup TestClient.</p>
</div>
<div class="attention">
<p class="attention__emoji-icon">🔑</p><p>  Notice that if you use <span class="red">pytest.fixture</span> without <span class="red">scope</span> the panini App will setup and teardown for each test.
If you don't want this - please use <span class="red">pytest.fixture(scope="module)</span></p>
</div>


## Separating tests

In a real application, you mostly would have your tests in a different file.

Your **Panini** app can also be in different files or modules.

### Panini **app file**

Let's say you have a file <span class="red">`main.py`</span> with your **Panini** app:

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

Then you could have a file <span class="red">`test_main.py`</span> with your tests, and import your <span class="red">app</span> from the <span class="red">`main`</span> module (<span class="red">`main.py`</span>):

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
<div class="attention">
<p class="attention__emoji-icon">⚙</p><p> Under the hood, <span class="red">TestClient</span> will run your panini application inside the different process.
And will communicate with it only using NATS messaging.
This is how you can <b>simulate</b> your panini app activity.</p>
</div>
<div class="attention">
<p class="attention__emoji-icon">🛠</p><p><span class="red">TestClient</span> will run 2 NATS clients for testing (one for sending, and one for listening).
The sending NATS client is in the <b>main Thread</b>, while the listening client can be in a separate thread.</p>
</div>

### Error testing

Let's say we need to check that the subject always requires an authorization.

```python
from panini import app as panini_app

app = panini_app.App(
    service_name="test",
    host="127.0.0.1",
    port=4222
)

@app.listen("subject.with.authorization")
def get_secret(msg):
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

We can use this method of testing, but if we take a better look - it's strange that we are getting a <span class="red">`OSError`</span> instead of a <span class="red">`ValueError`</span> Also, the tests will run for an extremely long time because of nats-timeout.

The reason for this is that <span class="red">`TestClient`</span> is a separate NATS service, that performs a simple request in our case. It does not get the response, because of an error on the application side.

But still, let's modify a bit our functions, to get the more obvious result:

```python
@app.listen("subject.with.authorization")
def get_secret(msg):
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

So we get the results faster and in a more obvious way.

### Testing microservice with dependencies

Let's say we want to test an **authorization application**, which **depends** on another panini application, that fetches data from a DB.

For our testing purpose, we don't want to create & support the database, because our application does not have a direct dependency on DB.

Using <span class="red">`TestClient`</span> we can <span class="red">`mock`</span> the communication between those applications. 

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

And then, apply <span class="red">`mocking`</span> using <span class="red">`TestClient`</span> object <span class="red">`.listen`</span> function.

 

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
<div class="attention">
<p class="attention__emoji-icon">💡</p><p>Notice that you have to call <span class="red">@client.listen</span> decorator before <span class="red">client.start()</span></p>
</div>

### TestClient publish & wait

We **strongly recommend** using other tools for testing (like <span class="red">`client.request`</span> & <span class="red">`client.listen`</span> only), but sometimes we need a specific <span class="red">`client.publish`</span> & <span class="red">`client.wait`</span> to test the panini application.
<div class="attention">
<p class="attention__emoji-icon">📖</p><p><span class="red">client.wait</span> is used to manually wait for <span class="red">@client.listen</span> callback to be called.
It was previously done automatically</p>
</div>

<div class="attention">
<p class="attention__emoji-icon">☝</p><p>You should specify <span class="red">client.start(do_always_listen=False)</span> to be able to use <span class="red">client.wait</span></p>
</div>

**Example for <span class="red">`client.publish`</span> & <span class="red">`client.wait`</span>**:

```python
from panini import app as panini_app

app = panini_app.App(
    service_name="test",
    host="127.0.0.1",
    port=4222
)

@app.listen("start")
async def start(msg):
    await app.publish("app.started", {"success": True})

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

    client.start(do_always_listen=False)
    yield client
    client.stop()

def test_get_token(client):
    assert is_app_started is False
    client.publish("start", {})
    client.wait(1)  # wait for @client.listen callback to work
    assert is_app_started is True
```
<div class="attention">
<p class="attention__emoji-icon">💡</p><p>Use <span class="red">client.publish</span> only, when <span class="red">@client.listen</span> returns nothing or <b>subject</b>. But you will need another subject, to check, if the call was successful.</p>
</div>

**Example for <span class="red">`client.wait`</span>:**

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

You can use `@client.listen` and `client.wait` for this:

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

    client.start(do_always_listen=False)
    yield client
    client.stop()

def test_get_token(client):
    assert task_data is None
    client.wait(1)  # wait for @client.listen callback to work
    assert task_data == "test"
```

