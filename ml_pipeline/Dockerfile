FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY ml_pipeline/requirements.txt /app/ml_pipeline/requirements.txt

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/ml_pipeline/requirements.txt

COPY ml_pipeline /app/ml_pipeline

CMD ["python", "ml_pipeline/src/main.py"]
