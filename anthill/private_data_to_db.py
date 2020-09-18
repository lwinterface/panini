import time
import json
import random
import asyncio
from config import msgr_config
from queue import Empty
from logger.logger import Logger





class SendManager:
    topic_map = {
        'order':'*.private_data_update.-.-.create_or_update.order',
        'cancel_order':'*.private_data_update.-.-.create_or_update.cancel_order',
        'cancel_orders': '*.private_data_update.-.-.create_or_update.cancel_orders',
        'trade': '*.private_data_update.-.-.create_or_update.trade',
        'trades':'*.private_data_update.-.-.create_or_update.trades',
        'balance': '*.private_data_update.-.-.create_or_update.balance',
        'create_si': '*.private_data_update.-.-.create.strategy_instance',
        'update_si': '*.private_data_update.-.-.update.strategy_instance',
        'create_or_update_si': '*.private_data_update.-.-.create_or_update.strategy_instance',
        'create_dpi': '*.private_data_update.-.-.create.data_processing_instance',
        'update_dpi': '*.private_data_update.-.-.update.data_processing_instance',
        'create_or_update_dpi': '*.private_data_update.-.-.create_or_update.data_processing_instance',
    }
    def __init__(self, msgr_cli, quenue):
        self.shared_queue = quenue
        self.log = Logger(name='DBSendManager', log_file='sending_to_db.log').log
        self.msgr_cli = msgr_cli
        self.msg_map = {
            'order': self._order,
            'orders': self._orders,
            'cancel_order': self._cancel_order,
            'cancel_orders': self._cancel_orders,
            'balance': self._balance,
            'trade': self._trade,
            'trades': self._trades,
            'create_si': self._create_si,
            'update_si': self._update_si,
            'create_dpi': self._create_dpi,
            'update_dpi': self._update_dpi,
            'create_or_update_dpi':self._create_or_update_dpi,
        }

    async def start(self):
        self.log('started')
        await self.incoming_messages_handler()

    async def incoming_messages_handler(self):
        while True:
            raw_msg = None
            try:
                raw_msg = self.shared_queue.get(timeout=1)
                if raw_msg == None:
                    await asyncio.sleep(0.05)
                    continue
                new_msg = json.loads(raw_msg)
                type_ = new_msg.pop('type')
                new_msg = new_msg['response']
                await self.msg_map[type_](new_msg)
            except Empty:
                pass
            except Exception as e:
                self.log(f"incoming message handling error {str(e)}, msg: {str(raw_msg)}, type: {type(raw_msg)}", level='error')
                await asyncio.sleep(0.05)
        self.log('finished')

    async def _create_si(self, msg):
        topic = self.topic_map['create_si']
        await self.send_and_check_response(topic, msg)

    async def _update_si(self, msg):
        topic = self.topic_map['update_si']
        await self.send_and_check_response(topic, msg)

    async def _create_or_update_si(self, msg):
        topic = self.topic_map['create_or_update_si']
        await self.send_and_check_response(topic, msg)

    async def _create_dpi(self, msg):
        topic = self.topic_map['create_dpi']
        await self.send_and_check_response(topic, msg)

    async def _update_dpi(self, msg):
        topic = self.topic_map['update_dpi']
        await self.send_and_check_response(topic, msg)

    async def _create_or_update_dpi(self, msg):
        topic = self.topic_map['create_or_update_dpi']
        await self.send_and_check_response(topic, msg)

    async def _order(self, msg):
        topic = self.topic_map['order']
        await self.send_without_check_response(topic, msg)

    async def _orders(self, msg):
        for order in msg['orders']:
            order['exchange'] = msg['exchange']
            order['account'] = msg['account']
            await self._order(order)

    async def _cancel_order(self, msg):
        topic = self.topic_map['cancel_order']
        await self.send_without_check_response(topic, msg)

    async def _cancel_orders(self, msg):
        for order in msg['cancel_orders']:
            order['exchange'] = msg['exchange']
            order['account'] = msg['account']
            await self._cancel_order(order)

    async def _balance(self, msg):
        topic = self.topic_map['balance']
        await self.send_without_check_response(topic, msg)

    async def _trade(self, msg):
        topic = self.topic_map['trade']
        await self.send_without_check_response(topic, msg['message'])

    async def _trades(self, msg):
        topic = self.topic_map['trades']
        message = {'trades':[], 'exchange': msg['exchange'],'account':msg['account']}
        for trade in msg['trades']:
            trade['exchange'] = msg['exchange']
            trade['account'] = msg['account']
            message['trades'].append(trade)
        await self.send_without_check_response(topic, message)

    async def send_without_check_response(self, topic, message):
        try:
            await self.msgr_cli.aio_publish(message, topic)
            await asyncio.sleep(0.005)
        except Exception as e:
            self.log(f'send error {str(e)} topic: {topic}, message {str(message)}', level='error', slack=True)

    async def send_and_check_response(self, topic, message, timeout=10):
        try:
            kwargs = {'topic':topic, 'message': json.dumps(message), 'timeout':timeout}
            response = await self.send_to_broker(**kwargs)
            if not 'success' in response or response['success'] is False:
                raise Exception(f'private_connector response error: {response}')
        except Exception as e:
            self.log(f'send error {str(e)} topic: {topic}, message {str(message)}', level='error', slack=True)

    async def send_to_broker(self, topic, message, timeout=10):
        return await self.msgr_cli.aio_publish_request(message, topic, timeout=timeout)

