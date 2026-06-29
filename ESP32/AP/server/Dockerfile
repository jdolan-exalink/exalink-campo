FROM python:3.12-alpine

WORKDIR /app

RUN mkdir -p /app/DB

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY cert.pem key.pem .

ENV LORA_LISTEN_PORT=6666
ENV LORA_AUTH_PASSWORD=abc1234
ENV LORA_MAX_PACKETS=500
ENV LORA_DB_PATH=/app/DB/lora.db

EXPOSE 6666

CMD ["python", "app.py"]
