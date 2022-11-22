# Always prefer setuptools over distutils
from setuptools import setup, find_packages

long_description = """
Panini is a modern framework for quick development of streaming microservices.
Our goal is to create fastapi/aiohttp/flask-like solution but for NATS streaming.
The framework allows you to work with NATS features and some additional logic using a simple interface:

- publish messages to subject
- subscribe to subject
- request-response
- request-response to another subject
- tasks
- periodic tasks
- middlewares
- HTTP server

"""

setup(
    name="panini",
    version="0.8.0a2",
    description="A python messaging framework for microservices based on NATS",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    url="https://github.com/lwinterface/panini",
    author="Op Return SA, developers: Andrii Volotskov, Danylo Tiutiushkin",
    author_email="example@example.com",
    python_requires=">=3.8.3",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3 :: Only",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Topic :: System :: Networking",
        "Topic :: System :: Distributed Computing",
    ],
    packages=[
        "panini",
        "panini.utils",
        "panini.http_server",
        "panini.middleware",
        "panini.managers",
    ],
    install_requires=[
        "async-timeout==4.0.0",
        "nats-py==2.2.0",
        "websocket-client>=1.2.3",
        "requests>=2.24.0",
        "six>=1.15.0",
        "yarl>=1.6.1",
        "python-json-logger>=2.0.1",
        "nest-asyncio==1.5.1",
        "prometheus-client==0.9.0",
        "nats-python>=0.8.0",
        "ujson==5.4.0",
    ],
    keywords=[
        "nats",
        "microservice",
        "stream",
        "processing",
        "asyncio",
        "distributed",
        "queue",
    ],
    project_urls={  # Optional
        "Bug Reports": "https://github.com/lwinterface/panini/issues",
        "Source": "https://github.com/lwinterface/panini/",
    },
    zip_safe=False,
)
