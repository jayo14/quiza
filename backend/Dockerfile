FROM python:3.12-slim

# tesseract-ocr: OCR for uploaded images. libgl1: PyMuPDF's runtime dependency.
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/storage && chmod +x entrypoint.sh

EXPOSE 8000

CMD ["./entrypoint.sh"]
