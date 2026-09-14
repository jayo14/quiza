FROM python:3.12-slim

# tesseract-ocr: OCR for uploaded images. libgl1: PyMuPDF's runtime dependency.
# supervisor: process manager for uvicorn + celery.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    supervisor \
    && rm -rf /var/log/supervisor \
    && mkdir -p /var/log/supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/storage && chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
