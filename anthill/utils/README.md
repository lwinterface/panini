# Logger:

Logger has 2 important parameters:
- logfiles_path - the path to the log folder - can be absolute or relative (will relate to the app root path):
  
```python
from anthill import app as ant_app

app = ant_app.App(  
    service_name='ms_template_sync_by_lib',
    host='127.0.0.1',
    port=4222,
    app_strategy='sync',
    logfiles_path='some/relative/path',  # put here absolute or relative path
)

log = app.logger

log.info("some log")  # write log

```
- in_separate_process - specify, if you want logger to be as separate process or to log in main process:
```python
from anthill import app as ant_app

app = ant_app.App(  
    service_name='ms_template_sync_by_lib',
    host='127.0.0.1',
    port=4222,
    app_strategy='sync',
    log_in_separate_process=True,  #  by default and more efficient
    # log_in_separate_process=False  # less efficient but more intuitive
)

log = app.logger

log.info("some log")  # write log

```

# Log Config:

In the logger we use simple default config, that fit majority of logger needs:
```json5
{
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
      "level": "WARNING",
      "formatter": "simple",
      "stream": "ext://sys.stdout"
    },
    "anthill": {
        "level": "DEBUG",
        "class": "logging.handlers.RotatingFileHandler",
        "filename": "anthill.log",
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
    "anthill": {
      "handlers": [
        "anthill"
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
}
```

Also, you can provide custom log configuration for advanced logging.
To do that - just create `config/log_config.json` file inside your app root path.
(see [log_config.json.sample](../../examples/simple_examples/config/log_config.json.sample))

*Please notice, that some formatters and loggers will be added to your custom config,
but not overwritten if they exist (such as anthill and inter_services_request loggers
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
from anthill.utils.logger import get_logger

log = get_logger('app')

log.warning('some log', extra_parameter='some extra parameter')
```
That will be logged due to your config (or only in the file, as it is done by default) -
see %(extra)s argument in the default configuration format. 

*Notice, that extra parameters will be added to your logs only if you add "%(extra)s" to your log config formatter*

# TODO:

- Add ability to change log configuration during runtime (ChangeLogConfigHandler, change_log_config)
- Add logger config checkers