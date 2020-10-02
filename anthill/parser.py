import json
from .utils.helper import is_json
from .logger.logger import Logger


log = Logger(name='service_core_parsers').log


def parse_dataprovider_streams_event(topic, message):
    try:
        if is_json(message):
            message = json.loads(message)
        if not 'success' in message or not message['success'] is True:
            raise Exception(f'Error message from dataprovider, topic {topic}')
        exchange = message.get('exchange', None).lower()
        account = message.get('account', None)
        message = message['data']
        topic_splitted = topic.split('.')
        if not topic_splitted[3] in ['-', '*']:
            message['pair'] = topic_splitted[3]
        if 'exchange' in message:
            exchange = message.pop('exchange').lower()
        elif exchange is None:
            exchange = topic_splitted[2].lower()
        return exchange, account, message
    except Exception as e:
        error = f'parse_request error: {str(e)}, topic: {topic}'
        log(error, level='error')
        raise Exception(error)
