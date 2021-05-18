# Changelog

## [Unreleased](https://github.com/lwinterface/panini/tree/HEAD)

[Full Changelog](https://github.com/lwinterface/panini/compare/v0.3.0...HEAD)

**Implemented enhancements:**

- Naming issue in check\_logger - use check\_logger\_connected instead [\#148](https://github.com/lwinterface/panini/issues/148)
- Cut sync strategy [\#137](https://github.com/lwinterface/panini/issues/137)

**Fixed bugs:**

- TestClient problem on @client.listen - do not wait, while publishing response back [\#153](https://github.com/lwinterface/panini/issues/153)

**Closed issues:**

- Re-add test for allocation queue group [\#157](https://github.com/lwinterface/panini/issues/157)
- Fix names for subscribe\_new\_subject \(remove old `aio` interface\) [\#151](https://github.com/lwinterface/panini/issues/151)
- Remove sync from panini TestClient [\#150](https://github.com/lwinterface/panini/issues/150)
- Minor issue - remove panini app's arguments 'app\_strategy', 'num\_of\_queues', 'publish\_subjects' [\#149](https://github.com/lwinterface/panini/issues/149)

## [v0.3.0](https://github.com/lwinterface/panini/tree/v0.3.0) (2021-04-27)

[Full Changelog](https://github.com/lwinterface/panini/compare/v0.2.3...v0.3.0)

**Implemented enhancements:**

- release 0.2.3 [\#139](https://github.com/lwinterface/panini/pull/139) ([artas728](https://github.com/artas728))
- From json to ujson [\#117](https://github.com/lwinterface/panini/pull/117) ([artas728](https://github.com/artas728))

**Fixed bugs:**

- Emulator examples does not work: ModuleNotFoundError: No module named 'panini.emulator' [\#145](https://github.com/lwinterface/panini/issues/145)
- TestClient timed out socket bug [\#142](https://github.com/lwinterface/panini/issues/142)
- bool fields fix [\#135](https://github.com/lwinterface/panini/pull/135) ([artas728](https://github.com/artas728))
- Ujson in requirements [\#122](https://github.com/lwinterface/panini/pull/122) ([artas728](https://github.com/artas728))
- from warn logger to print for experimental warning in emulator [\#116](https://github.com/lwinterface/panini/pull/116) ([artas728](https://github.com/artas728))

**Merged pull requests:**

- Removed sync app strategy [\#147](https://github.com/lwinterface/panini/pull/147) ([artas728](https://github.com/artas728))
- Cut sync strategy [\#146](https://github.com/lwinterface/panini/pull/146) ([danylott](https://github.com/danylott))
- \#142 - added auto-reconnect parameter to TestClient, that will reconn… [\#143](https://github.com/lwinterface/panini/pull/143) ([danylott](https://github.com/danylott))
- Bug/logger not working until app start [\#136](https://github.com/lwinterface/panini/pull/136) ([danylott](https://github.com/danylott))
- hotfix for test\_wss - added sleep waiting for websockets [\#132](https://github.com/lwinterface/panini/pull/132) ([danylott](https://github.com/danylott))
- Circleci project setup [\#129](https://github.com/lwinterface/panini/pull/129) ([bugimprover](https://github.com/bugimprover))
- \#125 - fixed test\_middleware\_manager - make independent testing middl… [\#128](https://github.com/lwinterface/panini/pull/128) ([danylott](https://github.com/danylott))
- \#118 - renamed: app.\_client\_id -\> app.client\_id in PrometheusMonitori… [\#121](https://github.com/lwinterface/panini/pull/121) ([danylott](https://github.com/danylott))
- \#101 - added posibility to pass args and kwargs to TestClient run\_panini [\#112](https://github.com/lwinterface/panini/pull/112) ([danylott](https://github.com/danylott))
- \#109 - fix requirements prometheus client on develop [\#110](https://github.com/lwinterface/panini/pull/110) ([danylott](https://github.com/danylott))
- changed ":" to "-" for emulator files [\#108](https://github.com/lwinterface/panini/pull/108) ([oleksii-v](https://github.com/oleksii-v))

## [v0.2.3](https://github.com/lwinterface/panini/tree/v0.2.3) (2021-04-06)

[Full Changelog](https://github.com/lwinterface/panini/compare/v0.2.2...v0.2.3)

**Implemented enhancements:**

- Use ujson instead of json to increase performance [\#114](https://github.com/lwinterface/panini/issues/114)
- app.logger and get\_logger\(\) is not working untill app.start\(\) [\#113](https://github.com/lwinterface/panini/issues/113)
- add posibility to pass args and kwargs to TestClient run\_panini [\#101](https://github.com/lwinterface/panini/issues/101)
- Middleware that count amount of request by status [\#82](https://github.com/lwinterface/panini/issues/82)
- Use labels in ListenPerformanceMonitoring middleware [\#81](https://github.com/lwinterface/panini/issues/81)

**Fixed bugs:**

- Bool field in validator doesn't work [\#134](https://github.com/lwinterface/panini/issues/134)
- Panini tests do not pass on Ubuntu with `pytest` command [\#125](https://github.com/lwinterface/panini/issues/125)
- ModuleNotFoundError: No module named 'ujson' [\#120](https://github.com/lwinterface/panini/issues/120)
- Error in PrometheusMonitoringMiddleware: AttributeError: 'App' object has no attribute '\_client\_id' [\#118](https://github.com/lwinterface/panini/issues/118)
- fix requirements prometheus client on develop [\#109](https://github.com/lwinterface/panini/issues/109)
- Error while cloning panini: error: unable to create file examples/emulator/resources/events.listener.2021-03-19-16:21:13.jsonl: Invalid argument [\#107](https://github.com/lwinterface/panini/issues/107)
- RuntimeWarning in time sending panini\_event.\*.\*.started with NATSTimeoutMiddleware [\#98](https://github.com/lwinterface/panini/issues/98)
- Fix app.\_start\_tasks [\#88](https://github.com/lwinterface/panini/issues/88)
- test\_client sleep\_time - depends on computer power [\#79](https://github.com/lwinterface/panini/issues/79)
- None does not have SIGKILL [\#28](https://github.com/lwinterface/panini/issues/28)

**Closed issues:**

- Integrate emulation system [\#49](https://github.com/lwinterface/panini/issues/49)
- Additional\(optional\) datatypes for messages: str, bytes [\#35](https://github.com/lwinterface/panini/issues/35)
- ./run\_test.sh - modify tests to run with simple pytest command, instead of shell script [\#27](https://github.com/lwinterface/panini/issues/27)
-  Change arguments format in endpoints [\#25](https://github.com/lwinterface/panini/issues/25)
- Not logic sub title [\#13](https://github.com/lwinterface/panini/issues/13)

**Merged pull requests:**

- Release v0.2.3 [\#140](https://github.com/lwinterface/panini/pull/140) ([artas728](https://github.com/artas728))

## [v0.2.2](https://github.com/lwinterface/panini/tree/v0.2.2) (2021-03-24)

[Full Changelog](https://github.com/lwinterface/panini/compare/v0.2.1...v0.2.2)

**Implemented enhancements:**

- Minor fix: change grafana dashboard default rate size from 1m to 15m [\#102](https://github.com/lwinterface/panini/issues/102)
- Panini dashboard [\#83](https://github.com/lwinterface/panini/issues/83)
- Release v0.2.2 [\#105](https://github.com/lwinterface/panini/pull/105) ([artas728](https://github.com/artas728))
- Release v0.2.2 [\#104](https://github.com/lwinterface/panini/pull/104) ([artas728](https://github.com/artas728))
- 1m default rate size changed to 15m [\#103](https://github.com/lwinterface/panini/pull/103) ([artas728](https://github.com/artas728))

**Fixed bugs:**

- :wrench: app selection fix \#16 [\#96](https://github.com/lwinterface/panini/pull/96) ([artas728](https://github.com/artas728))

**Merged pull requests:**

- Emulator [\#99](https://github.com/lwinterface/panini/pull/99) ([oleksii-v](https://github.com/oleksii-v))
- Fix test client sleep time [\#97](https://github.com/lwinterface/panini/pull/97) ([danylott](https://github.com/danylott))
- Panini dashboard [\#95](https://github.com/lwinterface/panini/pull/95) ([artas728](https://github.com/artas728))
- :chart\_with\_upwards\_trend: added grafana dashboard [\#94](https://github.com/lwinterface/panini/pull/94) ([artas728](https://github.com/artas728))
- version updated to 0.2.1 [\#93](https://github.com/lwinterface/panini/pull/93) ([artas728](https://github.com/artas728))

## [v0.2.1](https://github.com/lwinterface/panini/tree/v0.2.1) (2021-03-17)

[Full Changelog](https://github.com/lwinterface/panini/compare/v0.2.0...v0.2.1)

**Implemented enhancements:**

- Initialize logger only at \_start\(\) [\#67](https://github.com/lwinterface/panini/issues/67)

**Fixed bugs:**

- How to request default logger if there is no access too "app" object? [\#51](https://github.com/lwinterface/panini/issues/51)

**Merged pull requests:**

- Monitoring middleware [\#92](https://github.com/lwinterface/panini/pull/92) ([artas728](https://github.com/artas728))
- hotfix: send Panini event "started" only for asyncio app\_strategy [\#91](https://github.com/lwinterface/panini/pull/91) ([artas728](https://github.com/artas728))
- Send message when NATSClient started [\#90](https://github.com/lwinterface/panini/pull/90) ([artas728](https://github.com/artas728))
- Prometheus monitoring middleware [\#86](https://github.com/lwinterface/panini/pull/86) ([danylott](https://github.com/danylott))
- \#67 - run logger on app.\_start\(\), added test\_client.stop\(\) method, im… [\#80](https://github.com/lwinterface/panini/pull/80) ([danylott](https://github.com/danylott))
- added labels to ListenerMonitoring [\#75](https://github.com/lwinterface/panini/pull/75) ([artas728](https://github.com/artas728))
- For v0.2.0 [\#70](https://github.com/lwinterface/panini/pull/70) ([artas728](https://github.com/artas728))

## [v0.2.0](https://github.com/lwinterface/panini/tree/v0.2.0) (2021-03-12)

[Full Changelog](https://github.com/lwinterface/panini/compare/0.1.2...v0.2.0)

**Fixed bugs:**

- ListenPerformancePrometheusTracerMiddleware doesn't work [\#59](https://github.com/lwinterface/panini/issues/59)
- Middlewares don't work for dynamic listeners [\#58](https://github.com/lwinterface/panini/issues/58)
- send\_any, send\_publish, send\_request in one middleware [\#41](https://github.com/lwinterface/panini/issues/41)
- Remove annotations on message for publish and request - because for now we use more than just dict [\#38](https://github.com/lwinterface/panini/issues/38)
- Middlewares for dynamic listeners and ListenPerformancePrometheusTracerMiddleware minor fix  [\#62](https://github.com/lwinterface/panini/pull/62) ([artas728](https://github.com/artas728))

**Closed issues:**

- Rename ListenPerformancePrometheusTracerMiddleware to something shorter [\#57](https://github.com/lwinterface/panini/issues/57)
- Change log.warning -\> log.info in simple\_examples, because we use for now log.info as default console format [\#52](https://github.com/lwinterface/panini/issues/52)
- How to deliver build-in middlewares? [\#50](https://github.com/lwinterface/panini/issues/50)
- Make TestClient listen interface the same, as in app.listen\(\) [\#30](https://github.com/lwinterface/panini/issues/30)

**Merged pull requests:**

- Added new packages and dependencies [\#73](https://github.com/lwinterface/panini/pull/73) ([artas728](https://github.com/artas728))
- added new packages and dependencies [\#72](https://github.com/lwinterface/panini/pull/72) ([artas728](https://github.com/artas728))
- Listen monitoring fix [\#71](https://github.com/lwinterface/panini/pull/71) ([artas728](https://github.com/artas728))
- Listen monitoring percentile [\#69](https://github.com/lwinterface/panini/pull/69) ([danylott](https://github.com/danylott))
- quickfix - use Msg in test\_client [\#68](https://github.com/lwinterface/panini/pull/68) ([danylott](https://github.com/danylott))
-  \#30 - client.listen interface now is the same as in nats\_client \(usi… [\#66](https://github.com/lwinterface/panini/pull/66) ([danylott](https://github.com/danylott))
- \#38 - improved nats\_client interface, removed annotations from message [\#65](https://github.com/lwinterface/panini/pull/65) ([danylott](https://github.com/danylott))
- get\_logger default parameter and log.warning -\> log.info in examples  [\#64](https://github.com/lwinterface/panini/pull/64) ([danylott](https://github.com/danylott))
- Built in middlewares NATSTimeout & ListenPerfomanceMonitoring [\#55](https://github.com/lwinterface/panini/pull/55) ([artas728](https://github.com/artas728))
- Built in middlewares [\#54](https://github.com/lwinterface/panini/pull/54) ([danylott](https://github.com/danylott))

## [0.1.2](https://github.com/lwinterface/panini/tree/0.1.2) (2021-03-10)

[Full Changelog](https://github.com/lwinterface/panini/compare/v0.1.3...0.1.2)

## [v0.1.3](https://github.com/lwinterface/panini/tree/v0.1.3) (2021-03-10)

[Full Changelog](https://github.com/lwinterface/panini/compare/0.1.1...v0.1.3)

**Implemented enhancements:**

- Move validators to pydantic [\#18](https://github.com/lwinterface/panini/issues/18)
- Test validators [\#11](https://github.com/lwinterface/panini/issues/11)

**Fixed bugs:**

- Test client does not show errors from panini side - only errors, that returns back or logged [\#46](https://github.com/lwinterface/panini/issues/46)

**Closed issues:**

- Test different datatypes functionality [\#48](https://github.com/lwinterface/panini/issues/48)
- Update in README for middlewares [\#42](https://github.com/lwinterface/panini/issues/42)
- test wss example [\#23](https://github.com/lwinterface/panini/issues/23)
- Use Black8 as default project formatter [\#21](https://github.com/lwinterface/panini/issues/21)
- Default logger level  [\#16](https://github.com/lwinterface/panini/issues/16)
- Used Python Libraries [\#14](https://github.com/lwinterface/panini/issues/14)
- Change word "topic" to "subject" [\#12](https://github.com/lwinterface/panini/issues/12)
- slow customers  [\#4](https://github.com/lwinterface/panini/issues/4)
- Middleware [\#3](https://github.com/lwinterface/panini/issues/3)

**Merged pull requests:**

- \#46 - added error logging for panini testclient [\#47](https://github.com/lwinterface/panini/pull/47) ([danylott](https://github.com/danylott))
- :coconut: few words about middlewares [\#45](https://github.com/lwinterface/panini/pull/45) ([artas728](https://github.com/artas728))
- Middleware integration [\#40](https://github.com/lwinterface/panini/pull/40) ([artas728](https://github.com/artas728))
- make tests independent - to run it simply using pytest command [\#36](https://github.com/lwinterface/panini/pull/36) ([danylott](https://github.com/danylott))
- Bump aiohttp from 3.6.3 to 3.7.4 in /examples/dockercompose\_project/microservice1 [\#33](https://github.com/lwinterface/panini/pull/33) ([dependabot[bot]](https://github.com/apps/dependabot))
- \#21 - applied black formatter, flake8 python PEP8 principles and  [\#32](https://github.com/lwinterface/panini/pull/32) ([danylott](https://github.com/danylott))
- Test validators wss \#11, \#23 [\#31](https://github.com/lwinterface/panini/pull/31) ([danylott](https://github.com/danylott))
- middleware\_dict using msg object functionality [\#29](https://github.com/lwinterface/panini/pull/29) ([danylott](https://github.com/danylott))
- :wrench: readme minor fix [\#24](https://github.com/lwinterface/panini/pull/24) ([artas728](https://github.com/artas728))
- Added middleware dict feature -  [\#22](https://github.com/lwinterface/panini/pull/22) ([danylott](https://github.com/danylott))
- Added dynamic subscribe/unsubscribe [\#20](https://github.com/lwinterface/panini/pull/20) ([artas728](https://github.com/artas728))
- Bump aiohttp from 3.6.3 to 3.7.4 in /requirements [\#15](https://github.com/lwinterface/panini/pull/15) ([dependabot[bot]](https://github.com/apps/dependabot))

## [0.1.1](https://github.com/lwinterface/panini/tree/0.1.1) (2021-02-26)

[Full Changelog](https://github.com/lwinterface/panini/compare/7751489a13af06fba290a64dec0d224e8bc171ab...0.1.1)

**Fixed bugs:**

- Tests on Mac & Windows platform [\#8](https://github.com/lwinterface/panini/issues/8)
- Logger in separate process error on Mac & Windows [\#6](https://github.com/lwinterface/panini/issues/6)
- Windows support [\#5](https://github.com/lwinterface/panini/issues/5)
- having a root logging [\#1](https://github.com/lwinterface/panini/issues/1)

**Closed issues:**

- Default logging in the main process [\#10](https://github.com/lwinterface/panini/issues/10)

**Merged pull requests:**

- \#8 fix tests for support Mac & Windows - fixed using pytest.fixture\(s… [\#9](https://github.com/lwinterface/panini/pull/9) ([danylott](https://github.com/danylott))
- \#5 \#6 issues handled [\#7](https://github.com/lwinterface/panini/pull/7) ([danylott](https://github.com/danylott))
- Testclient [\#2](https://github.com/lwinterface/panini/pull/2) ([danylott](https://github.com/danylott))



\* *This Changelog was automatically generated by [github_changelog_generator](https://github.com/github-changelog-generator/github-changelog-generator)*
