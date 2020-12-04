import datetime
import json
import logging
import logging.handlers
import logging.config
import os
from multiprocessing import Process, Queue, Event


class Handler:
    @staticmethod
    def handle(record) -> None:
        if record.name == "root":
            logger = logging.getLogger()
        else:
            logger = logging.getLogger(record.name)

        # print(record)
        # print(logger)
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
    self.log_config_file_path: path (relative from root_path) to advanced log config file (ex. log_config.json).
    return: logging object, contain rules for logging.
    """

    def __init__(self, name,
                 log_file: str = None,
                 log_formatter: str = '%(message)s',
                 console_level: int = logging.DEBUG,
                 file_level: int = logging.DEBUG,
                 logging_level: int = logging.DEBUG,
                 root_path: str = None,
                 log_directory: str = None,
                 log_config_file_path: str = None,
                 ):
        self.name = name
        if log_file is not None:
            self.log_file = log_file
        else:
            # if 'CLIENT_ID' in os.environ:
            #     self.log_file = f"{os.environ['CLIENT_ID']}.log"
            #     self.client_id = os.environ['CLIENT_ID']
            # else:
            #     self.log_file = f"{name}.log"
            self.log_file = f"{name}.log"
        if not hasattr(self, 'client_id'):
            self.client_id = name
        self.log_formatter = log_formatter
        self.console_level = console_level
        self.file_level = file_level
        self.logging_level = logging_level
        self.log_directory = log_directory if log_directory is not None else 'logfiles'
        self.log_config_file_path = log_config_file_path
        if root_path is not None:
            self.root_path = root_path
        else:
            self.root_path = '/'

        if self.log_config_file_path is None:
            config = self.create()

        else:
            config = self.configure_logging_with_config_file()

        print(config)
        logging.config.dictConfig(config)

        processes_queue, stop_event, listener_process = self.set_logger_in_separate_process()
        self.logger = self.get_process_logging_config(processes_queue, name)

    def create(self):
        dir_name = f'{self.root_path}{self.log_directory}'
        if dir_name[0] == '/':
            dir_name = dir_name[1:]
        self._create_dir_when_none(dir_name)
        log_file = f'{dir_name}/{self.log_file}'
        logger = logging.getLogger(log_file)
        config = {}
        if not logger.handlers:
            config = {
                'version': 1,
                'disable_existing_loggers': True,
                'formatters': {
                    "default": {
                        "class": "logging.Formatter",
                        "format": self.log_formatter
                    }
                },
                'handlers': {
                    'console': {
                        'level': self.console_level,
                        'formatter': "default",
                        'class': 'logging.StreamHandler',
                        'stream': 'ext://sys.stdout',
                    },
                    'file': {
                        'class': 'logging.handlers.RotatingFileHandler',
                        'maxBytes': 2000000,
                        'backupCount': 20,
                        'filename': log_file,
                        'mode': 'a',
                        'formatter': "default",
                        'level': self.file_level,
                    },
                },
                'root': {
                    'handlers': ['console', 'file'],
                    'level': 'DEBUG'
                }
            }

        return config

    def configure_logging_with_config_file(self) -> dict:
        try:
            default_config_path = os.path.join(self.root_path, self.log_config_file_path)
            with open(default_config_path, mode='r', encoding='utf-8') as f:
                config = json.load(f)

            self._create_dir_when_none(os.path.join(self.root_path, self.log_directory))

            for handler in config['handlers']:
                if handler != 'console' \
                        and self.log_directory not in config['handlers'][handler]['filename']:
                    config['handlers'][handler]['filename'] = (f'{self.root_path}{self.log_directory}/'
                                                               f'{config["handlers"][handler]["filename"]}')

            return config

        except Exception as e:
            logging.exception(f'Error when loading the logging configuration: {e}')
            raise SystemExit()

    @staticmethod
    def _dedicated_listener_process(processes_queue: Queue, stop_event: Event) -> None:
        listener = logging.handlers.QueueListener(processes_queue, Handler())
        listener.start()
        stop_event.wait()
        listener.stop()

    def set_logger_in_separate_process(self) -> (Queue, Event, Process):
        try:
            processes_queue = Queue()
            stop_event = Event()
            listener_process = Process(target=self._dedicated_listener_process,
                                       name='listener',
                                       args=(processes_queue, stop_event,))
            listener_process.start()

            return processes_queue, stop_event, listener_process
        except Exception as e:
            logging.exception(f'Error when loading the logging configuration: {e}')
            raise SystemExit()

    @staticmethod
    def _create_dir_when_none(dir_name: str):
        """Check if a directory exist or create one.
        return: bool."""
        try:
            if dir_name[0] == '/':
                dir_name = dir_name[1:]
            if not os.path.isdir(dir_name):
                os.makedirs(dir_name)
                return False
            else:
                return True
        except OSError as e:
            pass

    @staticmethod
    def get_process_logging_config(processes_queue: Queue, name: str):
        logging.config.dictConfig({
            'version': 1,
            'disable_existing_loggers': True,
            'handlers': {
                'queue': {
                    'class': 'logging.handlers.QueueHandler',
                    'queue': processes_queue
                }
            },
            'root': {
                'handlers': ['queue'],
                'level': 'DEBUG'
            }
        })
        return logging.getLogger(name)

    def log(self, msg, level: str = 'info', from_: str = None, print_: bool = False, **log):
        if from_:
            log['from'] = self.name + '__' + from_
        else:
            log['from'] = self.name
        log['timestamp'] = datetime.datetime.now().timestamp()
        log['msg'] = str(msg)
        log['level'] = level
        log['client_id'] = self.client_id
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


class InterServicesRequestLogger(Logger):
    def __init__(self, name: str,
                 log_file: str = None,
                 log_formatter: str = '%(message)s',
                 console_level: int = logging.DEBUG,
                 file_level: int = logging.DEBUG,
                 logging_level: int = logging.DEBUG,
                 root_path: str = None,
                 separated_file: bool = False,
                 ):
        self.name = name
        if log_file is not None:
            self.log_file = log_file
        else:
            self.log_file = f"inter_services_requests.log"
        if not hasattr(self, 'client_id'):
            self.client_id = name
        self.log_formatter = log_formatter
        self.console_level = console_level
        self.file_level = file_level
        self.logging_level = logging_level
        if root_path is not None:
            self.root_path = root_path
        else:
            self.root_path = '/'
        self.logger = self.create(separate_file=separated_file)

    def isr_log(self, message: str, **kwargs):
        if not 'from_' in kwargs:
            kwargs['from_'] = os.environ['CLIENT_ID']
        self.log(message, **kwargs)
