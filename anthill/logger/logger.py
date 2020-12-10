import datetime
import json
import logging
import logging.handlers
import logging.config
import os
from multiprocessing import Process, Queue, Event
from ..utils import helper


class Handler:
    @staticmethod
    def handle(record) -> None:
        if record.name == "root":
            logger = logging.getLogger()
        else:
            logger = logging.getLogger(record.name)

        if logger.isEnabledFor(record.levelno):
            logger.handle(record)


class Logger:
    """Generate logging systems which display any level on the console
    and starting from INFO into logging file
    self.name: string, name of the logger,
    self.log_file: string, name of the file where to place the log datas.
    self.log_formatter: string, how the log is formated. See Formatter logging
        rules.
    self.console_level: logging object, the logging level to display in the
        console. Need to be superior to logging_level.
    self.file_level: logging object, the logging level to put in the
        logging file. Need to be superior to logging_level.
    self.logging_level: logging object, optional, the level of logging to catch.
    self.log_directory: name of directory for storing logs.
    self.log_config_file_path: path (relative from root_path) to advanced log config file (ex. log_config.json.sample).
    self.in_separate_process: Do logging in separate process? (with all pros and cons of that - advanced topic).
    return: logging object, contain rules for logging.
    """

    def __init__(self,
                 name,
                 app_root_path: str = None,
                 in_separate_process: bool = False,
                 ):
        self.name = name
        # TODO: insert client_id here
        self.in_separate_process = in_separate_process
        if app_root_path is not None:
            self.app_root_path = app_root_path
        else:
            self.app_root_path = ''

        self.log_root_path = os.path.join(self.app_root_path, 'logs')
        helper.create_dir_when_none(self.log_root_path)

        custom_config_path = os.path.join(self.app_root_path, 'config', 'log_config.json')
        if os.path.exists(custom_config_path):
            config = self._configure_logging_with_custom_config_file(custom_config_path)

        else:
            config = self._configure_default_logging()

        if self.in_separate_process:
            processes_queue, stop_event, listener_process = self._set_logger_in_separate_process(config)
            self.logger = self._get_process_logging_config(processes_queue, self.name)
        else:
            logging.config.dictConfig(config)
            self.logger = logging.getLogger(self.name)

    def _configure_default_logging(self):
        # TODO: add inter service requests logging configuration
        default_log_config = {
            "version": 1,
            "disable_existing_loggers": True,
            "formatters": {
                "detailed": {
                    "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
                    "format": "%(created)s %(name)s %(levelname)s %(processName)s %(threadName)s %(message)s"
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
                    "filename": os.path.join(self.log_root_path, f"anthill.log"),
                    "mode": "a",
                    "formatter": "detailed",
                    "maxBytes": 1000000,
                    "backupCount": 10,
                },
                self.name: {
                    "level": "DEBUG",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": os.path.join(self.log_root_path, f"{self.name}.log"),
                    "mode": "a",
                    "formatter": "detailed",
                    "maxBytes": 1000000,
                    "backupCount": 10
                },
                "errors": {
                    "class": "logging.FileHandler",
                    "filename": os.path.join(self.log_root_path, f"errors.log"),
                    "mode": "a",
                    "level": "ERROR",
                    "formatter": "detailed"
                }
            },
            "loggers": {
                self.name: {
                    "handlers": [self.name]
                },
                "anthill": {
                    "handlers": ["anthill"]
                }
            },
            "root": {
                "level": "DEBUG",
                "handlers": ["console", "errors"]
            }
        }

        return default_log_config

    def _emergency_logging(self) -> None:
        logging.basicConfig(
            format='%(asctime)s %(name)s %(levelname)s %(message)s',
            handlers=[logging.FileHandler(os.path.join(self.log_root_path, 'logging_error.log'), mode='a'),
                      logging.StreamHandler()],
            level=logging.DEBUG)

    def _modify_custom_config(self, config):
        for handler in config['handlers']:
            if handler == 'console':
                continue

            if not os.path.isabs(config['handlers'][handler]['filename']):
                config['handlers'][handler]['filename'] = os.path.join(self.log_root_path,
                                                                       config['handlers'][handler]['filename'])

            # TODO: add here parsing with regex and selecting phrases as % or $MS_NAME and % or $CLIENT_ID..

    def _configure_logging_with_custom_config_file(self, custom_config_path) -> dict:
        try:
            with open(custom_config_path, mode='r', encoding='utf-8') as f:
                config = json.load(f)

                self._modify_custom_config(config)

            return config

        except Exception as e:
            self._emergency_logging()
            logging.exception(f'Error when loading the logging configuration: {e}')
            raise SystemExit()

    @staticmethod
    def _dedicated_listener_process(processes_queue: Queue, stop_event: Event, config: dict) -> None:
        logging.config.dictConfig(config)
        listener = logging.handlers.QueueListener(processes_queue, Handler())
        listener.start()
        stop_event.wait()
        listener.stop()

    def _set_logger_in_separate_process(self, config: dict) -> (Queue, Event, Process):
        try:
            processes_queue = Queue()
            stop_event = Event()
            listener_process = Process(target=self._dedicated_listener_process,
                                       name='listener',
                                       args=(processes_queue, stop_event, config))
            listener_process.start()

            return processes_queue, stop_event, listener_process

        except Exception as e:
            self._emergency_logging()
            logging.exception(f'Error when loading the logging configuration: {e}')
            raise SystemExit()

    @staticmethod
    def _get_process_logging_config(processes_queue: Queue, name: str):
        config = {
            'version': 1,
            'disable_existing_loggers': True,
            'handlers': {
                'queue': {
                    'class': 'logging.handlers.QueueHandler',
                    'queue': processes_queue
                }
            },
            "root": {
                'handlers': ['queue'],
            }
        }
        logging.config.dictConfig(config)
        return logging.getLogger(name)

    def log(self, msg, level: str = 'info', from_: str = None, print_: bool = False, **log):
        if from_:
            log['from'] = self.name + '__' + from_
        else:
            log['from'] = self.name
        log['timestamp'] = datetime.datetime.now().timestamp()
        log['msg'] = str(msg)
        log['level'] = level
        if level == 'warning':
            self.logger.warning(log)
        elif level == 'error':
            self.logger.error(log)
        elif level == 'debug' or level == 'dev':
            self.logger.debug(log)
        elif level == 'critical':
            self.logger.critical(log)
        elif level == 'exception':
            self.logger.exception(log)
        else:
            self.logger.info(log)
        if print_:
            print(msg)
