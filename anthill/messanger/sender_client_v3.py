import sys
import os
import logging
import asyncio
import concurrent.futures
import time




if __name__ == "__main__":
    os.environ['SERVICE_NAME'] = 'private_request_validator_sender_client'
    script_position = os.path.dirname(sys.argv[0])
    os.environ['SERVICE_ROOT_PATH'] = f'{script_position}/' if script_position else ''
    from messanger._msgr_client_v3 import Sender, isr_log
    if len(sys.argv) > 1:
        kwargs = sys.argv[1]
    else:
        # error = 'argumets required'
        # isr_log(error, level='error')
        # raise Exception(error)
        kwargs = {'client_id': 'client45',
                  'broker_host': '127.0.0.1',
                  'port': '4222',
                  'listen_topics_callbacks': None,
                  'listen_message_queue': None,
                  'publish_topics': ['*.private_validated.*.*.get_balance', '*.private_validated.*.*.get_order', '*.private_validated.*.*.get_open_orders', '*.private_validated.*.*.get_trade_history', '*.private_validated.*.*.get_cancelled_orders', '*.private_validated.*.*.create_limit_order', '*.private_validated.*.*.cancel_order', '*.private_validated.*.*.cancel_all_orders', '*.private_validated.*.*.get_order_book', '*.private_validated.*.*.get_all_tickers', '-.block_endpoint', '-.get_ticker', '-.get_balance'],
                  'publish_message_queue': ['private_request_validator.get_balance', 'private_request_validator.get_order', 'private_request_validator.get_open_orders', 'private_request_validator.get_trade_history', 'private_request_validator.get_cancelled_orders', 'private_request_validator.create_limit_order', 'private_request_validator.cancel_order', 'private_request_validator.cancel_all_orders', 'private_request_validator.get_order_book', 'private_request_validator.get_all_tickers', 'private_request_validator.block_endpoint', 'private_request_validator.get_ticker'],
                  'allow_reconnect': True,
                  'max_reconnect_attempts': 10,
                  'reconnecting_time_wait': 10,
                  'if_error': 'warning',
                  'new_topics_redis_queue': None}
    Sender().launch(**kwargs)

