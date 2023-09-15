FROM python:3.8.3-buster

ARG WORK_FOLDER

RUN pip install --upgrade pip

ADD requirements.txt /

RUN pip install -r requirements.txt --ignore-installed --force-reinstall

RUN mkdir /app
WORKDIR /app
COPY ./$WORK_FOLDER/app /app

CMD ["python", "/app/main.py"]