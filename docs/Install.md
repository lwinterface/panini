
### Prerequisites

Before getting started, you need to have the following prerequisites installed:
- Python (3.8 or higher) 
- pip
- NATS
- Docker (optional) 

### Installing NATS

NATS should be installed as per the [documentation instructions](https://docs.nats.io/nats-server/installation). Here are some of the ways to do so:

- **Using Docker**: 
  ```python
  > docker pull nats:latest
  ```
- **On Windows**: 
  ```python
  > choco install nats-server
  ```
- **On Mac OS**: 
  ```python
  > brew install nats-server
  ```
  
### Running NATS

Once NATS is installed, you need to run the server. Simply execute the following command:

```python
> nats-server
[1281] 2021/11/01 07:19:20.762736 [INF] Starting nats-server version 2.1.6
[1281] 2021/11/01 07:19:20.762853 [INF] Git commit [not set]
[1281] 2021/11/01 07:19:20.763182 [INF] Listening for client connections on 0.0.0.0:4222
[1281] 2021/11/01 07:19:20.763190 [INF] Server id is NBIDLI72N7ONJZSSFKLL774A7RWCKVHU26X2QI7RFOETJFURXA6CETRB
[1281] 2021/11/01 07:19:20.763192 [INF] Server is ready
```

### Installing Panini

You can install Panini using the `pip` package manager or from the [GitHub repository](https://github.com/lwinterface/panini). 

- **Using pip**:
  ```bash
  > pip install panini
  ```

- **Using GitHub**:
  ```bash
  > git clone https://github.com/lwinterface/panini.git
  ```
  
After installation, verify that Panini has been installed by running this command:

```bash
> pip show panini
Name: panini
Version: 0.8.0
Summary: A python messaging framework for microservices based on NATS
Home-page: https://github.com/lwinterface/panini
Author: Op Return SA, developers: Andrii Volotskov, Danylo Tiutiushkin
Author-email: example@example.com
License: MIT
Location: /Users/artas/ITProduction/Pierre/panini/venv310/lib/python3.10/site-packages
Requires: python-json-logger, nest-asyncio, ujson, nats-py
Required-by:
```