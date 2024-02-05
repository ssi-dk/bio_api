# syntax=docker/dockerfile:1
FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY . /app/
WORKDIR /app

RUN python -m pip install -r requirements.txt

# Define volumes
RUN mkdir /test_data
VOLUME /test_data
