Authentication is essential for any system, especially microservice architectures. Modern design approaches tend to isolate and encapsulate microservices. For the NATS world, this becomes especially critical with the release of one of the key features of NATS 2.0 - decentralized security. This feature allows creating access groups at NATS client level and at subject level. In other words, it "containerizes" a network, which opens up new possibilities for engineers. 

NATS offers several authentication strategies, we suggest you explore them here: [https://docs.nats.io/developing-with-nats/security](https://docs.nats.io/developing-with-nats/security)

Panini does not interact with the authentication process. In fact, it just gives the interface of [nats.py](http://nats.py/) to establish a connection with authentication. NATS supports user-password, token, JWT, TLS, and NKeys authentication.

Let's make an example with User-password. First, we need to run NATS broker with user-password access:

```python
nats-server --user john --pass johnpassword
```

Then let's write a microservice that connects to NATS but without the user and the password:

```python
from panini import app as panini_app

app = panini_app.App(
    service_name="some_microservice",
    host="127.0.0.1",
    port=4222,
)

if __name__ == "__main__":
    app.start()
```

Let's save it to a file named *[app.py](http://app.py)* and run it:

```python
> python3 app.py
2021-11-04 14:58:07,163 nats.aio.client ERROR    nats: encountered error
Traceback (most recent call last):
  File "*/*/*", line 318, in connect
    await self._process_connect_init()
  File "*/*/*", line 1673, in _process_connect_init
    raise NatsError("nats: " + err_msg.rstrip('\r\n'))
nats.aio.errors.NatsError: nats: 'Authorization Violation'
```

As you can see, an 'Authorization Violation' raised. There is no way to establish a connection with the NATS broker without credentials. Let's add the username and the password to our app:

```python
from panini import app as panini_app

auth = {
    "user": "john",
    "password": "jpassword"
}

app = panini_app.App(
    service_name="some_microservice",
    host="127.0.0.1",
    port=4222,
    auth=auth
)

if __name__ == "__main__":
    app.start()
```

Let's run it again:

```python
> python3 app.py
======================================================================================
Panini service connected to NATS..
id: 3
name: some_microservice__non_docker_env_270377__75017

NATS brokers:
*  nats://127.0.0.1:4222
======================================================================================
```

It seems we have connected to the NATS broker! 

You can check out more on authentication in [nats.py specs](https://github.com/nats-io/nats.py/blob/main/readme.md) or [NATS docs](https://docs.nats.io/developing-with-nats/security).