import datetime
import inspect

_serializers = {}

class Serializer:
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls.retrieve_fields()
        cls.validated_serializer = True
        _serializers[cls.__name__] = cls

    @classmethod
    def retrieve_fields(cls):
        dct = cls.__dict__
        serialisers = {}
        [serialisers.update({field_name: field_obj}) for field_name, field_obj in dct.items() if not field_name.startswith('__')]
        cls.serialisers = serialisers
        [delattr(cls, field_name) for field_name in serialisers]

    @classmethod
    def validate_message(cls, message):
        if not type(message) in [dict, list]:
            raise Exception(
                'Unexpected message, expected dict. Accepted dict or list')
        if type(message) is list:
            if not cls.__many:
                raise Exception('Unexpected message, expected dict. You can set many=True in serializer if you need to handle list of dicts')
            for m in message:
                cls._validate_message(cls, m)
            return True
        message = cls._validate_message(message)
        # print(f'message {message} is OK {cls.serialisers}')
        return message

    @classmethod
    def _validate_message(cls, message):
        if not type(message) is dict:
            raise Exception(
                'Unexpected message, expected dict')
        for key, field_obj in cls.serialisers.items():
            if hasattr(field_obj.type, 'validated_serializer') and field_obj.type.validated_serializer is True:
                field_obj.type.validate_message(message[key])
                continue
            if not key in message and not hasattr(field_obj, 'default'):
                raise Exception(
                    f'Expected field "{key}" not found')
            elif not key in message and hasattr(field_obj, 'default'):
                message[key] = field_obj.default
            if message[key] is None and field_obj.null is False:
                raise Exception(
                    f'Wrong value None for field "{key}" (because null=False)')
            if field_obj.type is not type(message[key]) and message[key] is not None:
                raise Exception(
                    f'Expected field "{key}" type is {field_obj.type} but got {type(message[key])}')
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
            raise Exception('type required in Field')
        if 'default' in kwargs and kwargs['default'] is None and (not 'null' in kwargs or kwargs['null'] == False):
            raise Exception('You have to set null=True first if you want to set default=None')
        if 'default' in kwargs and kwargs['default'] is not None and kwargs['type'] is not type(kwargs['default']):
            raise Exception(f'Your default type is {type(kwargs["default"])} but expected {kwargs["type"]}')
        if not kwargs['type'] in [str, int, float, list, dict]:
            all_clss = inspect.getmro(kwargs['type'])
            if len(all_clss) > 1:
                serializator_name = all_clss[0].__name__
                if not serializator_name in _serializers:
                    raise Exception(f"Serializer {serializator_name} hasn't registered yet. You have to register in first")
                parent_name = all_clss[1].__name__
                if not parent_name == 'Serializer':
                    raise Exception('You have to inherit your serializer from the class "Serializer"')
            else:
                raise Exception(f'Invalid data type {kwargs["type"]} for field. Only JSON data types or another Serializer class allowed')
