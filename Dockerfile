FROM python:3.10-buster
ENV PYTHONUNBUFFERED=1
WORKDIR /src
COPY . /src/
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    postgresql-client
COPY requirements.txt /code/
RUN pip install -r requirements.txt