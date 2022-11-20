import nats
from .utils.logger import Logger

app_logger = None


class BaseError(Exception):
    pass


class CriticalError(SystemExit):

    def __init__(self, *args):
        super().__init__(*args)


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


class NATSTimeoutError(nats.errors.TimeoutError):
    pass


class EventHandlingError(BaseError):
    pass


class PublishError(BaseError):
    pass


class RequestError(BaseError):
    pass


class SubscribeError(BaseError):
    pass


class UnsubscribeError(BaseError):
    pass


class ValidationError(Exception):
    pass


class MessageSchemaError(Exception):
    pass


class DecodeError(BaseError):
    pass


class DataTypeError(BaseError):
    pass


class TestClientError(BaseError):
    pass


class JetStreamNotEnabledError(BaseError):
    pass



