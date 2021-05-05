# Install
### Install Panini

Supported Python≥3.8

Install via pip:
```bash
> pip install panini
```
Install via GitHub:

```bash
> git clone https://github.com/lwinterface/panini.git
```

### Install NATS

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

### Run NATS

Just run command:

```python
> nats-server
```

Or run broker via docker-compose. From project directory that includes file [docker-compose.yml](https://github.com/lwinterface/panini/blob/master/docker-compose.yml). Command below:

```python
> docker-compose up
```

Stop broker when you finish work with it:

```python
> docker-compose down
```

Note, for production we recommend running the broker with dockerized microservices. Example of dockerized panini project here