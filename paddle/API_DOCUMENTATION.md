# API Paddle OCR - Documentación de Endpoints

## Base URL

```
http://localhost:8000
```

## Endpoints Disponibles

### 1. Health Check

```http
GET /health
```

**Descripción:** Verifica que la API está activa

**Respuesta:**

```json
{
  "status": "healthy",
  "service": "Paddle OCR API",
  "timestamp": "2025-12-05T10:30:00.000Z"
}
```

---

### 2. Listar Proyectos

```http
GET /api/projects
```

**Descripción:** Lista todos los proyectos disponibles

**Respuesta:**

```json
{
  "total": 2,
  "projects": [
    {
      "name": "proyecto_20251201_053528",
      "status": "completed",
      "path": "/workspace/storage/projects/proyecto_20251201_053528"
    },
    {
      "name": "proyecto_20251201_053724",
      "status": "idle",
      "path": "/workspace/storage/projects/proyecto_20251201_053724"
    }
  ]
}
```

---

### 3. Listar Archivos JSON de un Proyecto

```http
GET /api/project/{project}/json-files
```

**Parámetros:**

- `project` (string, path): Nombre del proyecto

**Respuesta:**

```json
{
  "project": "proyecto_20251201_053528",
  "total": 1,
  "files": [
    {
      "filename": "lines.json",
      "size": 2048,
      "modified": "2025-12-05T09:15:00.000Z"
    }
  ]
}
```

---

### 4. Iniciar Procesamiento OCR

```http
POST /api/process
```

**Body (JSON):**

```json
{
  "project": "proyecto_20251201_053528",
  "json_filename": "lines.json"
}
```

**Respuesta:**

```json
{
  "status": "success",
  "message": "Procesamiento OCR iniciado",
  "project": "proyecto_20251201_053528",
  "json_file": "lines.json",
  "info": "El proceso continuará aunque cierres el navegador"
}
```

**Estados posibles:**

- `pending` → Esperando a procesarse
- `processing` → En procesamiento
- `completed` → Completado
- `error` → Error durante el procesamiento

---

### 5. Obtener Estado del Procesamiento

```http
GET /api/process-status/{project}
```

**Parámetros:**

- `project` (string, path): Nombre del proyecto

**Respuesta:**

```json
{
  "project": "proyecto_20251201_053528",
  "status": "completed",
  "progress": "5/5",
  "excel_path": "/workspace/storage/projects/proyecto_20251201_053528/resultado.xlsx",
  "error_message": null
}
```

---

### 6. Descargar Excel Procesado

```http
GET /api/download-excel/{project}
```

**Parámetros:**

- `project` (string, path): Nombre del proyecto

**Respuesta:** Archivo Excel (resultado.xlsx)

---

## Flujo Completo de Uso

### Paso 1: Listar proyectos

```bash
curl http://localhost:8000/api/projects
```

### Paso 2: Ver archivos JSON disponibles

```bash
curl http://localhost:8000/api/project/proyecto_20251201_053528/json-files
```

### Paso 3: Iniciar procesamiento

```bash
curl -X POST http://localhost:8000/api/process \
  -H "Content-Type: application/json" \
  -d '{
    "project": "proyecto_20251201_053528",
    "json_filename": "lines.json"
  }'
```

### Paso 4: Monitorear progreso

```bash
curl http://localhost:8000/api/process-status/proyecto_20251201_053528
```

### Paso 5: Descargar resultado

```bash
curl http://localhost:8000/api/download-excel/proyecto_20251201_053528 \
  -o resultado.xlsx
```

---

## Notas Importantes

✅ **Archivos procesados:**

- Se leen imágenes de la carpeta `originales/` (alta calidad)
- Se guardan resultados en `procesadas/`
- Se exporta Excel con datos extraídos

✅ **JSON requerido:**

- Debe contener estructura: `{ "lines": { "imagen.jpg": [x1, x2, ...] }, "line_gap": 6.5 }`
- Se pueden tener múltiples archivos JSON por proyecto

✅ **Procesamiento en background:**

- No bloquea la API
- Puedes monitorear con `/api/process-status/{project}`
- El procesamiento continúa aunque cierres el navegador

✅ **Manejo de errores:**

- Todos los endpoints retornan errores con descripciones
- Los errores se guardan en `status.json` del proyecto
