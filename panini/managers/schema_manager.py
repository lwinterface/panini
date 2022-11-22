import ujson
from typing import Callable, Dict, List, Any
from panini.exceptions import MessageSchemaError


class SchemaManager:
    @staticmethod
    def serialize_message(data_type, message: bytes):
        if data_type is bytes:
            return message
        elif data_type is Callable:
            return SchemaManager._bytes_through_callable(data_type, message)
        elif data_type is str:
            return SchemaManager._bytes_to_str(message)
        elif data_type is dict:
            return SchemaManager._bytes_to_dict(data_type, message)
        elif data_type is list:
            return SchemaManager._bytes_to_list(data_type, message)
        else:
            try:
                return SchemaManager._bytes_to_dataclass(data_type, message)
            except TypeError:
                pass
            except Exception as e:
                raise MessageSchemaError(f'Unexpected serialization error: {e}')
        raise MessageSchemaError(f'Unexpected data_type: {data_type}, message: {message}')

    @staticmethod
    def deserialize_message(data_type, message: Any):
        if data_type is bytes:
            return message
        elif data_type is Callable:
            return SchemaManager._something_through_callable_to_bytes(data_type, message)
        elif data_type is str:
            return SchemaManager._str_to_bytes(message)
        elif data_type is dict:
            return SchemaManager._dict_to_bytes(message)
        elif data_type is list:
            return SchemaManager._list_to_bytes(message)
        else:
            try:
                return SchemaManager._dataclass_to_bytes(message)
            except TypeError:
                pass
        raise MessageSchemaError(
            f'Unexpected data_type: {data_type}, message: {message}'
        )

    @staticmethod
    def _bytes_to_dataclass(data_type: Callable, message: bytes):
        data = ujson.loads(message.decode())
        return data_type(**data)

    @staticmethod
    def _dataclass_to_bytes(message) -> bytes:
        """ works only for pydantic dataclasses """
        data = ujson.dumps(message.dict())
        return data.encode()

    @staticmethod
    def _bytes_through_callable(data_type: Callable, message: bytes):
        return data_type(message)

    @staticmethod
    def _something_through_callable_to_bytes(data_type: Callable, message: Any) -> bytes:
        return SchemaManager._bytes_through_callable(data_type, message)

    @staticmethod
    def _bytes_to_str(message: bytes) -> str:
        return message.decode()

    @staticmethod
    def _str_to_bytes(message: str) -> bytes:
        return message.encode()

    @staticmethod
    def _bytes_to_dict(data_type: Dict, message: bytes) -> Dict:
        return SchemaManager._json_loads(data_type, message)

    @staticmethod
    def _dict_to_bytes(message: Dict) -> bytes:
        return SchemaManager._json_dumps(message)

    @staticmethod
    def _bytes_to_list(data_type: List, message: bytes) -> List:
        return SchemaManager._json_loads(data_type, message)

    @staticmethod
    def _list_to_bytes(message: List) -> bytes:
        return SchemaManager._json_dumps(message)

    @staticmethod
    def _json_loads(data_type: Dict or List, message: bytes) -> Dict or List:
        try:
            data = ujson.loads(message.decode())
            assert isinstance(data, data_type)
            return data
        except MessageSchemaError as e:
            raise MessageSchemaError(e)

    @staticmethod
    def _json_dumps(message: Dict or List) -> bytes:
        try:
            return ujson.dumps(message).encode()
        except MessageSchemaError as e:
            raise MessageSchemaError(e)
