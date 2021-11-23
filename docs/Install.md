
### Prerequisites:

Before getting started make sure you have all the prerequisites installed:

- Python
- pip
- NATS
- Docker (only if you want to run NATS via Docker)

Panini supports Python≥3.8, we recommend using the latest version

NATS should be installed as the [documentation suggests](https://docs.nats.io/nats-server/installation), one of the ways is described below. 

After installation, you need to run NATS.

  

### Installing NATS

Install via Docker:

```python
> docker pull nats:latest
```

On Windows:

```python
> choco install nats-server
```

On Mac OS:

```python
> brew install nats-server
```

### Running NATS

Simply run the following command:

```python
> nats-server
[1281] 2021/11/01 07:19:20.762736 [INF] Starting nats-server version 2.1.6
[1281] 2021/11/01 07:19:20.762853 [INF] Git commit [not set]
[1281] 2021/11/01 07:19:20.763182 [INF] Listening for client connections on 0.0.0.0:4222
[1281] 2021/11/01 07:19:20.763190 [INF] Server id is NBIDLI72N7ONJZSSFKLL774A7RWCKVHU26X2QI7RFOETJFURXA6CETRB
[1281] 2021/11/01 07:19:20.763192 [INF] Server is ready
```

### Installing Panini

Install Panini via pip:

```bash
> pip install panini
```

Check that Panini has been installed

```bash
> pip show panini
Name: panini
Version: 0.6.0
Summary: A python messaging framework for microservices based on NATS
Home-page: https://github.com/lwinterface/panini
Author: Op Return SA, developers: Andrii Volotskov, Danylo Tiutiushkin, Oleksii Volotskov
Author-email: example@example.com
License: MIT
Location: /Library/Frameworks/Python.framework/Versions/3.8/lib/python3.8/site-packages
Requires: six, requests, python-json-logger, async-timeout, asyncio-nats-client, prometheus-client, websocket-client, nest-asyncio, nats-python, ujson, yarl, aiohttp, aiohttp-cors
Required-by:
```

Install Panini via GitHub:

```bash
> git clone https://github.com/lwinterface/panini.git
```