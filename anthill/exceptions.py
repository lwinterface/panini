from .logger.logger import Logger
from nats.aio.errors import ErrTimeout, NatsError

app_logger = None

class BaseError(Exception): pass

class BaseLoggedError(Exception):
    def __init__(self, error_message='', log_obj=None, exception_obj=None):
        if log_obj is not None:
            if not isinstance(log_obj, Logger):
                print(f'Wrong log_obj for error {error_message}. It has to be Logger instance')
            else:
                log_obj.log(error_message, level='error')
        else:
            global app_logger
            if app_logger is None:
                from .app import _app
                app_logger = _app.logger
                app_logger.log(error_message, level='error')
            else:
                if not isinstance(app_logger, Logger):
                    print(f'Wrong log_obj for error {error_message}. It has to be Logger instance')
                else:
                    log(error_message, level='error')
        if exception_obj:
            raise exception_obj(error_message)
        else:
            raise Exception(error_message)

class InitializingNATSError(BaseError): pass

class InitializingLoggerError(BaseError): pass

class InitializingEventManagerError(BaseError): pass

class InitializingSerializerError(BaseError): pass

class InitializingTaskError(BaseError): pass

class InitializingIntevalTaskError(BaseError): pass

class InitializingMainJobError(BaseError): pass

class NotReadyError(BaseError): pass

class NATSTimeoutError(ErrTimeout): pass

class EventHandlingError(BaseError): pass

class PublishError(BaseError): pass

class RequestError(BaseError): pass

class SerializationError(Exception): pass

class DecodeError(BaseError): pass