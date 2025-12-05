# Frontend Update - OCR Processing Button

## 🎯 Funcionalidad Agregada

Se ha implementado un nuevo botón "🔄 Procesar OCR" que integra el flujo completo:

```
1. Usuario hace clic en "Procesar OCR"
   ↓
2. Frontend envía petición a Backend OCR con:
   - project: nombre del proyecto
   - json_filename: "lines.json"
   ↓
3. Backend OCR inicia procesamiento en background
   ↓
4. Frontend monitorea progreso cada 2 segundos
   - Muestra barra de progreso (0% → 100%)
   - Actualiza estado (iniciando → procesando → completado)
   ↓
5. Cuando se complete:
   - Frontend descarga automáticamente el Excel
   - Muestra mensaje de éxito
   - Limpia el estado después de 3 segundos
```

---

## 📋 Componentes Implementados

### 1. Estado Global (`useState`)

```javascript
const [processingStatus, setProcessingStatus] = useState(null);
const [processingProgress, setProcessingProgress] = useState(0);
```

Estados posibles:

- `null` - Sin procesamiento activo
- `'pending'` - Iniciando
- `'processing: {progress}'` - En progreso
- `'completed'` - Completado
- `'success'` - Éxito
- `'error'` - Error

### 2. Función Principal: `handleProcessOCR()`

```javascript
async function handleProcessOCR() {
  // 1. Validaciones
  if (!projectName) throw error

  // 2. Enviar petición POST a /api/process
  POST http://localhost:8000/api/process
  {
    "project": "proyecto_20251205_103000",
    "json_filename": "lines.json"
  }

  // 3. Monitorear progreso
  while (!isComplete) {
    GET http://localhost:8000/api/process-status/{project}

    if status === 'completed':
      // 4. Descargar Excel
      GET http://localhost:8000/api/download-excel/{project}
  }
}
```

### 3. Función Auxiliar: `downloadExcel()`

```javascript
async function downloadExcel(project) {
  // Obtener archivo Excel del backend
  const response = await fetch(
    `http://localhost:8000/api/download-excel/${project}`
  );

  // Crear blob y simular descarga
  const blob = await response.blob();
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${project}_resultado.xlsx`;
  link.click();
}
```

---

## 🎨 Interfaz de Usuario

### Barra de Progreso

```
┌─────────────────────────────────────────┐
│ ⏳ Iniciando...                          │
│ ████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  │
│ 25%                                     │
└─────────────────────────────────────────┘
```

Estados visuales:

- `⏳ Iniciando` - Yellow/Amber
- `⏸️ processing: 50/100` - Blue
- `✅ Completado` - Green
- `❌ Error` - Red

### Botones

```
[📥 Exportar JSON]  [🔄 Procesar OCR]
```

- **Exportar JSON**: Se deshabilita durante procesamiento
- **Procesar OCR**: Se deshabilita si no hay imágenes o está procesando

---

## 📡 Endpoints Utilizados

### 1. Iniciar Procesamiento

```http
POST http://localhost:8000/api/process
Content-Type: application/json

{
  "project": "proyecto_20251205_103000",
  "json_filename": "lines.json"
}

Response:
{
  "status": "success",
  "message": "Procesamiento OCR iniciado",
  "project": "proyecto_20251205_103000",
  "json_file": "lines.json"
}
```

### 2. Monitorear Progreso

```http
GET http://localhost:8000/api/process-status/proyecto_20251205_103000

Response:
{
  "project": "proyecto_20251205_103000",
  "status": "processing",
  "progress": "3/5",
  "excel_path": null,
  "error_message": null
}
```

Posibles valores de `status`:

- `idle` - Sin procesamiento
- `pending` - Esperando inicio
- `processing` - En progreso
- `completed` - Completado exitosamente
- `error` - Error durante procesamiento

### 3. Descargar Excel

```http
GET http://localhost:8000/api/download-excel/proyecto_20251205_103000

Response: Binary (archivo xlsx)
```

---

## ⚙️ Parámetros de Configuración

### Monitoreo de Progreso

```javascript
// Intervalo de chequeo
await new Promise((resolve) => setTimeout(resolve, 2000)); // 2 segundos

// Máximo de intentos
const maxAttempts = 180; // 6 minutos máximo
```

### Nombres de Archivo

```javascript
// El JSON debe estar exportado previamente
json_filename: "lines.json";

// El archivo descargado se nombra automáticamente
filename: `${project}_resultado.xlsx`;
```

---

## 🔄 Flujo de Datos Completo

```
Frontend (React)
    │
    ├─► POST /api/process
    │   ├─► Backend OCR recibe
    │   └─► Inicia background task
    │
    ├─► GET /api/process-status (cada 2s)
    │   ├─► Chequea estado
    │   └─► Retorna progreso
    │
    └─► GET /api/download-excel (cuando complete)
        ├─► Backend OCR retorna xlsx
        └─► Frontend descarga automáticamente

Backend OCR (http://localhost:8000)
    │
    ├─► Valida proyecto y JSON
    ├─► Lee imágenes de carpeta "originales/"
    ├─► Aplica líneas marcadas
    ├─► Procesa con PaddleOCR
    ├─► Genera resultado.xlsx
    └─► Retorna archivo
```

---

## 📝 Requisitos Previos

✅ Proyecto creado y con imágenes subidas
✅ Líneas marcadas en las imágenes
✅ JSON exportado (`lines.json` en carpeta del proyecto)
✅ Backend OCR en ejecución (puerto 8000)

---

## 🚀 Uso

1. **Subir PDF**

   - Hacer clic en el área de carga
   - Seleccionar archivo PDF

2. **Marcar Líneas**

   - Hacer clic en las imágenes para marcar líneas
   - Usar botón "Replicar" para aplicar a otras páginas

3. **Exportar Líneas**

   - Hacer clic en "📥 Exportar JSON"
   - Se guarda en backend: `proyecto_XXXXX/lines.json`

4. **Procesar OCR**

   - Hacer clic en "🔄 Procesar OCR"
   - Ver barra de progreso
   - Excel se descarga automáticamente

5. **Verificar Resultado**
   - Abrir el archivo Excel descargado
   - Los datos estarán organizados por columnas (según las líneas marcadas)

---

## ⚠️ Manejo de Errores

### Error: "No hay proyecto activo"

- Causa: No se ha cargado ningún proyecto
- Solución: Cargar un proyecto desde el historial

### Error: "Timeout: Procesamiento tardó demasiado"

- Causa: OCR tardó más de 6 minutos
- Solución: Intentar nuevamente o verificar los logs del servidor

### Error: "Error descargando Excel"

- Causa: El archivo no existe o la ruta es incorrecta
- Solución: Verificar que el procesamiento se completó exitosamente

---

## 🔍 Debugging

### Ver logs en consola (F12)

```javascript
// Logs de inicio
console.log(`Iniciando OCR para proyecto: ${projectName}`);

// Logs de progreso
console.log(`Progreso: ${statusData.progress}`);

// Logs de descarga
console.log(`✅ Excel descargado: ${filename}`);
```

### Verificar estado del backend

```bash
curl http://localhost:8000/api/process-status/proyecto_20251205_103000
```

---

## 📊 Estados de Aplicación

| Estado     | Visual | Botones        | Descripción              |
| ---------- | ------ | -------------- | ------------------------ |
| Inactivo   | -      | Habilitados    | Esperando acción         |
| Pendiente  | ⏳     | Deshabilitados | Iniciando procesamiento  |
| Procesando | ⏸️     | Deshabilitados | En progreso con %        |
| Completado | ✅     | Deshabilitados | Descargando Excel        |
| Éxito      | ✅     | Habilitados    | Procesamiento completado |
| Error      | ❌     | Habilitados    | Mostrar error y limpiar  |

---

## 🎯 Próximas Mejoras

- [ ] Agregar opción de descargar en formato CSV
- [ ] Mostrar preview del Excel antes de descargar
- [ ] Agregar cancelación de procesamiento
- [ ] Guardar historial de procesamiento
- [ ] Notificaciones sonoras cuando complete
- [ ] Opción de procesar múltiples proyectos en batch
