from anthill import app as ant_app

app = ant_app.App(
        service_name='ms_template_async_by_lib',
        host='127.0.0.1',
        port=4222,
        app_strategy='asyncio',
)
log = app.logger.log
print('started')

@app.listen('open_orders.BINANCE.binance_account_name123.BTC/USDT')
def topic1_handler(topic, message):
    try:
        log(f'recieved message: {message}')
        """
        put you business logic here
        """
        response = {'success': True, 'data': 'request has been processed'}
        log(response, from_=topic)
        return response
    except Exception as e:
        if not 'result' in locals():
            result = ''
        msg = {'success': False, 'error': f"result: {result}, request: {topic},{message}, error: {str(e)}"}
        log(msg, topic=topic, message=message, level='error', slack=True)
        return msg

@app.listen('balances.BINANCE.binance_account_name123.*')
def topic2_handler(topic, message):
    try:
        log(f'recieved message: {message}')
        """
        put you business logic here
        """
        response = {'success': True, 'data': 'request has been processed'}
        log(response, from_=topic)
        return response
    except Exception as e:
        if not 'result' in locals():
            result = ''
        msg = {'success': False, 'error': f"result: {result}, request: {topic},{message}, error: {str(e)}"}
        log(msg, topic=topic, message=message, level='error', slack=True)
        return msg

@app.listen('user_trades.BINANCE.*.*')
def topic3_handler(topic, message):
    try:
        log(f'recieved message: {message}')
        """
        put you business logic here
        """
        response = {'success': True, 'data': 'request has been processed'}
        log(response, from_=topic)
        return response
    except Exception as e:
        if not 'result' in locals():
            result = ''
        msg = {'success': False, 'error': f"result: {result}, request: {topic},{message}, error: {str(e)}"}
        log(msg, topic=topic, message=message, level='error', slack=True)
        return msg


print('done')