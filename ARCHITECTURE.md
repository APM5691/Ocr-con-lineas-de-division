# PDF OCR Lines Manager - Arquitectura Completa

## 📋 Descripción General

Sistema modular para procesar PDFs, marcar líneas de división y extraer datos con OCR. Separa claramente las responsabilidades:

1. **Backend Flask** - Gestión de proyectos, imágenes, líneas
2. **Frontend** - Interfaz para marcar líneas
3. **Paddle OCR API** - Procesamiento de OCR

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Nginx:80)                       │
│  - Subir PDF                                                 │
│  - Marcar líneas en imágenes                                │
│  - Ver historial de proyectos                              │
└──────────────────┬──────────────────────────────────────────┘
                   │
        ┌──────────┴──────────┐
        ▼                     ▼
┌──────────────────┐   ┌──────────────────┐
│ BACKEND (5000)   │   │ PADDLE OCR       │
│                  │   │ (8000 + 8888)    │
│ - Upload PDF     │   │                  │
│ - Manage images  │   │ - Process OCR    │
│ - Mark lines     │   │ - Extract text   │
│ - Export JSON    │   │ - Generate Excel │
└──────────────────┘   └──────────────────┘
```

---

## 🔄 Flujo de Trabajo

### Fase 1: Preparación (Backend)

```
1. Usuario sube PDF
   → Backend convierte a imágenes (300 DPI)
   → Crea: originales/ (alta calidad) + baja_calidad/ (visualización)
   → Retorna proyecto_id

2. Frontend carga imágenes (baja_calidad/)
   → Usuario marca líneas de división
   → Datos se guardan en navegador

3. Usuario exporta líneas
   → Backend guarda lines.json en proyecto
   → Estructura: { "lines": { "img_001.jpg": [x1, x2, ...] } }
```

### Fase 2: Procesamiento (Paddle OCR)

```
1. Usuario inicia procesamiento
   → POST /api/process con { "project": "...", "json_filename": "lines.json" }

2. Paddle OCR lee:
   → Imágenes originales (300 DPI)
   → Configuración de líneas (lines.json)
   → Aplica cortes según líneas marcadas

3. Genera resultado:
   → resultado.xlsx con datos extraídos
   → Imágenes procesadas en carpeta procesadas/
```

---

## 📁 Estructura de Directorios

```
project-root/
│
├── backend/
│   ├── main.py                  # API Flask (gestión + imágenes)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── storage/
│       ├── uploads/              # PDFs originales
│       └── projects/
│           └── proyecto_TIMESTAMP/
│               ├── status.json
│               ├── lines.json
│               ├── originales/    (300 DPI, 95% quality)
│               ├── baja_calidad/  (800px, 70% quality)
│               └── procesadas/    (resultados OCR)
│
├── paddle/
│   ├── app/
│   │   ├── api.py               # API FastAPI (OCR)
│   │   ├── ocr_processor.py
│   │   └── __init__.py
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── workspace/               # Jupyter notebooks
│   └── outputs/                 # Resultados finales
│
├── frontend/
│   ├── index.html
│   ├── App.jsx
│   ├── app.js
│   └── Dockerfile
│
└── docker-compose.yml           # Orquestación
```

---

## 🚀 Endpoints por Servicio

### Backend (http://localhost:5000)

| Método | Endpoint                    | Función           |
| ------ | --------------------------- | ----------------- |
| GET    | `/health`                   | Verificar estado  |
| POST   | `/api/upload`               | Subir PDF         |
| GET    | `/api/images/{filename}`    | Obtener imagen    |
| GET    | `/api/projects`             | Listar proyectos  |
| POST   | `/api/set-project/{name}`   | Activar proyecto  |
| POST   | `/api/export-lines`         | Exportar líneas   |
| GET    | `/api/project/{name}/lines` | Obtener líneas    |
| GET    | `/api/project/{name}/info`  | Info del proyecto |
| DELETE | `/api/project/{name}`       | Eliminar proyecto |

### Paddle OCR (http://localhost:8000)

| Método | Endpoint                         | Función                  |
| ------ | -------------------------------- | ------------------------ |
| GET    | `/health`                        | Verificar estado         |
| POST   | `/api/process`                   | Iniciar OCR              |
| GET    | `/api/process-status/{project}`  | Estado del procesamiento |
| GET    | `/api/download-excel/{project}`  | Descargar resultado      |
| GET    | `/api/projects`                  | Listar proyectos         |
| GET    | `/api/project/{name}/json-files` | Listar JSONs             |

---

## 📊 Flujo de Datos JSON

### 1. Exportación (Backend → Paddle)

```json
{
  "lines": {
    "img_001.jpg": [100.5, 250.3, 400.8],
    "img_002.jpg": [100.5, 250.3],
    "img_003.jpg": []
  },
  "line_gap": 6.5,
  "exported_at": "2025-12-05T10:35:00.000Z",
  "total_lines": 5
}
```

### 2. Estado del Proyecto

```json
{
  "status": "idle|processing|completed|error",
  "created_at": "20251205_103000",
  "pdf_filename": "documento.pdf",
  "total_pages": 5,
  "lines_exported": "2025-12-05T10:35:00.000Z"
}
```

### 3. Resultado OCR (Paddle)

```json
{
  "status": "completed",
  "excel_path": "/workspace/.../resultado.xlsx",
  "total_rows": 150,
  "json_used": "lines.json",
  "completed_at": "2025-12-05T11:45:00.000Z"
}
```

---

## 🐳 Docker Compose

```yaml
services:
  backend:
    port: 5000
    volume: ./backend/storage

  paddle:
    port: 8000, 8888
    gpu: enabled
    volume: ./paddle/workspace

  frontend:
    port: 80
    depends_on: backend, paddle
```

---

## 🔌 Integración con Componentes Externos

### Frontend ↔ Backend

```javascript
// Subir PDF
const formData = new FormData();
formData.append("file", pdfFile);
const response = await fetch("http://localhost:5000/api/upload", {
  method: "POST",
  body: formData,
});

// Exportar líneas
await fetch("http://localhost:5000/api/export-lines", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ lines: linesData, line_gap: 6.5 }),
});
```

### Backend ↔ Paddle OCR

```python
# El frontend puede llamar directamente a Paddle
requests.post('http://localhost:8000/api/process', json={
  'project': 'proyecto_20251205_103000',
  'json_filename': 'lines.json'
})
```

---

## 📝 Variables de Entorno

### Backend

```env
FLASK_ENV=production
PYTHONUNBUFFERED=1
```

### Paddle

```env
TZ=America/Mexico_City
JUPYTER_TOKEN=
JUPYTER_ENABLE_LAB=yes
```

### Frontend

```env
VITE_API_URL=http://localhost:5000
VITE_OCR_API_URL=http://localhost:8000
```

---

## 🚦 Estados de Proyecto

```
idle
  ↓
upload PDF → backend convierte imágenes
  ↓
set-project → carga imágenes en frontend
  ↓
mark lines → usuario marca líneas
  ↓
export-lines → guarda lines.json
  ↓
[opcional] process OCR → paddle procesa
  ↓
completed → resultado.xlsx generado
```

---

## ⚠️ Consideraciones Importantes

### Imágenes

- **Originales:** Se mantienen a 300 DPI para OCR
- **Baja calidad:** Se reducen a 800px de ancho para visualización rápida
- Ambas versiones se guardan (no se eliminan)

### Líneas

- Se guardan como coordenadas X en píxeles
- Relativas a la imagen original (300 DPI)
- Se pueden marcar múltiples líneas por página

### OCR

- Requiere GPU NVIDIA (soporte en docker-compose)
- PaddleOCR con español como idioma
- Procesa en background (no bloquea API)

### Seguridad

- CORS habilitado para desarrollo (cambiar en producción)
- Sin autenticación (agregar si es necesario)
- PDFs se guardan en servidor (considerar límites)

---

## 🔧 Comandos Útiles

```bash
# Iniciar servicios
docker compose up --build

# Ver logs
docker compose logs -f backend
docker compose logs -f paddle

# Detener servicios
docker compose down

# Eliminar volúmenes
docker compose down -v

# Acceder a Jupyter Lab
# http://localhost:8888

# Acceder a API docs
# http://localhost:5000/docs
# http://localhost:8000/docs
```

---

## 📦 Dependencias

### Backend

- FastAPI, Uvicorn
- pdf2image, Pillow (PIL)
- pandas

### Paddle OCR

- PaddleOCR, PaddleOCR
- FastAPI, Uvicorn
- OpenCV, scikit-image
- JupyterLab

### Frontend

- React/Vue/Vanilla JS
- Axios (o fetch)
- Tailwind CSS

---

## 🎯 Próximos Pasos

- [ ] Agregar autenticación (JWT)
- [ ] Implementar caché de imágenes
- [ ] Agregar validación de PDF (páginas máx)
- [ ] Monitoreo y logging centralizado
- [ ] Tests unitarios
- [ ] Documentación Swagger completa
- [ ] Soporte para múltiples idiomas en OCR
- [ ] Interfaz de reporte de progreso en tiempo real
