FROM python:3.12-slim

WORKDIR /app

COPY project_management_server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared/ ./shared/
COPY project_management_server/ ./project_management_server/

WORKDIR /app/project_management_server

EXPOSE 8002

CMD ["python", "server.py"]
