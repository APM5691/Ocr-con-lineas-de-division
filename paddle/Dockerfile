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
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo
WORKDIR /workspace

# Actualiza pip y herramientas base
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel

# Instala librerías necesarias:
# - JupyterLab + ipywidgets para notebooks
# - FastAPI + Uvicorn para servidor API
RUN pip3 install --no-cache-dir \
    jupyterlab \
    ipywidgets \
    jupyterlab_widgets \
    fastapi \
    "uvicorn[standard]"

# Crea directorios comunes de trabajo
RUN mkdir -p /workspace/app /workspace/notebooks /workspace/data && \
    chmod -R 777 /workspace

# Expone puertos:
# 8888 → Jupyter
# 8000 → FastAPI
EXPOSE 8888 8000

# Variables de entorno
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace
ENV JUPYTER_ENABLE_LAB=yes

# Comando por defecto: inicia JupyterLab sin token
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--allow-root", "--no-browser", "--NotebookApp.token=", "--NotebookApp.password="]
