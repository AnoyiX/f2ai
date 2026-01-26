# Base image
FROM python:3.13-slim

# Install system dependencies
# libreoffice: for converting doc/docx/ppt/pptx to pdf
# poppler-utils: for converting pdf to images (used by pdf2image)
# libmagic1: for python-magic
# fonts-liberation, fonts-wqy-zenhei: fonts to support various languages (including Chinese)
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    libreoffice-impress \
    libreoffice-calc \
    poppler-utils \
    imagemagick \
    ffmpeg \
    libmagic1 \
    fonts-liberation \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p static/upload static/convert

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
