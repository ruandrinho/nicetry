FROM python:3.11-slim-bullseye

WORKDIR /bot

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "bot.py"]