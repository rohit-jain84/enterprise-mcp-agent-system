FROM python:3.12-slim

WORKDIR /app

COPY github_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY github_server/ ./github_server/

WORKDIR /app/github_server

EXPOSE 8001

CMD ["python", "server.py"]
