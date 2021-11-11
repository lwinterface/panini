# Changelog
## [v0.6.2](https://github.com/lwinterface/panini/tree/v0.6.2) (2021-11-11)

- Fixed bug: tasks doesn't works with HTTP server
- Fixed package incompatibility

## [v0.6.0](https://github.com/lwinterface/panini/tree/v0.6.0) (2021-11-04)

- Global refactoring
- Added new interface for pereodic tasks: @app.task(interval=1)
- Changed `listen_subject_only_if_include` param in App to function `app.add_filters(include, exclude)`
- Added ability to use all authorization methods from nats.py
- Added ability to establish connection to multiple NATS brokers
- Added start message when starting in terminal

## [v0.5.2](https://github.com/lwinterface/panini/tree/v0.5.2) (2021-08-17)

- Added ability to use any parameters for aiohttp including ssl_context(for HTTPS)

## [v0.5.0](https://github.com/lwinterface/panini/tree/v0.5.0) (2021-07-21)

- Implemented AsyncTestClient for better testing experience
- Added listen_subject_only_if_exclude parameter for excluding unnecessary subjects

## [v0.4.0](https://github.com/lwinterface/panini/tree/v0.4.0) (2021-07-09)

- Fixed silent error if response type is list
- Fixed TestClient
- Added non-blocking request support for bytes messages
- Added automatically generated changelog
- Added pending_bytes_limit parameter to panini App for nats_client
- Added is_async parameter to subscribe_new_subject for nats_client
- Added data types for dynamic subscription
- Added test for long requests

## [v0.3.1](https://github.com/lwinterface/panini/tree/v0.3.1) (2021-05-25)

- Fixed bug with no hinting for publish & request functions
- Removed 'app_strategy' parameter
- Removed old 'aio' interface for nats_client & managers
- Added auto unsubscribe to test_client waiting for panini to start
- Change ci test flow, add test on python v3.9 -major fixes in TestClient, changes in client.wait() function
- Added non-blocking request support for bytes messages

## [v0.3.0](https://github.com/lwinterface/panini/tree/v0.3.0) (2021-04-27)

- removed sync app connection strategy
- removed redis dependency
- minor fix

## [v0.2.3](https://github.com/lwinterface/panini/tree/v0.2.3) (2021-04-06)

- Added CI/CD checks
- Moved from json to ujson
- Fixed logging bugs
- Fixed bug with emulator for windows
- Many minor bugs

## [v0.2.2](https://github.com/lwinterface/panini/tree/v0.2.2) (2021-03-24)

- Added Emulator middlewares: ReaderEmulatorMiddleware & WriterEmulatorMiddleware
- Fixed Test client
- Minor fix: grafana dashboard default rate size changed from 1m to 15m PrometheusMonitoringMiddleware(ex ListenPerformancePrometheusTracerMiddleware)

## [v0.2.0](https://github.com/lwinterface/panini/tree/v0.2.0) (2021-03-12)

- Msg object instead of arguments subject and message in listener's callbacks
- Addition datatypes supported: bytes, str
- Added publish/request from another thread
- Added http-like middlewares
- Added default middleware that calculates processing time for incoming messages and sends it to pushgateway(prometheus)
- Added default middleware that sends alert message to some topic if service for NatsTimeoutError
- Changed default console logging level: WARNING -> INFO
- Added new examples



