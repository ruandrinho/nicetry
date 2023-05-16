FROM python:3.11-slim-bullseye

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /backend

RUN mkdir /backend/static

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
