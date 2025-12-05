# Solución del Error: OSError [Errno 12] Cannot allocate memory

## 🔍 Problema Identificado

**Error en Docker:**

```
OSError: [Errno 12] Cannot allocate memory: '/app/storage'
```

### Causa Raíz

El contenedor `ocr-backend` estaba usando **`--reload`** en Uvicorn, que:

1. Monitorea recursivamente TODOS los archivos `.py` en el directorio
2. También intenta monitorear `/app/storage/` donde se guardan imágenes y PDFs
3. Con PDFs y miles de archivos, consume toda la memoria disponible
4. El contenedor no tiene suficiente RAM asignada

---

## ✅ Soluciones Aplicadas

### 1. **Dockerfile Backend - Remover `--reload`**

**Antes:**

```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Después:**

```dockerfile
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
```

✅ Ventajas:

- No monitorea archivos constantemente
- Reduce consumo de memoria drásticamente
- Ideal para producción en Docker
- Los cambios de código requieren rebuild (normal en Docker)

### 2. **Docker Compose - Corregir Puerto**

**Antes:**

```yaml
ports:
  - "5000:8000" # ❌ Mapeaba puerto 5000 host a 8000 contenedor
```

**Después:**

```yaml
ports:
  - "5000:5000" # ✅ Mapeaba puerto 5000 host a 5000 contenedor
```

### 3. **Puerto Correcto en Dockerfile**

```dockerfile
EXPOSE 5000  # ✅ Correcto
```

---

## 📊 Comparación

| Aspecto               | Con `--reload`       | Sin `--reload`       |
| --------------------- | -------------------- | -------------------- |
| Monitoreo de archivos | ✅ Automático        | ❌ Manual            |
| Consumo de memoria    | 🔴 Alto              | 🟢 Bajo              |
| Restart en cambios    | ✅ Automático        | ❌ Manual            |
| Ideal para            | 🏠 Desarrollo local  | 🏭 Docker/Producción |
| Archivos monitorados  | Todos recursivamente | Ninguno              |

---

## 🚀 Cómo Proceder

### Opción 1: Desarrollo Local (SIN Docker)

Usar `--reload` para desarrollo más rápido:

```bash
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

### Opción 2: Docker (Recomendado)

Ejecutar sin `--reload`:

```bash
docker compose down  # Detener contenedores previos
docker compose up --build  # Compilar y ejecutar
```

---

## 🔧 Ports Definitivos

| Servicio             | Puerto | Uso                        |
| -------------------- | ------ | -------------------------- |
| Backend (FastAPI)    | 5000   | Gestión de PDFs e imágenes |
| Paddle OCR (FastAPI) | 8000   | Procesamiento OCR          |
| Jupyter Lab          | 8888   | Notebooks interactivos     |
| Frontend (Nginx)     | 80     | Interfaz web               |

---

## ✨ Cambios Realizados

```
backend/
├── Dockerfile          ✅ Removido --reload, puerto 5000
└── main.py             ✅ No requiere cambios (ya era :5000)

docker-compose.yml      ✅ Puerto mapeado correctamente (5000:5000)
```

---

## 🎯 Próximos Pasos

1. **Compilar nuevamente:**

   ```bash
   docker compose up --build
   ```

2. **Verificar que funciona:**

   ```bash
   curl http://localhost:5000/health
   ```

3. **Respuesta esperada:**
   ```json
   {
     "status": "healthy",
     "service": "PDF OCR Lines Manager",
     "timestamp": "2025-12-05T..."
   }
   ```

---

## 💡 Notas Adicionales

### Para Desarrollo con Cambios Rápidos

Si necesitas hot-reload durante desarrollo, ejecuta localmente:

```bash
pip install -r backend/requirements.txt
uvicorn backend.main:app --reload --port 5000
```

### Para Producción

Usa el Docker sin `--reload` (más eficiente):

```bash
docker compose up -d
```

### Monitoreo de Memoria

Si aún tienes problemas de memoria, puedes limitar Docker:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

---

## 📋 Resumen

| ✅ Solucionado       | Descripción         |
| -------------------- | ------------------- |
| Memoria agotada      | Removido --reload   |
| Puerto incorrecto    | Corregido 8000→5000 |
| Configuración Docker | Actualizado         |
| Documentación        | Creada              |

**Ahora puedes hacer:** `docker compose up --build` 🚀
