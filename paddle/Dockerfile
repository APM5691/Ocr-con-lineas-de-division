# Imagen base liviana con soporte CUDA (solo runtime, sin toolkits de desarrollo)
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

# Evita preguntas interactivas
ENV DEBIAN_FRONTEND=noninteractive

# Instala Python y dependencias básicas del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    git \
    curl \
    wget \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /workspace

# Actualiza pip y herramientas base
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# Instala librerías necesarias del requirements.txt
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Instala PaddleOCR con soporte GPU
RUN pip3 install --no-cache-dir \
    paddleocr \
    paddlepaddle-gpu \
    jupyterlab \
    ipywidgets \
    jupyterlab_widgets \
    fastapi \
    "uvicorn[standard]"

# Crea directorios comunes de trabajo
RUN mkdir -p /workspace/app /workspace/notebooks /workspace/data /workspace/uploads /workspace/outputs && \
    chmod -R 777 /workspace

# Expone puertos:
# 8000 → FastAPI (OCR API)
# 8888 → Jupyter (opcional, solo desarrollo)
EXPOSE 8000 8888

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace
ENV JUPYTER_ENABLE_LAB=yes

# Comando por defecto: inicia FastAPI con Uvicorn
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]
