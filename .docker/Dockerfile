FROM ghcr.io/doyunshin/apache-python:3.13

WORKDIR /app
COPY requirements.txt ./

RUN pip install -U pip wheel setuptools && \
    pip install -U -r requirements.txt && \
    mkdir /app/data/logs -p

COPY ./*.py .docker/app.wsgi ./
COPY static/ static/
COPY .docker/apache.conf /usr/local/apache2/conf/sites/
