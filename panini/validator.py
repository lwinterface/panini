import inspect
from .exceptions import ValidationError

_validators = {}
_logger = None


class Validator:
    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        Validator.set_logger()
        cls.retrieve_fields()
        _validators[cls.__name__] = cls

    @staticmethod
    def set_logger():
        global _logger
        if _logger is None:
            from .app import _app

            _logger = _app.logger

    @classmethod
    def retrieve_fields(cls):
        dct = cls.__dict__
        validators = {}
        [
            validators.update({field_name: field_obj})
            for field_name, field_obj in dct.items()
            if not field_name.startswith("__")
        ]
        cls.validators = validators
        [delattr(cls, field_name) for field_name in validators]

    @classmethod
    def validated_message(cls, message):
        if not type(message) in [dict, list]:
            error = "Unexpected message. Accepted dict or list"
            _logger.error(error)
            raise ValidationError(error)
        if type(message) is list:
            if not cls.__many:
                error = (
                    "Unexpected message, expected dict. "
                    "You can set many=True in validator if you need to handle list of dicts"
                )
                _logger.error(error)
                raise ValidationError(error)
            result = []
            for m in message:
                result.append(cls._validate_message(cls, m))
            return result
        message = cls._validate_message(message)
        # print(f'message {message} is OK {cls.validators}')
        return message

    @classmethod
    def _validate_message(cls, message):
        if not type(message) is dict:
            error = "Unexpected message, expected dict"
            _logger.error(error)
            raise ValidationError(error)
        for key, field_obj in cls.validators.items():
            if issubclass(field_obj.type.__base__, Validator):
                field_obj.type.validated_message(message[key])
                continue
            if key not in message and not hasattr(field_obj, "default"):
                error = f'Expected field "{key}" not found'
                _logger.error(error)
                raise ValidationError(error)
            elif key not in message and hasattr(field_obj, "default"):
                message[key] = field_obj.default
            if message[key] is None and field_obj.null is False:
                error = f'Wrong value None for field "{key}" (because null=False)'
                _logger.error(error)
                raise ValidationError(error)
            if field_obj.type is not type(message[key]) and message[key] is not None:
                error = f'Expected {field_obj.type} type of field "{key}" but got {type(message[key])} instead'
                _logger.error(error)
                raise ValidationError(error)
            continue
        return message


class Field:
    def __init__(self, many=False, null=False, **kwargs):
        # todo: check all incoming attrs
        self.__many = many
        kwargs["null"] = null
        self.validate_field(kwargs)
        self.__dict__.update(kwargs)

    @staticmethod
    def validate_field(kwargs):
        if "type" not in kwargs:
            error = "type required in Field"
            _logger.error(error)
            raise ValidationError(error)
        if (
            "default" in kwargs
            and kwargs["default"] is None
            and ("null" not in kwargs or kwargs["null"] is False)
        ):
            error = "You have to set null=True first if you want to set default=None"
            _logger.error(error)
            raise ValidationError(error)
        if (
            "default" in kwargs
            and kwargs["default"] is not None
            and kwargs["type"] is not type(kwargs["default"])
        ):
            error = f'Your default type is {type(kwargs["default"])} but expected {kwargs["type"]}'
            _logger.error(error)
            raise ValidationError(error)
        if not kwargs["type"] in [str, int, float, list, dict]:
            all_classes = inspect.getmro(kwargs["type"])
            if len(all_classes) > 1:
                validator_name = all_classes[0].__name__
                if validator_name not in _validators:
                    error = f"Validator {validator_name} hasn't registered yet. You have to register in first"
                    _logger.error(error)
                    raise ValidationError(error)
                parent_name = all_classes[1].__name__
                if not parent_name == "Validator":
                    error = (
                        'You have to inherit your validator from the class "Validator"'
                    )
                    _logger.error(error)
                    raise ValidationError(error)
            else:
                error = (
                    f'Invalid data type {kwargs["type"]} for field.'
                    f" Only JSON data types or another Validator class allowed"
                )
                _logger.error(error)
                raise ValidationError(error)
