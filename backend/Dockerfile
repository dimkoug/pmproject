FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev \
    # Optional OCR dependencies — present in the image, only used when
    # DMS_OCR_ENABLED=1 is set. Adds ~120MB. Remove this block if you
    # never plan to OCR scanned images.
    tesseract-ocr poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default: production with 4 workers.
# Override CMD in docker-compose for dev (--reload) or different worker count.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", \
     "--workers", "4", "--loop", "uvloop", "--http", "httptools", \
     "--limit-concurrency", "500", "--timeout-keep-alive", "30"]
