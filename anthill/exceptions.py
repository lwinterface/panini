from nats.aio.errors import ErrTimeout, NatsError



class BaseError(Exception): pass

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

class SerializationError(BaseError): pass

class DecodeError(BaseError): pass