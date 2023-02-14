# What is the Panini Internal Logger?

The Panini internal logger is a default Python logger with some settings that the Panini team found convenient. If you are using your own logging style, you can skip this section.

The logger has two important parameters:

- <span class="red">logger_files_path</span> - the path to the log folder - it can be absolute or relative (relating to the app root path). For example:

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

- <span class="red">in_separate_process</span> - this parameter specifies whether you want the logger to run in a separate process or not. By default it is set to `False` which is more intuitive, but if you need more efficient logging, it can be set to `True`:

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

# Log Config

The logger uses a simple default config that fits most logger needs:

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

If you need advanced logging, you can provide a custom log configuration. To do that, create a `config/log_config.json` file inside your app root path. (See [log_config.json.sample](https://github.com/lwinterface/panini/blob/master/examples/simple_examples/config/log_config.json.sample) for an example.)

**Please note that some formatters and loggers will be added to your custom config, but not overwritten if they exist.**

You can also provide some keywords to the custom log config file that will be replaced by some meaningful data. These keywords are `%MS_NAME%`, which will be replaced with the microservice name (app_name), `%CLIENT_ID%`, which will be replaced with the client_id from os.environ (advanced), and `%DATETIME%`, which will be replaced with the datetime of the app start in a human-readable string format.

**Note that these keywords only work inside the "filename" log configuration.**

## Additional Logger Settings

If you want to be able to log some *extra* parameters, you can do this by using the `get_logger` utility:

```python
from panini.utils.logger import get_logger

log = get_logger('app')

log.warning('some log', extra_parameter='some extra parameter')
```

These extra parameters will be logged with each log - see %(extra)s argument in the default configuration format.

**Note that extra parameters will be added to your logs only if you add "%(extra)s" to your log config formatter.**