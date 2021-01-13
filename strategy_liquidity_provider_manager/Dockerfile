FROM python:3.7.8-buster

RUN pip install --upgrade pip

ADD requirements_strategy_liquidity_provider_manager.txt /
RUN pip install -r requirements_strategy_liquidity_provider_manager.txt

RUN export EXTERNAL_PATH=$(pwd)
CMD [ "cd", "app/strategy_liquidity_provider_manager" ]
WORKDIR ./app

CMD [ "./strategy_liquidity_provider_manager/run.sh" ]

