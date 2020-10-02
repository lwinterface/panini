import datetime
import inspect
from .exceptions import SerializationError


_serializers = {}
_logger = None

class Serializer:
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Serializer.set_logger()
        cls.retrieve_fields()
        # cls.validated_serializer = True
        _serializers[cls.__name__] = cls

    @staticmethod
    def set_logger():
        global _logger
        if _logger is None:
            from .app import _app
            _logger = _app.logger

    @classmethod
    def retrieve_fields(cls):
        dct = cls.__dict__
        serialisers = {}
        [serialisers.update({field_name: field_obj}) for field_name, field_obj in dct.items() if not field_name.startswith('__')]
        cls.serialisers = serialisers
        [delattr(cls, field_name) for field_name in serialisers]

    @classmethod
    def validated_message(cls, message):
        if not type(message) in [dict, list]:
            error = 'Unexpected message. Accepted dict or list'
            _logger.log(error, level='error')
            raise SerializationError(error)
        if type(message) is list:
            if not cls.__many:
                error = 'Unexpected message, expected dict. You can set many=True in serializer if you need to handle list of dicts'
                _logger.log(error, level='error')
                raise SerializationError(error)
            result = []
            for m in message:
                result.append(cls._validate_message(cls, m))
            return result
        message = cls._validate_message(message)
        # print(f'message {message} is OK {cls.serialisers}')
        return message

    @classmethod
    def _validate_message(cls, message):
        if not type(message) is dict:
            error = 'Unexpected message, expected dict'
            _logger.log(error, level='error')
            raise SerializationError(error)
        for key, field_obj in cls.serialisers.items():
            if issubclass(field_obj.type.__base__, Serializer):
                field_obj.type.validated_message(message[key])
                continue
            if not key in message and not hasattr(field_obj, 'default'):
                error = f'Expected field "{key}" not found'
                _logger.log(error, level='error')
                raise SerializationError(error)
            elif not key in message and hasattr(field_obj, 'default'):
                message[key] = field_obj.default
            if message[key] is None and field_obj.null is False:
                error = f'Wrong value None for field "{key}" (because null=False)'
                _logger.log(error, level='error')
                raise SerializationError(error)
            if field_obj.type is not type(message[key]) and message[key] is not None:
                error = f'Expected {field_obj.type} type of field "{key}" but got {type(message[key])} instead'
                _logger.log(error, level='error')
                raise SerializationError(error)
            continue
        return message



class Field:
    def __init__(self, many=False, null=False, **kwargs):
        #todo: check all incoming attrs
        self.__many = many
        kwargs['null'] = null
        self.validate_field(kwargs)
        self.__dict__.update(kwargs)

    def validate_field(self, kwargs):
        if not 'type' in kwargs:
            error = 'type required in Field'
            _logger.log(error, level='error')
            raise SerializationError(error)
        if 'default' in kwargs and kwargs['default'] is None and (not 'null' in kwargs or kwargs['null'] == False):
            error = 'You have to set null=True first if you want to set default=None'
            _logger.log(error, level='error')
            raise SerializationError(error)
        if 'default' in kwargs and kwargs['default'] is not None and kwargs['type'] is not type(kwargs['default']):
            error = f'Your default type is {type(kwargs["default"])} but expected {kwargs["type"]}'
            _logger.log(error, level='error')
            raise SerializationError(error)
        if not kwargs['type'] in [str, int, float, list, dict]:
            all_clss = inspect.getmro(kwargs['type'])
            if len(all_clss) > 1:
                serializator_name = all_clss[0].__name__
                if not serializator_name in _serializers:
                    error = f"Serializer {serializator_name} hasn't registered yet. You have to register in first"
                    _logger.log(error, level='error')
                    raise SerializationError(error)
                parent_name = all_clss[1].__name__
                if not parent_name == 'Serializer':
                    error = 'You have to inherit your serializer from the class "Serializer"'
                    _logger.log(error, level='error')
                    raise SerializationError(error)
            else:
                error = f'Invalid data type {kwargs["type"]} for field. Only JSON data types or another Serializer class allowed'
                _logger.log(error, level='error')
                raise SerializationError(error)
