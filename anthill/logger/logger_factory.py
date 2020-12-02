import json
import logging
import logging.config
import logging.handlers
from multiprocessing import Process, Queue, Event
import threading


import pythonjsonlogger
import anthill.utils.helper as helper
import anthill.logger.logger_config_checkers as check


class Logger:
    def __init__(self, logger):
        self.logger = logger

    def debug(self, message: str) -> None:
        self.logger.log(logging.DEBUG, message)

    def info(self, message: str) -> None:
        self.logger.log(logging.INFO, message)

    def warning(self, message: str) -> None:
        self.logger.log(logging.WARNING, message)

    def error(self, message: str) -> None:
        self.logger.log(logging.ERROR, message)

    def critical(self, message: str) -> None:
        self.logger.log(logging.CRITICAL, message)

    def exception(self, message: str) -> None:
        self.logger.exception(message)

    def ext_debug(self, message: str) -> None:
        self.logger.log(logging.DEBUG, message, extra={"alert_manager": True})

    def ext_info(self, message: str) -> None:
        self.logger.log(logging.INFO, message, extra={"alert_manager": True})

    def ext_warning(self, message: str) -> None:
        self.logger.log(logging.WARNING, message,
                        extra={"alert_manager": True})

    def ext_error(self, message: str) -> None:
        self.logger.log(logging.ERROR, message, extra={"alert_manager": True})

    def ext_critical(self, message: str) -> None:
        self.logger.log(logging.CRITICAL, message,
                        extra={"alert_manager": True})

    def ext_exception(self, message: str) -> None:
        self.logger.exception(message, extra={"alert_manager": True})


class Handler:
    def handle(self, record) -> None:
        if record.name == "root":
            logger = logging.getLogger()
        else:
            logger = logging.getLogger(record.name)

        if logger.isEnabledFor(record.levelno):
            logger.handle(record)


def emergency_logging() -> None:
    logging.basicConfig(
        format='%(asctime)s %(name)s %(levelname)s %(message)s',
        handlers=[logging.FileHandler('logging_error.log', mode='a'),
                  logging.StreamHandler()],
        level=logging.DEBUG)


def configure_logging(root_path: str, new_handlers: dict = None,
    new_formatter: dict = None) -> dict:

    try:
        default_config_path = f'{root_path}logger/log_config.json'
        with open(default_config_path,  mode='r', encoding='utf-8') as f:
            config = json.load(f)

        check.check_logger_config(config)

        if new_formatter:
            formatter_name = next(iter(new_formatter))
            config['formatters'][formatter_name] = \
                check.check_new_formatter(new_formatter[formatter_name])

        if new_handlers:
            formatters_names = check.get_formatters_names(config['formatters'])

            for handler_name in new_handlers:
                config['handlers'].update(check.generate_custom_handler(
                    handler_name, new_handlers[handler_name], formatters_names))

                if handler_name not in config['loggers']:
                    config['loggers'][handler_name] = {
                        'handlers': [handler_name]}

        helper.create_dir_when_none(f'{root_path}logs')

        for handler in config['handlers']:
            if handler != 'console' \
            and 'logs/' not in config['handlers'][handler]['filename']:

                config['handlers'][handler]['filename'] = (f'{root_path}logs/'
                    f'{config["handlers"][handler]["filename"]}')

        return config

    except Exception as e:
        emergency_logging()
        logging.exception('Error when loading the logging configuration')
        raise SystemExit()


def set_simple_logger(root_path: str, new_handlers: dict = None,
    new_formatters: dict = None):

    """For single process application, with multithread or not."""
    config = configure_logging(root_path, new_handlers, new_formatters)
    logging.config.dictConfig(config)


def get_simple_logger(name: str) -> Logger:
    check.check_logger_name(name)
    return Logger(logging.getLogger(name))


def logger_thread(q: Queue) -> None:
    while True:
        record = q.get()
        if record is None:
            break
        logger = logging.getLogger(record.name)
        logger.handle(record)


def set_process_logger_in_separate_thread(root_path: str,
    new_handlers: dict = None,
    new_formatters: dict = None) -> (Queue, threading.Thread):
    """Put the logging system in the main process but in a separate thread."""

    config = configure_logging(root_path, new_handlers, new_formatters)
    logging.config.dictConfig(config)
    processes_queue = Queue()
    listener_thread = threading.Thread(
        target=logger_thread, args=(processes_queue,))
    listener_thread.start()

    return processes_queue, listener_thread


def get_logger_in_process(processes_queue: Queue, name: str,
    root_logging_level: logging = logging.DEBUG) -> Logger:

    check.check_logger_name(name)
    queue_handler = logging.handlers.QueueHandler(processes_queue)
    root = logging.getLogger()
    root.addHandler(queue_handler)

    return Logger(logging.getLogger(name))


def dedicated_listener_process(processes_queue: Queue, stop_event: Event,
    config: dict) -> None:

    logging.config.dictConfig(config)
    listener = logging.handlers.QueueListener(processes_queue, Handler())
    listener.start()
    stop_event.wait()
    listener.stop()


def set_logger_in_separate_process(root_path: str, new_handlers: dict = None,
    new_formatters: dict = None) -> (Queue, Event, Process):

    try:
        config = configure_logging(root_path, new_handlers, new_formatters)
        processes_queue = Queue()
        stop_event = Event()
        listener_process = Process(target=dedicated_listener_process,
                                   name='listener',
                                   args=(processes_queue, stop_event, config,))
        listener_process.start()

        return processes_queue, stop_event, listener_process
    except Exception as e:
        emergency_logging()
        logging.exception('Error when loading the logging configuration')
        raise SystemExit()


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
    return Logger(logging.getLogger(name))
