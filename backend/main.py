from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import fitz  # PyMuPDF
from PIL import Image
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
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

class LinesData(BaseModel):
    lines: dict  # {"imagen_001.jpg": [100, 200, 300]}

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    global current_project
    
    if not file.filename.endswith('.pdf'):
        raise HTTPException(400, "Solo archivos PDF")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    project_name = f"proyecto_{timestamp}"
    project_path = PROJECTS_PATH / project_name
    
    baja_calidad_path = project_path / "baja_calidad"
    originales_path = project_path / "originales"
    procesadas_path = project_path / "procesadas"
    
    baja_calidad_path.mkdir(parents=True, exist_ok=True)
    originales_path.mkdir(parents=True, exist_ok=True)
    procesadas_path.mkdir(parents=True, exist_ok=True)
    
    pdf_path = UPLOADS_PATH / f"{project_name}.pdf"
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    pdf_document = fitz.open(pdf_path)
    image_list = []
    
    for page_num in range(len(pdf_document)):
        page = pdf_document[page_num]
        
        # Alta calidad (originales)
        pix_original = page.get_pixmap(matrix=fitz.Matrix(3, 3))
        img_original = Image.frombytes("RGB", [pix_original.width, pix_original.height], pix_original.samples)
        original_filename = f"img_{page_num+1:03d}.jpg"
        img_original.save(originales_path / original_filename, "JPEG", quality=95)
        
        # Baja calidad (para frontend)
        max_width = 800
        width_percent = max_width / img_original.width
        new_height = int(img_original.height * width_percent)
        img_baja = img_original.resize((max_width, new_height), Image.Resampling.LANCZOS)
        img_baja.save(baja_calidad_path / original_filename, "JPEG", quality=70)
        
        image_list.append(original_filename)
    
    pdf_document.close()
    current_project = project_name
    
    return {
        "project": project_name,
        "images": image_list,
        "total": len(image_list)
    }

@app.get("/api/images/{filename}")
async def get_image(filename: str):
    if not current_project:
        raise HTTPException(400, "No hay proyecto activo")
    
    image_path = PROJECTS_PATH / current_project / "baja_calidad" / filename
    if not image_path.exists():
        raise HTTPException(404, "Imagen no encontrada")
    
    return FileResponse(image_path)

@app.get("/api/projects")
async def list_projects():
    projects = [p.name for p in PROJECTS_PATH.iterdir() if p.is_dir()]
    return {"projects": projects, "current": current_project}

@app.post("/api/set-project/{project_name}")
async def set_current_project(project_name: str):
    global current_project
    project_path = PROJECTS_PATH / project_name
    
    if not project_path.exists():
        raise HTTPException(404, "Proyecto no encontrado")
    
    current_project = project_name
    baja_calidad_path = project_path / "baja_calidad"
    images = [f.name for f in baja_calidad_path.glob("*.jpg")]
    
    json_path = project_path / "lines.json"
    lines = {}
    if json_path.exists():
        with open(json_path) as f:
            lines = json.load(f)
    
    return {"project": project_name, "images": sorted(images), "lines": lines}

@app.post("/api/export")
async def export_lines(data: LinesData):
    if not current_project:
        raise HTTPException(400, "No hay proyecto activo")
    
    project_path = PROJECTS_PATH / current_project
    json_path = project_path / "lines.json"
    
    with open(json_path, "w") as f:
        json.dump(data.lines, f, indent=2)
    
    return {"message": "JSON exportado", "path": str(json_path)}

@app.post("/api/process")
async def process_images():
    if not current_project:
        raise HTTPException(400, "No hay proyecto activo")
    
    project_path = PROJECTS_PATH / current_project
    json_path = project_path / "lines.json"
    
    if not json_path.exists():
        raise HTTPException(404, "No se encontró lines.json")
    
    with open(json_path) as f:
        lines_data = json.load(f)
    
    originales_path = project_path / "originales"
    procesadas_path = project_path / "procesadas"
    
    processed_count = 0
    for filename, lines in lines_data.items():
        original_img_path = originales_path / filename
        if not original_img_path.exists():
            continue
        
        img = Image.open(original_img_path)
        # Aquí irá tu lógica de procesamiento con las líneas
        # Por ahora solo copiamos la imagen
        output_path = procesadas_path / f"processed_{filename}"
        img.save(output_path, "JPEG", quality=95)
        processed_count += 1
    
    return {
        "message": "Procesamiento completo",
        "processed": processed_count,
        "output_path": str(procesadas_path)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)