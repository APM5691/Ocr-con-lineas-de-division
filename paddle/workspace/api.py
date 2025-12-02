from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import shutil
from datetime import datetime
import pandas as pd
from ocr_processor import OCRProcessor

app = FastAPI(
    title="OCR Processing API",
    description="API para procesamiento OCR de imágenes con PaddleOCR",
    version="1.0.0",
)

# Inicializar procesador OCR
ocr_processor = None

# Directorios
UPLOAD_DIR = "./uploads"
OUTPUT_DIR = "./outputs"
TEMP_LINEAS_DIR = "./temp_lineas"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(TEMP_LINEAS_DIR, exist_ok=True)


class HealthResponse(BaseModel):
    status: str
    timestamp: str
    ocr_loaded: bool
    libraries: dict
    directories: dict


class ProcessImageResponse(BaseModel):
    success: bool
    imagen_original: str
    imagen_con_lineas: str
    dataframe: List[List]
    shape: tuple
    mensaje: str


class ProcessFolderResponse(BaseModel):
    success: bool
    total_imagenes: int
    procesadas_exitosamente: int
    errores: int
    dataframe_final_shape: tuple
    resultados: List[dict]
    mensaje: str


@app.on_event("startup")
async def startup_event():
    """Inicializa el procesador OCR al arrancar la API"""
    global ocr_processor
    try:
        ocr_processor = OCRProcessor(lang="es")
        print("✅ OCR Processor inicializado correctamente")
    except Exception as e:
        print(f"❌ Error al inicializar OCR Processor: {e}")


@app.get("/", tags=["General"])
async def root():
    """Endpoint raíz con información básica"""
    return {
        "mensaje": "API de Procesamiento OCR",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "process_image": "/process-image",
            "process_folder": "/process-folder",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["General"])
async def health_check():
    """
    Endpoint de salud del sistema.
    Verifica el estado de la API, librerías cargadas y directorios.
    """
    try:
        import paddleocr
        import cv2
        import numpy

        libraries = {
            "paddleocr": (
                paddleocr.__version__ if hasattr(paddleocr, "__version__") else "loaded"
            ),
            "pandas": pd.__version__,
            "numpy": numpy.__version__,
            "opencv": cv2.__version__,
        }

        directories = {
            "uploads": os.path.exists(UPLOAD_DIR),
            "outputs": os.path.exists(OUTPUT_DIR),
            "temp_lineas": os.path.exists(TEMP_LINEAS_DIR),
        }

        return HealthResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            ocr_loaded=ocr_processor is not None,
            libraries=libraries,
            directories=directories,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en health check: {str(e)}")


@app.post("/process-image", response_model=ProcessImageResponse, tags=["OCR"])
async def process_image(
    file: UploadFile = File(...),
    cortes: Optional[str] = Query(
        "120,680,800", description="Cortes en X separados por comas"
    ),
    line_gap: Optional[float] = Query(6.5, description="Gap entre líneas"),
):
    """
    Procesa una imagen individual con OCR.

    - **file**: Archivo de imagen (JPG, PNG, BMP)
    - **cortes**: Posiciones X para dividir en columnas (ej: "120,680,800")
    - **line_gap**: Distancia máxima entre líneas del mismo renglón

    Retorna:
    - Ruta de la imagen procesada con líneas
    - DataFrame en formato array
    - Información sobre el procesamiento
    """
    if ocr_processor is None:
        raise HTTPException(
            status_code=503, detail="OCR Processor no está inicializado"
        )

    # Validar extensión
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png", ".bmp"]:
        raise HTTPException(
            status_code=400,
            detail="Formato de archivo no soportado. Use JPG, PNG o BMP",
        )

    # Guardar archivo temporal
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    temp_filename = f"{timestamp}_{file.filename}"
    temp_path = os.path.join(UPLOAD_DIR, temp_filename)

    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Procesar cortes
        cortes_list = [int(x.strip()) for x in cortes.split(",")]

        # Procesar imagen
        df_procesado, img_con_lineas = ocr_processor.procesar_imagen(
            temp_path, cortes=cortes_list, line_gap=line_gap
        )

        # Convertir DataFrame a lista
        df_array = df_procesado.values.tolist()

        return ProcessImageResponse(
            success=True,
            imagen_original=temp_path,
            imagen_con_lineas=img_con_lineas,
            dataframe=df_array,
            shape=df_procesado.shape,
            mensaje=f"Imagen procesada exitosamente. Shape: {df_procesado.shape}",
        )

    except Exception as e:
        # Limpiar archivo temporal si hay error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(
            status_code=500, detail=f"Error al procesar imagen: {str(e)}"
        )


@app.post("/process-folder", response_model=ProcessFolderResponse, tags=["OCR"])
async def process_folder(
    folder_path: str = Query(..., description="Ruta absoluta o relativa de la carpeta"),
    cortes: Optional[str] = Query(
        "120,680,800", description="Cortes en X separados por comas"
    ),
    line_gap: Optional[float] = Query(6.5, description="Gap entre líneas"),
    limit: Optional[int] = Query(None, description="Límite de imágenes a procesar"),
):
    """
    Procesa todas las imágenes de una carpeta.

    - **folder_path**: Ruta de la carpeta con imágenes
    - **cortes**: Posiciones X para dividir en columnas
    - **line_gap**: Distancia máxima entre líneas del mismo renglón
    - **limit**: Número máximo de imágenes a procesar

    Retorna:
    - Resultados individuales por imagen
    - DataFrame consolidado de todas las imágenes
    - Estadísticas del procesamiento
    """
    if ocr_processor is None:
        raise HTTPException(
            status_code=503, detail="OCR Processor no está inicializado"
        )

    if not os.path.exists(folder_path):
        raise HTTPException(
            status_code=404, detail=f"La carpeta no existe: {folder_path}"
        )

    if not os.path.isdir(folder_path):
        raise HTTPException(
            status_code=400, detail=f"La ruta no es una carpeta: {folder_path}"
        )

    try:
        # Procesar cortes
        cortes_list = [int(x.strip()) for x in cortes.split(",")]

        # Procesar carpeta
        resultados, df_final = ocr_processor.procesar_carpeta(
            folder_path, cortes=cortes_list, line_gap=line_gap, limit=limit
        )

        # Contar éxitos y errores
        exitosos = sum(1 for r in resultados if "dataframe" in r)
        errores = sum(1 for r in resultados if "error" in r)

        # Preparar resultados para JSON
        resultados_json = []
        for r in resultados:
            if "dataframe" in r:
                resultados_json.append(
                    {
                        "imagen_original": r["imagen_original"],
                        "imagen_con_lineas": r["imagen_con_lineas"],
                        "shape": r["dataframe"].shape,
                        "success": True,
                    }
                )
            else:
                resultados_json.append(
                    {
                        "imagen_original": r["imagen_original"],
                        "error": r["error"],
                        "success": False,
                    }
                )

        return ProcessFolderResponse(
            success=True,
            total_imagenes=len(resultados),
            procesadas_exitosamente=exitosos,
            errores=errores,
            dataframe_final_shape=df_final.shape if not df_final.empty else (0, 0),
            resultados=resultados_json,
            mensaje=f"Procesamiento completado. {exitosos} exitosas, {errores} errores",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error al procesar carpeta: {str(e)}"
        )


@app.get("/download-image/{filename}", tags=["Archivos"])
async def download_image(filename: str):
    """
    Descarga una imagen procesada con líneas.

    - **filename**: Nombre del archivo en temp_lineas
    """
    file_path = os.path.join(TEMP_LINEAS_DIR, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    return FileResponse(file_path, media_type="image/jpeg", filename=filename)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
