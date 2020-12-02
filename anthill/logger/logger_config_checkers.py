from copy import deepcopy
import re


LOGGER_CONFIG_BASE = ['version', 'formatters', 'handlers', 'root']

FORMATTERS_CLASS = ['logging.Formatter',
                    'pythonjsonlogger.jsonlogger.JsonFormatter']

LOGGER_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']

FILE_HANDLER_TEMPLATE = {
    "class": "logging.handlers.RotatingFileHandler",
    "level": "WARNING",
    "filename": "",
    "mode": "a",
    "formatter": "",
    "maxBytes": 1000000,
    "backupCount": 10
}


"""The following pattern are not researched (and will cause an error):
%(created)f, %(lineno)d, %(msecs)d, %(process)d, %(relativeCreated)d,
%(thread)d"""
NORMAL_PATTERN = re.compile(r"""
^(%\((
asctime|
filename|
funcName|
levelname|
levelno|
module|
message|
name|
pathname|
processName|
threadName)\)
(-{1,3}\d)?
s
[:-]?
\s?)""", re.VERBOSE)

JSON_FORMAT = re.compile(r"""
^(%\((
asctime|
filename|
funcName|
levelname|
levelno|
module|
message|
name|
pathname|
processName|
threadName)\)
s\s?)
*$""", re.VERBOSE)



class LoggerConfigMalformation(Exception):
    """When the data received is not what is expected"""

    def __init__(self, err):
        pass


def check_logger_config(config: dict) -> list:
    optional_loggers = check_main_structure(config)
    formatters = check_formatters(config['formatters'])
    custom_handlers = check_handlers(config['handlers'], formatters)

    if optional_loggers:
        for custom_handler in config['loggers']:
            check_optional_logger(
                config['loggers'][custom_handler], custom_handlers)

    return custom_handlers


def check_main_structure(config: dict) -> bool:
    optional_loggers = False
    for base_config_name in LOGGER_CONFIG_BASE:
        if base_config_name not in config:
            raise LoggerConfigMalformation(f'{base_config_name} is not in '
                'your logger configuration!')

    if not isinstance(config['version'], int):
        raise LoggerConfigMalformation('config version is not an integer: '
            f'{config["version"]}')

    if 'loggers' in config:
        optional_loggers = True

    if 'disable_existing_loggers' in config:
        if not isinstance(config['disable_existing_loggers'], bool):
            raise LoggerConfigMalformation('config disable_existing_loggers '
                f'is not an boolean: {config["disable_existing_loggers"]}')

    return optional_loggers


def check_formatters(formatters: dict) -> list:
    for formatter in formatters:
        check_formatter_structure(formatters[formatter])
        check_formatter_format(formatters[formatter])

    return get_formatters_names(formatters)


def check_formatter_structure(formatter: dict) -> None:
    for formatter_item in ['class', 'format']:
        if formatter_item not in formatter:
            raise LoggerConfigMalformation(f'{formatter_item} is not in your '
                f'formatters: {formatter}!')

        if not isinstance(formatter[formatter_item], str):
            raise LoggerConfigMalformation(f'{formatter_item} is not a string'
                f': {formatter[formatter_item]}')

    # if formatter['class'] not in FORMATTERS_CLASS:
    #     raise LoggerConfigMalformation('Wrong class for your formatters '
    #         f'{formatter}: {formatters[formatter]["class"]} !')


def check_formatter_format(formatter: dict) -> None:
    if formatter['class'] == FORMATTERS_CLASS[0]:
        check_normal_format(formatter["format"])

    else:
        check_json_format(formatter['format'])


def check_normal_format(formatter: str) -> None:
    if not re.match(NORMAL_PATTERN, formatter):
        raise LoggerConfigMalformation(f'Wrong format for your formatters: '
            f'{formatter} !')


def check_json_format(formatter: str) -> None:
    if not re.match(JSON_FORMAT, formatter):
        raise LoggerConfigMalformation('Wrong format for your formatters: '
            f'{formatter} !')


def get_formatters_names(formatters: dict) -> list:
    formatters_names = []

    for formatter_name in formatters:
        formatters_names.append(formatter_name)

    return formatters_names


def check_handlers(handlers: dict, formatters: list) -> list:
    base_handlers = ['console', 'file', 'errors']
    custom_handlers = []

    for handler_name in handlers:
        if handler_name not in base_handlers:
            custom_handlers.append(handler_name)

    handlers_names = custom_handlers + base_handlers

    for handler_name in handlers_names:
        check_handler_structure(
            handler_name, handlers[handler_name], formatters)
        check_handler_parameters(
            handler_name, handlers[handler_name], formatters)

    return custom_handlers


def check_handler_structure(handler_name: str, handler: dict,
    formatters: list) -> None:

    for param_name in handler:
        if param_name in ['class', 'formatter', 'filename']:
            continue

        elif handler_name != 'errors' \
        and param_name in ['maxBytes', 'backupCount']:
            continue

        elif handler_name != 'console' and param_name in ['mode', 'filename']:
            continue

        elif 'level' in handler:
            continue

        else:
            raise LoggerConfigMalformation(f'{param_name} is not in your '
                f'{handler} handler!')

        check_handler_param_type(param_name, handler[param_name])


def check_handler_param_type(param_name: str, handler_param: dict) -> None:
    if param_name not in ['maxBytes', 'backupCount']:
        if not isinstance(handler_param, str):
            raise LoggerConfigMalformation(f'{param_name} is not a string: '
                f'{handler_param}')

    else:
        if not isinstance(handler_param, int):
            raise LoggerConfigMalformation(f'{param_name} is not an integer: '
                f'{handler_param}')


def check_handler_parameters(handler_name: str, handler: dict,
    formatters: list) -> None:

    check_handler_class(handler_name, handler)

    if handler['formatter'] not in formatters:
        raise LoggerConfigMalformation(f'{handler["formatter"]} of '
            f'{handler_name} is unknown!')

    if 'level' in handler and handler['level'] not in LOGGER_LEVELS:
        raise LoggerConfigMalformation(f'{handler["level"]} of {handler_name} '
            'is unknown!')

    if handler_name == 'console' and handler['stream'] != 'ext://sys.stdout':
        raise LoggerConfigMalformation(f'{handler["stream"]} of {handler_name}'
            ' is not set correctly')

    if handler_name != 'console' and handler['mode'] != 'a':
        raise LoggerConfigMalformation(f'{handler["mode"]} of {handler_name} '
            'is not set correctly')

    if handler['class'] == 'logging.handlers.RotatingFileHandler':
        if handler['maxBytes'] < 100000:
            raise LoggerConfigMalformation(f'{handler["maxBytes"]} of '
                f'{handler_name} is too small')

        if handler['backupCount'] < 10:
            raise LoggerConfigMalformation(f'{handler["backupCount"]} of '
                f'{handler_name} is too small')


def check_handler_class(handler_name: str, handler: dict) -> None:
    if handler_name not in ['console', 'error'] \
    and (handler["class"] == 'logging.handlers.RotatingFileHandler'
    or handler["class"] == 'logging.FileHandler'):
        pass

    elif handler_name == 'errors' \
    and handler["class"] == 'logging.FileHandler':
        pass

    elif handler_name == 'console' \
    and handler["class"] == 'logging.StreamHandler':
        pass

    else:
        raise LoggerConfigMalformation(f'{handler["class"]} of {handler_name} '
            f'is not set correctly: {handler}')


def check_optional_logger(logger: dict, custom_handlers: str) -> None:
    if len(logger) != 1:
        raise LoggerConfigMalformation('logger should have only one '
            f'parameter: {logger}')

    if next(iter(logger)) != 'handlers':
        raise LoggerConfigMalformation('logger should have only handlers as '
            f'parameter: {logger}')

    for handler_name in logger['handlers']:
        if handler_name not in custom_handlers:
            raise LoggerConfigMalformation(f'{handler_name} do not have a '
                f'custom handlers associated: {logger}')


def check_new_formatter(formatter: dict) -> dict:
    check_formatter_structure(formatter)
    check_formatter_format(formatter)

    return formatter


def check_custom_handler_parameter(custom_handler: dict,
    formatters_names: list) -> None:

    if next(iter(custom_handler)).lower() == 'root':
        raise LoggerConfigMalformation('Handler name can\'t be root')

    for param_name in custom_handler:
        if param_name not in ['filename', 'formatter', 'level']:
            raise LoggerConfigMalformation(f'{param_name} should not exist.')

        if not isinstance(custom_handler[param_name], str):
            raise LoggerConfigMalformation('Parameter '
                f'{custom_handler[param_name]} is not a string.')

    if custom_handler['formatter'] not in formatters_names:
        raise LoggerConfigMalformation('Formatter '
            f'{custom_handler["formatter"]} not in {formatters_names}')

    if 'level' in custom_handler \
    and custom_handler['level'] not in LOGGER_LEVELS:

        raise LoggerConfigMalformation(f'Level {custom_handler["level"]} '
            f'not in {LOGGER_LEVELS}')


def generate_custom_handler(handler_name: str, custom_handler: dict,
    formatters_names: list) -> dict:

    check_custom_handler_parameter(custom_handler, formatters_names)
    new_handler = deepcopy(FILE_HANDLER_TEMPLATE)

    if new_handler['filename']:
        new_handler['filename'] = {custom_handler['filename']}
    else:
        new_handler['filename'] = f'{handler_name}.log'

    new_handler['formatter'] = custom_handler['formatter']
    if 'level' in custom_handler:
        new_handler['level'] = custom_handler['level']

    return {handler_name: new_handler}


def check_logger_name(name: str) -> None:
    if not isinstance(name, str):
        raise LoggerConfigMalformation('Your logger name is not a string: '
            f'type({name}) ==  {type(name)}')
