from .utils.logger import Logger
from nats.aio.errors import ErrTimeout

app_logger = None


class BaseError(Exception):
    pass


class BaseLoggedError(Exception):
    def __init__(self, error_message="", log_obj=None, exception_obj=None):
        if log_obj is not None:
            if not isinstance(log_obj, Logger):
                print(
                    f"Wrong log_obj for error {error_message}. It has to be Logger instance"
                )
            else:
                log_obj.error(error_message)
        else:
            global app_logger
            if app_logger is None:
                from .app import _app

                app_logger = _app.logger
                app_logger.error(error_message)
            else:
                if not isinstance(app_logger, Logger):
                    print(
                        f"Wrong log_obj for error {error_message}. It has to be Logger instance"
                    )
                else:
                    app_logger.error(error_message)
        if exception_obj:
            raise exception_obj(error_message)
        else:
            raise Exception(error_message)


class InitializingNATSError(BaseError):
    pass


class InitializingLoggerError(BaseError):
    pass


class InitializingEventManagerError(BaseError):
    pass


class InitializingValidatorError(BaseError):
    pass


class InitializingTaskError(BaseError):
    pass


class InitializingIntervalTaskError(BaseError):
    pass


class InitializingMainJobError(BaseError):
    pass


class NotReadyError(BaseError):
    pass


class NATSTimeoutError(ErrTimeout):
    pass


class EventHandlingError(BaseError):
    pass


class PublishError(BaseError):
    pass


class RequestError(BaseError):
    pass


class ValidationError(Exception):
    pass


class DecodeError(BaseError):
    pass
