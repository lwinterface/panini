FROM python:3.7.8-buster

RUN pip install --upgrade pip
ADD requirements.txt /
RUN pip install -r requirements.txt

CMD [ "cd", "app/microservice1" ]
WORKDIR ./app

CMD [ "./microservice1/run.sh" ]

