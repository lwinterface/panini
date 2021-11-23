# Panini Docks

<span style="font-size:4em;">👋</span>
 
**Hey there!**

Welcome to Panini's explanatory documentation! Here you can become familiar with the concept, learn how to setup a working environment, and take your first steps towards building with it.

Panini is a python microframework based on the [nats.py](http://nats.py/) library. Its goal is to offer developers an easy way to create NATS microservices with a lower barrier of entry. It provides a specific template for creating microservices, similarly to FastAPI, Aiohttp, or Flask. Like all of the above frameworks, Panini has its design limits and edge cases. In the event that you become restricted by Panini's capabilities, we recommend switching to [nats.py](https://github.com/nats-io/nats.py).

Panini was inspired by [Faust](https://github.com/robinhood/faust) project.

**What are microservices?**

Microservices are a type of software architecture that breaks up the features of an application into smaller, task-specific functions to make the app more resilient and scalable. More info about it here: [https://microservices.io](https://microservices.io/)

**What can Panini do for me?**

Panini allows you to create microservices that use NATS to communicate with each other and extend the microservice by adding an HTTP server ([aiohttp](https://github.com/aio-libs/aiohttp)) to it if necessary.

**Compatibility with libraries**

Panini works well with various libraries used with FastAPI, Aiohttp, or Flask.

**Can I scale it?**

Yes, you can scale out your microservices horizontally. There are 2 strategies for distributing traffic between microservices:

- Parallel processing: Each microservice processes all messages
- Balancing: Messages are placed in a common queue and distributed among a group of microservices

**Monitoring**

Panini has a [Grafana](https://grafana.com) dashboard for performance monitoring; the code is [here](https://github.com/lwinterface/panini/blob/master/grafana_dashboard/panini_dashboard.json). Also, we are planning to add the ability to use [Opentracing](https://opentracing.io) soon.

**Do you support JetStream?**

Not at the moment.

**How to start?**

We recommend getting familiar with Panini in the following order:

- Understand what NATS is about
- Install NATS and Panini
- Complete Quickstart
- Understand Panini interface and datatypes
- Explore validation and middlewares
- Try to create a Panini microservice with an HTTP server
- Test and debug
- Deploy to server
- Write your own issue and PR to make Panini better 🙂