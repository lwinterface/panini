import json
import logging
import logging.handlers
import logging.config
import os
import datetime
from multiprocessing import Process, Queue, Event


from ..utils import helper


# Decorator for check, if logger exist
def check_logger(func):
    def wrapper(self, msg, **extra):
        if self.logger is None:
            raise Exception("Logger hasn't been connected")
        else:
            func(self, msg, **extra)

    return wrapper


class Logger:
    """Generate logging systems which can be simply customized by adding config/log_config.json file to app_root_path
    self.logger - use built in logging system but with improved interface for logging
    """

    def __init__(self, logger: logging.Logger):
        self.logger = logger

    @check_logger
    def debug(self, msg, **extra):
        self.logger.debug(msg, extra={"extra": extra})

    @check_logger
    def info(self, msg, **extra):
        self.logger.info(msg, extra={"extra": extra})

    @check_logger
    def warning(self, msg, **extra):
        self.logger.warning(msg, extra={"extra": extra})

    @check_logger
    def error(self, msg, **extra):
        self.logger.error(msg, extra={"extra": extra})

    @check_logger
    def exception(self, msg, **extra):
        self.logger.exception(msg, extra={"extra": extra})


def set_logger(
    ms_name: str,
    app_root_path: str,
    logger_files_path: str,
    in_separate_process: bool,
    client_id: str = None,
):
    logger_config = _get_logger_config(
        app_root_path, logger_files_path, ms_name, client_id
    )

    if in_separate_process:
        (
            logger_queue,
            log_stop_event,
            log_process,
            change_log_config_listener_queue,
        ) = _set_log_recorder_process(logger_config)
        _set_main_logging_config(logger_queue)
        return (
            logger_queue,
            log_stop_event,
            log_process,
            change_log_config_listener_queue,
        )
    else:
        logging.config.dictConfig(logger_config)
        return


def get_logger(name) -> Logger:
    return Logger(logging.getLogger(name))


def _get_logger_config(
    app_root_path: str, logger_files_path: str, ms_name: str, client_id: str = None
):
    if os.path.isabs(logger_files_path):
        log_dir_path = logger_files_path
    else:
        log_dir_path = os.path.join(app_root_path, logger_files_path)
    custom_config_path = os.path.join(app_root_path, "config", "log_config.json")
    if os.path.exists(custom_config_path):
        config = _configure_logging_with_custom_config_file(custom_config_path)

    else:
        config = _configure_default_logging(ms_name)
    config["handlers"] = _modify_handlers(
        config["handlers"], log_dir_path, ms_name=ms_name, client_id=client_id
    )
    return config


def _replace_keywords(filename: str, ms_name: str = None, client_id: str = None):
    """replace keywords with some meaningful data"""
    keywords = {
        "%MS_NAME%": ms_name,
        "%CLIENT_ID%": client_id,
        "%DATETIME%": str(datetime.datetime.now()),
    }
    for keyword, meaningful_data in keywords.items():
        filename = filename.replace(keyword, meaningful_data)

    return filename


def _modify_handlers(
    handlers, log_dir_path, ms_name: str = None, client_id: str = None
):
    for handler in handlers:
        if handler == "console":
            continue

        filename = _replace_keywords(handlers[handler]["filename"], ms_name, client_id)

        if not os.path.isabs(filename):
            filename = os.path.join(log_dir_path, filename)

        helper.create_dir_when_none(os.path.dirname(filename))
        handlers[handler]["filename"] = filename

    return handlers


def _basic_file_handler_skeleton(name: str, level="DEBUG", formatter="detailed"):
    return {
        "level": level,
        "class": "logging.handlers.RotatingFileHandler",
        "filename": f"{name}.log",
        "mode": "a",
        "formatter": formatter,
        "maxBytes": 1000000,
        "backupCount": 10,
    }


def _configure_default_logging(name):
    default_log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "detailed": {
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                # do not remove 'extra' field - that's for extra arguments logging
                "format": "%(created)f %(name)s %(levelname)s %(processName)s %(threadName)s %(message)s %(extra)s",
            },
            "simple": {
                "class": "logging.Formatter",
                "format": "%(asctime)s %(name)-15s %(levelname)-8s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "WARNING",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            },
            "panini": _basic_file_handler_skeleton("panini"),
            "inter_services_request": _basic_file_handler_skeleton(
                "inter_services_request"
            ),
            "app": _basic_file_handler_skeleton("app"),
            "errors": {
                "class": "logging.FileHandler",
                "filename": f"errors.log",
                "mode": "a",
                "level": "ERROR",
                "formatter": "detailed",
            },
        },
        "loggers": {
            "panini": {"handlers": ["panini"]},
            "inter_services_request": {"handlers": ["inter_services_request"]},
        },
        "root": {"level": "DEBUG", "handlers": ["console", "errors", "app"]},
    }
    if name not in ("panini", "inter_services_request"):
        default_log_config["handlers"][name] = _basic_file_handler_skeleton(name)

        default_log_config["loggers"][name] = {"handlers": [name]}

    return default_log_config


def _configure_logging_with_custom_config_file(custom_config_path) -> dict:
    try:
        with open(custom_config_path, mode="r", encoding="utf-8") as f:
            config = json.load(f)

        if "detailed" not in config["formatters"]:
            config["formatters"]["detailed"] = {
                "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(created)s %(name)s %(levelname)s %(processName)s %(threadName)s %(message)s %(extra)s",
            }
        for basic_config in ("panini", "inter_services_request"):
            if basic_config not in config["handlers"]:
                config["handlers"][basic_config] = _basic_file_handler_skeleton(
                    basic_config
                )
                config["loggers"][basic_config] = {"handlers": [basic_config]}

        return config

    except Exception as e:
        _emergency_logging()
        logging.exception(f"Error when loading the logging configuration: {e}")
        raise SystemExit()


class LogHandler:
    @staticmethod
    def handle(record) -> None:
        if record.name == "root":
            logger = logging.getLogger()
        else:
            logger = logging.getLogger(record.name)

        if logger.isEnabledFor(record.levelno):
            logger.handle(record)


class ChangeConfigHandler:
    @staticmethod
    def handle(record) -> None:
        print(record)
        # TODO: implement changing logger configuration during runtime


def _emergency_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler("logging_error.log", mode="a"),
            logging.StreamHandler(),
        ],
        level=logging.DEBUG,
    )


def _dedicated_listener_process(
    log_listener_queue: Queue,
    stop_event: Event,
    config: dict,
    change_config_listener_queue: Queue,
) -> None:
    logging.config.dictConfig(config)
    log_listener = logging.handlers.QueueListener(log_listener_queue, LogHandler())
    change_log_config_listener = logging.handlers.QueueListener(
        change_config_listener_queue, ChangeConfigHandler()
    )
    change_log_config_listener.start()
    log_listener.start()
    stop_event.wait()
    log_listener.stop()
    change_log_config_listener.stop()


def _set_log_recorder_process(config: dict) -> (Queue, Event, Process, Queue):
    try:
        log_listener_queue = Queue()
        change_log_config_listener_queue = Queue()
        stop_event = Event()
        listener_process = Process(
            target=_dedicated_listener_process,
            name="listener",
            args=(
                log_listener_queue,
                stop_event,
                config,
                change_log_config_listener_queue,
            ),
        )
        listener_process.start()
        return (
            log_listener_queue,
            stop_event,
            listener_process,
            change_log_config_listener_queue,
        )

    except Exception as e:
        _emergency_logging()
        logging.exception(f"Error when loading the logging configuration: {e}")
        raise SystemExit()


def _set_main_logging_config(log_listener_queue: Queue):
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "queue": {
                "class": "logging.handlers.QueueHandler",
                "queue": log_listener_queue,
            }
        },
        "root": {
            "level": "DEBUG",
            "handlers": ["queue"],
        },
    }
    logging.config.dictConfig(config)
