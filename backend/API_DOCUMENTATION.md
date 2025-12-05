# Backend API - Documentación de Endpoints

## Base URL

```
http://localhost:5000
```

## Descripción General

API para gestión de proyectos OCR: subida de PDFs, conversión a imágenes de alta/baja calidad, marcado de líneas y exportación de configuración.

---

## Endpoints

### 1. Health Check

```http
GET /health
```

Verifica que la API está activa

**Respuesta:**

```json
{
  "status": "healthy",
  "service": "PDF OCR Lines Manager",
  "timestamp": "2025-12-05T10:30:00.000Z"
}
```

---

### 2. Subir PDF

```http
POST /api/upload
```

Sube un PDF y lo convierte a imágenes (alta y baja calidad)

**Content-Type:** `multipart/form-data`

**Parámetros:**

- `file` (file, required): Archivo PDF

**Respuesta:**

```json
{
  "status": "success",
  "project": "proyecto_20251205_103000",
  "total_pages": 5,
  "images": [
    "img_001.jpg",
    "img_002.jpg",
    "img_003.jpg",
    "img_004.jpg",
    "img_005.jpg"
  ],
  "message": "PDF procesado: 5 páginas"
}
```

**Estructura creada:**

```
storage/
├── uploads/
│   └── proyecto_20251205_103000.pdf
└── projects/
    └── proyecto_20251205_103000/
        ├── status.json
        ├── originales/          (300 DPI, 95% quality)
        │   ├── img_001.jpg
        │   ├── img_002.jpg
        │   └── ...
        ├── baja_calidad/        (reducidas, 70% quality)
        │   ├── img_001.jpg
        │   ├── img_002.jpg
        │   └── ...
        └── procesadas/          (para futuros resultados)
```

---

### 3. Obtener Imagen

```http
GET /api/images/{filename}?quality=baja
```

Obtiene una imagen del proyecto actual

**Parámetros:**

- `filename` (string, path): Nombre del archivo (ej: `img_001.jpg`)
- `quality` (string, query): `"baja"` (defecto, 800px) o `"alta"` (original, 300 DPI)

**Respuesta:** Imagen JPEG

---

### 4. Listar Proyectos

```http
GET /api/projects
```

Lista todos los proyectos disponibles

**Respuesta:**

```json
{
  "total": 3,
  "current": "proyecto_20251205_103000",
  "projects": [
    {
      "name": "proyecto_20251205_103000",
      "status": "idle",
      "created_at": "20251205_103000",
      "total_pages": 5
    },
    {
      "name": "proyecto_20251204_150000",
      "status": "idle",
      "created_at": "20251204_150000",
      "total_pages": 3
    }
  ]
}
```

---

### 5. Establecer Proyecto Activo

```http
POST /api/set-project/{project_name}
```

Establece un proyecto como activo y carga sus imágenes

**Parámetros:**

- `project_name` (string, path): Nombre del proyecto

**Respuesta:**

```json
{
  "status": "success",
  "project": "proyecto_20251205_103000",
  "total_images": 5,
  "images": [
    "img_001.jpg",
    "img_002.jpg",
    "img_003.jpg",
    "img_004.jpg",
    "img_005.jpg"
  ],
  "lines": {
    "img_001.jpg": [100.5, 250.3, 400.8],
    "img_002.jpg": [100.5, 250.3]
  },
  "project_status": "idle"
}
```

---

### 6. Exportar Líneas

```http
POST /api/export-lines
```

Exporta las líneas marcadas a JSON

**Body (JSON):**

```json
{
  "lines": {
    "img_001.jpg": [100.5, 250.3, 400.8],
    "img_002.jpg": [100.5, 250.3],
    "img_003.jpg": []
  },
  "line_gap": 6.5
}
```

**Respuesta:**

```json
{
  "status": "success",
  "message": "Líneas exportadas correctamente",
  "path": "/workspace/storage/projects/proyecto_20251205_103000/lines.json",
  "total_lines": 5
}
```

---

### 7. Obtener Líneas de un Proyecto

```http
GET /api/project/{project_name}/lines
```

Obtiene las líneas guardadas de un proyecto específico

**Parámetros:**

- `project_name` (string, path): Nombre del proyecto

**Respuesta:**

```json
{
  "status": "success",
  "project": "proyecto_20251205_103000",
  "lines": {
    "img_001.jpg": [100.5, 250.3, 400.8],
    "img_002.jpg": [100.5, 250.3]
  },
  "line_gap": 6.5,
  "exported_at": "2025-12-05T10:35:00.000Z"
}
```

---

### 8. Obtener Información del Proyecto

```http
GET /api/project/{project_name}/info
```

Obtiene información detallada de un proyecto

**Parámetros:**

- `project_name` (string, path): Nombre del proyecto

**Respuesta:**

```json
{
  "status": "success",
  "project": "proyecto_20251205_103000",
  "created_at": "20251205_103000",
  "total_pages": 5,
  "total_lines_marked": 5,
  "lines_exported_at": "2025-12-05T10:35:00.000Z",
  "pdf_filename": "documento.pdf"
}
```

---

### 9. Eliminar Proyecto

```http
DELETE /api/project/{project_name}
```

Elimina un proyecto completo (carpetas y archivos)

**Parámetros:**

- `project_name` (string, path): Nombre del proyecto

**Respuesta:**

```json
{
  "status": "success",
  "message": "Proyecto 'proyecto_20251205_103000' eliminado"
}
```

---

## Flujo Completo de Uso

### 1. Subir PDF

```bash
curl -X POST http://localhost:5000/api/upload \
  -F "file=@documento.pdf"
```

### 2. Obtener imagen para marcar líneas

```bash
curl http://localhost:5000/api/images/img_001.jpg?quality=baja \
  -o imagen.jpg
```

### 3. Exportar líneas marcadas

```bash
curl -X POST http://localhost:5000/api/export-lines \
  -H "Content-Type: application/json" \
  -d '{
    "lines": {
      "img_001.jpg": [100.5, 250.3, 400.8],
      "img_002.jpg": [100.5, 250.3]
    },
    "line_gap": 6.5
  }'
```

### 4. Obtener líneas guardadas

```bash
curl http://localhost:5000/api/project/proyecto_20251205_103000/lines
```

### 5. Procesar en Paddle OCR

```bash
curl -X POST http://localhost:8000/api/process \
  -H "Content-Type: application/json" \
  -d '{
    "project": "proyecto_20251205_103000",
    "json_filename": "lines.json"
  }'
```

---

## Estructura de Carpetas

```
storage/
├── uploads/
│   ├── proyecto_20251205_103000.pdf
│   └── proyecto_20251204_150000.pdf
│
└── projects/
    ├── proyecto_20251205_103000/
    │   ├── status.json
    │   ├── lines.json
    │   ├── originales/
    │   │   ├── img_001.jpg (300 DPI, 95% quality)
    │   │   ├── img_002.jpg
    │   │   └── ...
    │   ├── baja_calidad/
    │   │   ├── img_001.jpg (800px, 70% quality)
    │   │   ├── img_002.jpg
    │   │   └── ...
    │   └── procesadas/
    │       └── (resultados del OCR)
    │
    └── proyecto_20251204_150000/
        └── ...
```

---

## Notas Importantes

✅ **Imágenes:**

- **Originales:** 300 DPI, 95% JPEG quality - para procesamiento OCR
- **Baja calidad:** Máx 800px ancho, 70% quality - para visualización rápida

✅ **Líneas:**

- Se guardan como coordenadas X (píxeles) en un objeto JSON
- Se asocian a cada imagen por nombre de archivo
- Se pueden replicar entre páginas

✅ **Proyectos:**

- Cada proyecto tiene carpeta separada con timestamp
- Se genera `status.json` para seguimiento
- Estructura lista para integración con OCR

✅ **Integración:**

- El JSON exportado es compatible con Paddle OCR API
- Las imágenes en `originales/` se usan para procesamiento
- Resultados se guardan en carpeta `procesadas/`
