FROM python:3.12-slim

WORKDIR /app

COPY calendar_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY calendar_server/ ./calendar_server/

WORKDIR /app/calendar_server

EXPOSE 8003

CMD ["python", "server.py"]
