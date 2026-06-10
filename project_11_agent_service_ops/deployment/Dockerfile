FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY common /app/common
COPY project_11_agent_service_ops /app/project_11_agent_service_ops

RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

ENV PROJECT_11_HOST=0.0.0.0
ENV PROJECT_11_PORT=8011

EXPOSE 8011

CMD ["python", "project_11_agent_service_ops/main.py"]
