import json
import os
import sys
from pythonjsonlogger.jsonlogger import JsonFormatter


class CustomLoggerConfigSet:
    @staticmethod
    def _get_app_root_path():
        root_path = os.path.dirname(sys.argv[0])
        return f"{root_path}/" if root_path else ""

    @staticmethod
    def _load_logging_with_custom_config_file(custom_config_path) -> dict:
        with open(custom_config_path, mode='r', encoding='utf8') as f:
            config = json.load(f)
        return config

    @staticmethod
    def _save_logging_with_custom_config_file(custom_config_path, data) -> None:
        with open(custom_config_path, mode='w') as f:
            str_ = json.dumps(data)
            f.write(str_)

    @staticmethod
    def cook_logger_config(filename, static_log_fields):
        CustomJsonFormatter.static_log_fields = static_log_fields
        custom_config_path = os.path.join(CustomLoggerConfigSet._get_app_root_path(), "config", "log_config.json")
        if not os.path.exists(custom_config_path):
            return
        config = CustomLoggerConfigSet._load_logging_with_custom_config_file(custom_config_path)
        if not filename.endswith('.log'):
            filename = f'{filename}.log'
        config['handlers']['app']['filename'] = filename
        config['formatters']['detailed']['class'] = 'app.utils.logging.formatter.CustomJsonFormatter'
        CustomLoggerConfigSet._save_logging_with_custom_config_file(custom_config_path, data=config)


class CustomJsonFormatter(JsonFormatter):
    static_log_fields = {}
    def __init__(self, *args, **kwargs):
        super().__init__(static_fields=CustomJsonFormatter.static_log_fields, *args, **kwargs)