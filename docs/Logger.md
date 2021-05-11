# Logger
Logger has 2 important parameters:

- logger_files_path - the path to the log folder - can be absolute or relative (will relate to the app root path):

```python
from panini import app as panini_app

app = panini_app.App(
    service_name='logger_example',
    host='127.0.0.1',
    port=4222,
    logger_files_path='some/relative/path',  # put here absolute or relative path
)

log = app.logger

log.info("some log")  # write log
```

- in_separate_process - specify, if you want logger to be as separate process or to log in main process:

```python
from panini import app as panini_app

app = panini_app.App(
    service_name='logger_example',
    host='127.0.0.1',
    port=4222,
    logger_in_separate_process=False,  # by default, more intuitive
    # logger_in_separate_process=True  # more efficient, but needs good understanding of process
)

log = app.logger

log.info("some log")  # write log
```

# Log Config:

In the logger we use simple default config, that fit majority of logger needs:

```json
`{
  "version": 1,
  // we use False for handling build in errors in our logs
  "disable_existing_loggers": false,
  "formatters": {
    "detailed": {
      "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
      // notice 'extra' field - that's for extra arguments logging
      "format": "%(created)f %(name)s %(levelname)s %(processName)s %(threadName)s %(message)s %(extra)s"
    },
    "simple": {
      "class": "logging.Formatter",
      "format": "%(asctime)s %(name)-15s %(levelname)-8s %(message)s"
    }
  },
  "handlers": {
    "console": {
      "class": "logging.StreamHandler",
      "level": "INFO",
      "formatter": "simple",
      "stream": "ext://sys.stdout"
    },
    "panini": {
        "level": "DEBUG",
        "class": "logging.handlers.RotatingFileHandler",
        "filename": "panini.log",
        "mode": "a",
        "formatter": "detailed",
        "maxBytes": 1000000,
        "backupCount": 10,
    },
    "inter_services_request": {
      "level": "DEBUG",
      "class": "logging.handlers.RotatingFileHandler",
      "filename": "inter_services_request.log",
      "mode": "a",
      "formatter": "detailed",
      "maxBytes": 1000000,
      "backupCount": 10,
    },
    // root logger, that contains all existing logs
    "app": {
        "level": "DEBUG",
        "class": "logging.handlers.RotatingFileHandler",
        "filename": "app.log",
        "mode": "a",
        "formatter": "detailed",
        "maxBytes": 1000000,
        "backupCount": 10,
    },
    "errors": {
      "class": "logging.FileHandler",
      "filename": "errors.log",
      "mode": "a",
      "level": "ERROR",
      "formatter": "detailed"
    },
    // consider your app.name here
    "app_name": {
      "level": "DEBUG",
        "class": "logging.handlers.RotatingFileHandler",
        // and here also
        "filename": "app_name.log",
        "mode": "a",
        "formatter": "detailed",
        "maxBytes": 1000000,
        "backupCount": 10,
    }
  },
  "loggers": {
    "panini": {
      "handlers": [
        "panini"
      ]
    },
    "inter_services_request": {
      "handlers": [
        "inter_services_request"
      ]
    },
    // your app_name is here
    "app_name": {
      "handlers": [
        "app_name"
      ]
    },
  },
  "root": {
    "level": "DEBUG",
    "handlers": [
      "console",
      "errors",
      "app"
    ]
  }
}`
```

Also, you can provide a custom log configuration for advanced logging.
To do that - just create `config/log_config.json` file inside your app root path.
(see [log_config.json.sample](https://github.com/lwinterface/panini/blob/master/examples/simple_examples/config/log_config.json.sample))

*Please notice, that some formatters and loggers will be added to your custom config,
but not overwritten if they exist (such as panini and inter_services_request loggers
and detailed formatter)*

You can also provide some keywords to custom log config file, that will be replaced to
some meaningful data, such as:

```
%MS_NAME% - will be replaced to microservice name (app_name),
%CLIENT_ID% - will be replaced to client_id from os.environ (advanced),
"%DATETIME%": will be replaced as datetime of app start in human readable string format,

```

*Notice, that this keywords works only inside "filename" log configuration*

## Additional logger information:

If you want to be able to log some *extra* parameters, the things should be done as next:

```python
from panini.utils.logger import get_logger

log = get_logger('app')

log.warning('some log', extra_parameter='some extra parameter')
```

That will be logged due to your config (or only in the file, as it is done by default) -
see %(extra)s argument in the default configuration format.

*Notice, that extra parameters will be added to your logs only if you add "%(extra)s" to your log config formatter*