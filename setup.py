# Always prefer setuptools over distutils
from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / "README.md").read_text(encoding="utf-8")


setup(
    name="panini",
    version="0.1.0",
    description="A python messaging framework for microservices based on NATS",
    long_description=long_description,
    url="https://github.com/lwinterface/panini",
    author="Op Return SA, developers: Andrew Volotskov, Danylo Tiutiushkin",
    author_email="example@example.com",
    python_requires=">=3.8.2",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3 :: Only",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS :: MacOS X",
        "Topic :: System :: Networking",
        "Topic :: System :: Distributed Computing",
    ],
    packages=["panini"],
    install_requires=[
        "aiohttp>=3.6.2",
        "aiohttp-cors>=0.7.0",
        "async-timeout>=3.0.1",
        "asyncio-nats-client>=0.11.2",
        "redis>=3.5.3",
        "requests>=2.24.0",
        "six>=1.15.0",
        "yarl>=1.6.1",
        "python-json-logger>=2.0.1",
        "nats-python>=0.8.0",
    ],
    keywords=[
        "nats",
        "microservice" "stream",
        "processing",
        "asyncio",
        "distributed",
        "queue",
    ],
    project_urls={  # Optional
        "Bug Reports": "https://github.com/pypa/panini/issues",
        "Source": "https://github.com/pypa/panini/",
    },
    zip_safe=False,
)
