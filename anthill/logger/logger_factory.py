import os
import logging
from multiprocessing import Process, Queue, Event


class Handler:
    @staticmethod
    def handle(record) -> None:
        if record.name == "root":
            logger = logging.getLogger()
        else:
            logger = logging.getLogger(record.name)

        if logger.isEnabledFor(record.levelno):
            logger.handle(record)


def _emergency_logging() -> None:
    logging.basicConfig(
        format='%(asctime)s %(name)s %(levelname)s %(message)s',
        handlers=[logging.FileHandler(os.path.join(self.log_root_path, 'logging_error.log'), mode='a'),
                  logging.StreamHandler()],
        level=logging.DEBUG)


def _dedicated_listener_process(processes_queue: Queue, stop_event: Event, config: dict) -> None:
    logging.config.dictConfig(config)
    listener = logging.handlers.QueueListener(processes_queue, Handler())
    listener.start()
    stop_event.wait()
    listener.stop()


def _set_log_recorder_process(config: dict) -> (Queue, Event, Process):
    try:
        log_listener_queue = Queue()
        stop_event = Event()
        listener_process = Process(target=_dedicated_listener_process,
                                   name='listener',
                                   args=(log_listener_queue, stop_event, config,))
        listener_process.start()
        return log_listener_queue, stop_event, listener_process

    except Exception as e:
        _emergency_logging()
        logging.exception(f'Error when loading the logging configuration: {e}')
        raise SystemExit()


def _set_main_logging_config(processes_queue: Queue):
    config = {
        'version': 1,
        'disable_existing_loggers': False,
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
