FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

# Instalar dependencias en orden, forzando PyMuPDF más reciente
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn==0.24.0 \
    python-multipart==0.0.6 \
    pandas==2.1.4 \
    openpyxl==3.1.2 \
    Pillow==10.1.0 \
    pdf2image==1.16.3 \
    opencv-python-headless==4.8.1.78 \
    PyMuPDF==1.23.8 && \
    pip install --no-cache-dir --no-deps paddleocr==2.7.0 && \
    pip install --no-cache-dir paddlepaddle==2.6.2

COPY main.py .

RUN mkdir -p storage/uploads storage/projects

EXPOSE 5000

# Sin --reload para evitar consumo excesivo de memoria en Docker
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
