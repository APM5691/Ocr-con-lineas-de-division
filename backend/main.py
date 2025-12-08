from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from pdf2image import convert_from_path
from PIL import Image
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from concurrent.futures import ProcessPoolExecutor, as_completed
import os
import gc


app = FastAPI(title="PDF OCR Lines Manager", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_PATH = Path("storage")
UPLOADS_PATH = STORAGE_PATH / "uploads"
PROJECTS_PATH = STORAGE_PATH / "projects"

STORAGE_PATH.mkdir(exist_ok=True)
UPLOADS_PATH.mkdir(exist_ok=True)
PROJECTS_PATH.mkdir(exist_ok=True)

current_project = None

def process_image(image_data):
    """
    Procesa una imagen individual: guarda original y versión reducida
    Esta función se ejecuta en procesos separados (sin bloqueos de GIL)
    
    Args:
        image_data: tuple (page_num, img_original, originales_path, baja_calidad_path)
    
    Returns:
        tuple (filename, success, error_msg)
    """
    try:
        page_num, img_original, originales_path_str, baja_calidad_path_str = image_data
        
        originales_path = Path(originales_path_str)
        baja_calidad_path = Path(baja_calidad_path_str)
        
        original_filename = f"img_{page_num:03d}.jpg"
        
        # Guardar original en alta calidad (98% JPEG quality)
        original_file_path = originales_path / original_filename
        img_original.save(str(original_file_path), "JPEG", quality=98)
        
        # Liberar memoria de la imagen original inmediatamente
        img_original.close()
        
        # Crear versión de baja calidad para frontend (más rápida de cargar)
        max_width = 800
        width_percent = max_width / img_original.width if img_original.width > 0 else 1
        new_height = max(1, int(img_original.height * width_percent)) if img_original.height > 0 else 800
        
        # Cargar imagen desde disco (ya guardada) para procesamiento de baja calidad
        temp_img = Image.open(original_file_path)
        img_baja = temp_img.resize((max_width, new_height), Image.Resampling.LANCZOS)
        
        baja_file_path = baja_calidad_path / original_filename
        img_baja.save(str(baja_file_path), "JPEG", quality=55)
        
        img_baja.close()
        temp_img.close()
        
        return (original_filename, True, None)
    
    except Exception as e:
        return (None, False, str(e))

class LinesData(BaseModel):
    lines: dict
    line_gap: Optional[float] = 6.5

class ProjectInfo(BaseModel):
    project: str
    status: str
    created_at: Optional[str] = None
    total_images: Optional[int] = None
    images: Optional[List[str]] = None

@app.get("/health")
async def health_check():
    """Verificar estado de la API"""
    return {
        "status": "healthy",
        "service": "PDF OCR Lines Manager",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Sube un PDF y lo convierte a imágenes (alta y baja calidad)
    Crea carpetas: originales (300dpi) y baja_calidad (reducidas)
    """
    global current_project
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Solo se aceptan archivos PDF")
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        project_name = f"proyecto_{timestamp}"
        project_path = PROJECTS_PATH / project_name
        
        print(f"Procesando PDF: {file.filename} como proyecto '{project_name}'")
        
        # Crear estructura de carpetas
        baja_calidad_path = project_path / "baja_calidad"
        originales_path = project_path / "originales"
        procesadas_path = project_path / "procesadas"
        
        baja_calidad_path.mkdir(parents=True, exist_ok=True)
        originales_path.mkdir(parents=True, exist_ok=True)
        procesadas_path.mkdir(parents=True, exist_ok=True)
        
        # Guardar archivo PDF original
        pdf_path = UPLOADS_PATH / f"{project_name}.pdf"
        with open(pdf_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Convertir PDF a imágenes con alta calidad (150 DPI - balance calidad/velocidad)
        print(f"Convirtiendo PDF a imágenes (150 DPI)...")
        
        try:
            # Usar 150 DPI en lugar de 300 (más rápido, sigue siendo alta calidad)
            images = convert_from_path(pdf_path, dpi=150, fmt='jpeg')
            print(f"✓ PDF convertido a {len(images)} imágenes")
        except Exception as e:
            print(f"✗ Error al convertir PDF: {str(e)}")
            raise HTTPException(500, f"Error convirtiendo PDF: {str(e)}")
        
        image_list = []
        
        # Preparar datos para procesamiento en lotes
        num_workers = min(os.cpu_count() or 4, 4)  # Limitar a máximo 4 para no saturar memoria
        batch_size = max(5, os.cpu_count() or 4)  # Procesar en lotes pequeños
        
        print(f"Total: {len(images)} imágenes")
        print(f"Procesando en lotes de {batch_size} con {num_workers} workers...")
        
        # Procesar en lotes para no saturar memoria
        for batch_start in range(0, len(images), batch_size):
            batch_end = min(batch_start + batch_size, len(images))
            batch = images[batch_start:batch_end]
            
            print(f"\n📦 Procesando lote: imágenes {batch_start + 1} a {batch_end}...")
            
            # Preparar datos del lote actual
            batch_data = [
                (page_num, img, str(originales_path), str(baja_calidad_path))
                for page_num, img in enumerate(batch, start=batch_start + 1)
            ]
            
            # Procesar lote en paralelo
            with ProcessPoolExecutor(max_workers=num_workers) as executor:
                futures = {
                    executor.submit(process_image, img_data): page_num 
                    for page_num, img_data in enumerate(batch_data, start=1)
                }
                
                for future in as_completed(futures):
                    try:
                        filename, success, error = future.result()
                        if success:
                            image_list.append(filename)
                            print(f"  ✓ {filename}")
                        else:
                            print(f"  ✗ Error: {error}")
                    except Exception as e:
                        print(f"  ✗ Error ejecutando tarea: {str(e)}")
            
            # Liberar memoria del lote procesado
            del batch
            import gc
            gc.collect()
            print(f"✅ Lote completado. Memoria liberada.")
        
        # Guardar estado del proyecto
        status_path = project_path / "status.json"
        with open(status_path, "w") as f:
            json.dump({
                "status": "idle",
                "created_at": timestamp,
                "pdf_filename": file.filename,
                "total_pages": len(image_list)
            }, f, indent=2)
        
        current_project = project_name
        
        return {
            "status": "success",
            "project": project_name,
            "total_pages": len(image_list),
            "images": image_list,
            "message": f"PDF procesado: {len(image_list)} páginas"
        }
    
    except Exception as e:
        raise HTTPException(500, f"Error procesando PDF: {str(e)}")

@app.get("/api/images/{filename}")
async def get_image(filename: str, quality: str = "baja"):
    """
    Obtiene una imagen del proyecto actual
    quality: "baja" (para frontend) o "alta" (para procesamiento)
    """
    if not current_project:
        raise HTTPException(400, "No hay proyecto activo")
    
    folder = "baja_calidad" if quality == "baja" else "originales"
    image_path = PROJECTS_PATH / current_project / folder / filename
    
    if not image_path.exists():
        raise HTTPException(404, f"Imagen no encontrada: {filename}")
    
    return FileResponse(image_path)

@app.get("/api/projects")
async def list_projects():
    """Lista todos los proyectos disponibles"""
    try:
        projects = []
        if PROJECTS_PATH.exists():
            for project_dir in PROJECTS_PATH.iterdir():
                if project_dir.is_dir():
                    status_path = project_dir / "status.json"
                    status_data = {}
                    if status_path.exists():
                        with open(status_path) as f:
                            status_data = json.load(f)
                    
                    projects.append({
                        "name": project_dir.name,
                        "status": status_data.get("status", "idle"),
                        "created_at": status_data.get("created_at"),
                        "total_pages": status_data.get("total_pages", 0)
                    })
        
        return {
            "total": len(projects),
            "projects": sorted(projects, key=lambda x: x["created_at"], reverse=True)
        }
    
    except Exception as e:
        raise HTTPException(500, f"Error listando proyectos: {str(e)}")

@app.post("/api/set-project/{project_name}")
async def set_current_project(project_name: str):
    """Establece el proyecto activo y carga sus imágenes y líneas"""
    global current_project
    
    try:
        project_path = PROJECTS_PATH / project_name
        
        if not project_path.exists():
            raise HTTPException(404, f"Proyecto '{project_name}' no encontrado")
        
        current_project = project_name
        
        # Obtener lista de imágenes de baja calidad
        baja_calidad_path = project_path / "baja_calidad"
        images = sorted([f.name for f in baja_calidad_path.glob("*.jpg")])
        
        # Cargar líneas si existen
        json_path = project_path / "lines.json"
        lines = {}
        if json_path.exists():
            with open(json_path) as f:
                lines = json.load(f)
        
        # Obtener status del proyecto
        status_path = project_path / "status.json"
        status = {}
        if status_path.exists():
            with open(status_path) as f:
                status = json.load(f)
        
        return {
            "status": "success",
            "project": project_name,
            "total_images": len(images),
            "images": images,
            "lines": lines,
            "project_status": status.get("status", "idle")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error estableciendo proyecto: {str(e)}")

@app.post("/api/export-lines")
async def export_lines(data: LinesData):
    """
    Exporta las líneas marcadas a un archivo JSON
    El JSON se guarda en la carpeta del proyecto como 'lines.json'
    """
    if not current_project:
        raise HTTPException(400, "No hay proyecto activo")
    
    try:
        project_path = PROJECTS_PATH / current_project
        json_path = project_path / "lines.json"
        
        export_data = {
            "lines": data.lines,
            "line_gap": data.line_gap,
            "exported_at": datetime.now().isoformat(),
            "total_lines": sum(len(v) for v in data.lines.values())
        }
        
        with open(json_path, "w") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        # Actualizar status del proyecto
        status_path = project_path / "status.json"
        if status_path.exists():
            with open(status_path) as f:
                status = json.load(f)
        else:
            status = {"status": "idle"}
        
        status["lines_exported"] = datetime.now().isoformat()
        with open(status_path, "w") as f:
            json.dump(status, f, indent=2)
        
        return {
            "status": "success",
            "message": "Líneas exportadas correctamente",
            "path": str(json_path),
            "total_lines": export_data["total_lines"]
        }
    
    except Exception as e:
        raise HTTPException(500, f"Error exportando líneas: {str(e)}")

@app.get("/api/project/{project_name}/lines")
async def get_project_lines(project_name: str):
    """Obtiene las líneas guardadas de un proyecto específico"""
    try:
        project_path = PROJECTS_PATH / project_name
        
        if not project_path.exists():
            raise HTTPException(404, f"Proyecto '{project_name}' no encontrado")
        
        json_path = project_path / "lines.json"
        
        if not json_path.exists():
            return {"status": "success", "project": project_name, "lines": {}}
        
        with open(json_path) as f:
            lines_data = json.load(f)
        
        return {
            "status": "success",
            "project": project_name,
            "lines": lines_data.get("lines", {}),
            "line_gap": lines_data.get("line_gap", 6.5),
            "exported_at": lines_data.get("exported_at")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error obteniendo líneas: {str(e)}")

@app.delete("/api/project/{project_name}")
async def delete_project(project_name: str):
    """Elimina un proyecto completo (carpeta y archivos)"""
    global current_project
    
    try:
        project_path = PROJECTS_PATH / project_name
        
        if not project_path.exists():
            raise HTTPException(404, f"Proyecto '{project_name}' no encontrado")
        
        # Eliminar carpeta del proyecto
        shutil.rmtree(project_path)
        
        # Eliminar PDF si existe
        pdf_path = UPLOADS_PATH / f"{project_name}.pdf"
        if pdf_path.exists():
            pdf_path.unlink()
        
        # Si era el proyecto activo, desactivar
        if current_project == project_name:
            current_project = None
        
        return {
            "status": "success",
            "message": f"Proyecto '{project_name}' eliminado"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error eliminando proyecto: {str(e)}")

@app.get("/api/project/{project_name}/info")
async def get_project_info(project_name: str):
    """Obtiene información detallada de un proyecto"""
    try:
        project_path = PROJECTS_PATH / project_name
        
        if not project_path.exists():
            raise HTTPException(404, f"Proyecto '{project_name}' no encontrado")
        
        # Contar imágenes
        originales_path = project_path / "originales"
        baja_calidad_path = project_path / "baja_calidad"
        
        total_images = len(list(originales_path.glob("*.jpg"))) if originales_path.exists() else 0
        
        # Obtener status
        status_path = project_path / "status.json"
        status = {}
        if status_path.exists():
            with open(status_path) as f:
                status = json.load(f)
        
        # Obtener líneas
        lines_path = project_path / "lines.json"
        lines_count = 0
        if lines_path.exists():
            with open(lines_path) as f:
                lines_data = json.load(f)
                lines_count = lines_data.get("total_lines", 0)
        
        return {
            "status": "success",
            "project": project_name,
            "created_at": status.get("created_at"),
            "total_pages": status.get("total_pages", total_images),
            "total_lines_marked": lines_count,
            "lines_exported_at": status.get("lines_exported"),
            "pdf_filename": status.get("pdf_filename")
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error obteniendo información: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
