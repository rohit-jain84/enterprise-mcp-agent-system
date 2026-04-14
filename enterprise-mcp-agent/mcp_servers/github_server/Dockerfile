FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Also install the shared module
COPY ../shared /app/shared

EXPOSE 8001

CMD ["python", "server.py"]
