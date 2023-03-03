log_config = {
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "class": "utils.logging.formatter.CustomJsonFormatter",
            "format": "%(created)f %(name)s %(levelname)s %(processName)s %(threadName)s %(message)s"
        },
        "simple": {
            "class": "logging.Formatter",
            "format": "%(asctime)s %(name)-15s %(levelname)-8s %(message)s"
        }
    },
    "handlers": {
        "app": {
            "backupCount": 10,
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/app/logs/app.log",
            "formatter": "detailed",
            "level": "DEBUG",
            "maxBytes": 1000000,
            "mode": "a"
        },
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
            "level": "INFO",
            "stream": "ext://sys.stdout"
        },
        "errors": {
            "class": "logging.FileHandler",
            "filename": "/app/logs/errors.log",
            "formatter": "detailed",
            "level": "ERROR",
            "mode": "a"
        },
        "loki": {
            "class": "utils.logging.loki_logger.Logger",
            "formatter": "detailed",
            "level": "INFO",
            "stream": "http://loki:3100/loki/api/v1/push",
            "tags": {}
        }
    },
    "loggers": {},
    "root": {
        "handlers": [
            "console",
            "errors",
            "app",
            "loki"
        ],
        "level": "DEBUG"
    },
    "version": 1
}