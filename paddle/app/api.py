"""
API FastAPI para Paddle OCR
Permite procesar documentos PDF/imágenes y extraer texto con coordinates
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from paddleocr import PaddleOCR
from fastapi.responses import FileResponse
from ocr_processor import OCRProcessor
import os
from pathlib import Path
import json
from datetime import datetime
from pydantic import BaseModel
import shutil
import pandas as pd
from typing import List, Optional
import traceback

# Inicializar FastAPI
app = FastAPI(
    title="Paddle OCR API",
    description="API para reconocimiento óptico de caracteres con Paddle",
    version="1.0.0"
)

# CORS - Permitir requests desde frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProjectStatus(BaseModel):
    project: str
    status: str  # "idle" | "processing" | "completed" | "error"
    progress: Optional[str] = None
    excel_path: Optional[str] = None
    error_message: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    global ocr_processor
    try:
        ocr_processor = OCRProcessor(lang="es")
        print("✅ OCR Processor inicializado")
    except Exception as e:
        print(f"❌ Error al inicializar OCR: {e}")
        
# Directorios
UPLOAD_DIR = Path("/workspace/uploads")
OUTPUT_DIR = Path("/workspace/outputs")
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


STORAGE_PATH = Path("storage")
UPLOADS_PATH = STORAGE_PATH / "uploads"
PROJECTS_PATH = STORAGE_PATH / "projects"

STORAGE_PATH.mkdir(exist_ok=True)
UPLOADS_PATH.mkdir(exist_ok=True)
PROJECTS_PATH.mkdir(exist_ok=True)

current_project = None
ocr_processor = None


@app.get("/health")
def health_check():
    """Verificar que la API está activa"""
    return {
        "status": "healthy",
        "service": "Paddle OCR API",
        "timestamp": datetime.now().isoformat()
    }

def process_ocr_background(project_name: str, json_filename: str):
    """Procesa OCR en background usando el JSON especificado"""
    try:
        project_path = PROJECTS_PATH / project_name
        status_path = project_path / "status.json"
        
        # Verificar que el proyecto existe
        if not project_path.exists():
            raise Exception(f"Proyecto '{project_name}' no existe")
        
        # Actualizar estado a "processing"
        with open(status_path, "w") as f:
            json.dump({"status": "processing", "started_at": datetime.now().isoformat()}, f)
        
        # Leer el archivo JSON especificado
        json_path = project_path / json_filename
        if not json_path.exists():
            raise Exception(f"Archivo JSON '{json_filename}' no encontrado en {project_path}")
        
        with open(json_path) as f:
            data = json.load(f)
        
        lines_data = data.get("lines", {})
        line_gap = data.get("line_gap", 6.5)
        
        # Usar carpeta de imágenes de alta calidad (originales)
        originales_path = project_path / "originales"
        procesadas_path = project_path / "procesadas"
        
        if not originales_path.exists():
            raise Exception(f"Carpeta 'originales' no encontrada en {project_path}")
        
        procesadas_path.mkdir(exist_ok=True)
        
        all_dfs = []
        total = len(lines_data)
        
        for idx, (filename, line_positions) in enumerate(lines_data.items(), 1):
            # Buscar imagen en carpeta originales (alta calidad)
            original_img = originales_path / filename
            
            if not original_img.exists():
                print(f"⚠️  Imagen no encontrada: {filename}")
                continue
            
            if not line_positions or len(line_positions) == 0:
                print(f"⚠️  Sin líneas para: {filename}")
                continue
            
            # Procesar con OCR
            try:
                cortes = sorted(line_positions)
                df_procesado, img_con_lineas = ocr_processor.procesar_imagen(
                    str(original_img), 
                    cortes=cortes, 
                    line_gap=line_gap
                )
                
                # Guardar imagen procesada
                output_img = procesadas_path / filename
                shutil.copy(img_con_lineas, str(output_img))
                
                all_dfs.append(df_procesado)
                print(f"✅ Procesada {idx}/{total}: {filename}")
                
            except Exception as e:
                print(f"❌ Error procesando {filename}: {e}")
                continue
            
            # Actualizar progreso
            with open(status_path, "w") as f:
                json.dump({
                    "status": "processing",
                    "progress": f"{idx}/{total}",
                    "started_at": data.get("started_at"),
                    "current_file": filename
                }, f)
        
        # Concatenar todos los DataFrames
        if all_dfs:
            df_final = pd.concat(all_dfs, ignore_index=True)
            excel_path = project_path / "resultado.xlsx"
            df_final.to_excel(excel_path, index=False)
            
            # Estado completado
            with open(status_path, "w") as f:
                json.dump({
                    "status": "completed",
                    "completed_at": datetime.now().isoformat(),
                    "excel_path": str(excel_path),
                    "total_rows": len(df_final),
                    "json_used": json_filename
                }, f)
            
            print(f"✅ Procesamiento completado: {project_name}")
        else:
            raise Exception("No se procesó ninguna imagen")
            
    except Exception as e:
        print(f"❌ Error en procesamiento: {e}")
        print(traceback.format_exc())
        # Estado error
        try:
            project_path = PROJECTS_PATH / project_name
            status_path = project_path / "status.json"
            with open(status_path, "w") as f:
                json.dump({
                    "status": "error",
                    "error_message": str(e),
                    "failed_at": datetime.now().isoformat(),
                    "json_used": json_filename
                }, f)
        except:
            pass

class ProcessRequest(BaseModel):
    project: str
    json_filename: str

@app.post("/api/process")
async def start_processing(request: ProcessRequest, background_tasks: BackgroundTasks):
    """Inicia procesamiento OCR con proyecto y JSON especificados"""
    try:
        if not request.project or not request.json_filename:
            raise HTTPException(400, "Parámetros requeridos: 'project' y 'json_filename'")
        
        if ocr_processor is None:
            raise HTTPException(503, "OCR no está inicializado")
        
        project_path = PROJECTS_PATH / request.project
        
        if not project_path.exists():
            raise HTTPException(404, f"Proyecto '{request.project}' no existe")
        
        json_path = project_path / request.json_filename
        
        if not json_path.exists():
            raise HTTPException(404, f"Archivo JSON '{request.json_filename}' no encontrado en proyecto")
        
        # Crear archivo de estado
        status_path = project_path / "status.json"
        with open(status_path, "w") as f:
            json.dump({
                "status": "pending",
                "created_at": datetime.now().isoformat(),
                "project": request.project,
                "json_filename": request.json_filename
            }, f)
        
        # Iniciar procesamiento en background
        background_tasks.add_task(process_ocr_background, request.project, request.json_filename)
        
        return {
            "status": "success",
            "message": "Procesamiento OCR iniciado",
            "project": request.project,
            "json_file": request.json_filename,
            "info": "El proceso continuará aunque cierres el navegador"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error iniciando procesamiento: {str(e)}")

@app.get("/api/process-status/{project}")
async def get_process_status(project: str):
    """Obtiene estado del procesamiento para un proyecto específico"""
    try:
        project_path = PROJECTS_PATH / project
        status_path = project_path / "status.json"
        
        if not project_path.exists():
            raise HTTPException(404, f"Proyecto '{project}' no existe")
        
        if not status_path.exists():
            return ProjectStatus(project=project, status="idle")
        
        with open(status_path) as f:
            status_data = json.load(f)
        
        return ProjectStatus(
            project=project,
            status=status_data.get("status", "idle"),
            progress=status_data.get("progress"),
            excel_path=status_data.get("excel_path"),
            error_message=status_data.get("error_message")
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error obteniendo estado: {str(e)}")

@app.get("/api/download-excel/{project}")
async def download_excel(project: str):
    """Descarga el Excel procesado de un proyecto específico"""
    try:
        project_path = PROJECTS_PATH / project
        excel_path = project_path / "resultado.xlsx"
        
        if not project_path.exists():
            raise HTTPException(404, f"Proyecto '{project}' no existe")
        
        if not excel_path.exists():
            raise HTTPException(404, "Excel no encontrado. Primero procesa el proyecto")
        
        return FileResponse(
            excel_path, 
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"{project}_resultado.xlsx"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error descargando Excel: {str(e)}")

@app.get("/api/projects")
async def list_projects():
    """Lista todos los proyectos disponibles"""
    try:
        projects = []
        if PROJECTS_PATH.exists():
            for project_dir in PROJECTS_PATH.iterdir():
                if project_dir.is_dir():
                    status_path = project_dir / "status.json"
                    status = "idle"
                    if status_path.exists():
                        with open(status_path) as f:
                            status = json.load(f).get("status", "idle")
                    
                    projects.append({
                        "name": project_dir.name,
                        "status": status,
                        "path": str(project_dir)
                    })
        
        return {
            "total": len(projects),
            "projects": sorted(projects, key=lambda x: x["name"])
        }
    
    except Exception as e:
        raise HTTPException(500, f"Error listando proyectos: {str(e)}")

@app.get("/api/project/{project}/json-files")
async def list_json_files(project: str):
    """Lista los archivos JSON disponibles en un proyecto"""
    try:
        project_path = PROJECTS_PATH / project
        
        if not project_path.exists():
            raise HTTPException(404, f"Proyecto '{project}' no existe")
        
        json_files = []
        for json_file in project_path.glob("*.json"):
            if json_file.name != "status.json":
                json_files.append({
                    "filename": json_file.name,
                    "size": json_file.stat().st_size,
                    "modified": datetime.fromtimestamp(json_file.stat().st_mtime).isoformat()
                })
        
        return {
            "project": project,
            "total": len(json_files),
            "files": sorted(json_files, key=lambda x: x["modified"], reverse=True)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error listando archivos JSON: {str(e)}")
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
