import pandas as pd
import numpy as np
from paddleocr import PaddleOCR
from pathlib import Path
from typing import List, Optional, NamedTuple
import logging
import gc
from PIL import Image
import json
import re
import unicodedata

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ========================
# FUNCIONES DE UTILIDAD
# ========================


def clean_text_simple(text):
    """Limpia texto eliminando caracteres especiales y palabras no deseadas"""
    if not isinstance(text, str):
        return text

    default_remove = [
        "continua...",
        "continua",
        "ejemplo",
        "borrar",
        "...",
        "DEDUCIR",
        "EL",
        "COSTO",
        "DE",
        "REACONDICIONAMIENTO",
        "Linea",
        "Nueva",
        "Unidades",
        "Usadas",
        "-",
        "Actualizacion",
        "Nuevas",
        ".",
        "Precios",
        ":",
        "Lista",
        "N D.",
    ]

    s = text.strip()

    # Normalizar y eliminar diacríticos
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", "ignore").decode("ascii")

    # Eliminar apostrofes y guion bajo
    s = re.sub(r"[\'\u2019_]", "", s)

    # Eliminar palabras no deseadas
    escaped = [re.escape(r) for r in default_remove if r]
    if escaped:
        pattern = r"\b(?:" + "|".join(escaped) + r")\b"
        s = re.sub(pattern, " ", s, flags=re.IGNORECASE)

    # Remover múltiples espacios
    s = re.sub(r"\s+", " ", s).strip()
    return s


def leer_data_in_json(path):
    """Lee archivo JSON"""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data


def cargar_datos_referencia(json_path):
    """Carga marcas y modelos del JSON"""
    json_data = leer_data_in_json(json_path)["rows"]

    marcas_validas = set()
    modelos_por_marca = {}

    for row in json_data:
        marca = row["marca"].upper()
        modelo = row["modelo"].upper()

        marcas_validas.add(marca)
        if marca not in modelos_por_marca:
            modelos_por_marca[marca] = set()
        modelos_por_marca[marca].add(modelo)

    return marcas_validas, modelos_por_marca


def buscar_en_fila(row, columnas_indices, valores_buscar):
    """Busca valores en múltiples columnas de una fila"""
    for idx in columnas_indices:
        if idx < len(row):
            valor_raw = row.iloc[idx]
            if pd.notna(valor_raw):
                valor = str(valor_raw).strip().upper()
                if valor and valor in valores_buscar:
                    return valor
    return None


def detectar_marcas_modelos(
    df, marcas_validas, modelos_por_marca, columnas=[0, 1, 2, 3]
):
    """Detecta y propaga marcas y modelos en el DataFrame"""
    marcas = []
    modelos = []
    marca_actual = None
    modelo_actual = None

    for idx, row in df.iterrows():
        marca_encontrada = buscar_en_fila(row, columnas, marcas_validas)
        if marca_encontrada:
            marca_actual = marca_encontrada
            if marca_actual != (marcas[-1] if marcas else None):
                modelo_actual = None
            logger.info(f"Fila {idx}: Nueva marca → {marca_actual}")

        if marca_actual and marca_actual in modelos_por_marca:
            modelo_encontrado = buscar_en_fila(
                row, columnas, modelos_por_marca[marca_actual]
            )
            if modelo_encontrado:
                modelo_actual = modelo_encontrado
                logger.info(f"Fila {idx}: Nuevo modelo → {modelo_actual}")

        marcas.append(marca_actual)
        modelos.append(modelo_actual)

    return marcas, modelos


def separar_anio_y_resto(texto):
    """Separa año del resto del texto"""
    if pd.isna(texto) or texto == "":
        return pd.Series([np.nan, ""])

    texto_str = str(texto).strip()

    # Patrón 1: Año con trimestre (2023Q2)
    match = re.match(r"^(\d{4})Q\d+", texto_str, re.IGNORECASE)
    if match:
        anio = match.group(1)
        logger.info(f"  Detectado año con trimestre: {texto_str} → {anio}")
        return pd.Series([anio, ""])

    # Patrón 2: Año + espacio + texto
    match = re.match(r"^(\d{4})\s+(.+)", texto_str)
    if match:
        return pd.Series([match.group(1), match.group(2)])

    # Patrón 3: Solo año
    match = re.match(r"^(\d{4})$", texto_str)
    if match:
        return pd.Series([match.group(1), ""])

    return pd.Series([np.nan, texto_str])


# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExcelResult(NamedTuple):
    """Resultado del procesamiento"""

    success: bool
    df: Optional[pd.DataFrame] = None
    output_path: Optional[str] = None
    image_path: Optional[str] = None
    error_msg: Optional[str] = None


class OCRProcessor:
    """
    Procesa imágenes con OCR y genera Excel estructurado

    Acepta array de líneas para dividir texto en secciones
    """

    def __init__(
        self, line_gap: float = 6.5, use_gpu: bool = True, use_fast_model: bool = True
    ):
        """
        Inicializa el procesador

        Args:
            line_gap: Espaciado en líneas para agrupar texto
            use_gpu: Usar GPU si disponible
            use_fast_model: Usar modelo móvil rápido (PP-OCRv3)
        """
        self.line_gap = line_gap
        self.use_gpu = use_gpu
        self.use_fast_model = use_fast_model

        # Inicializar OCR
        try:
            logger.info("🔄 Inicializando PaddleOCR...")
            self.ocr = PaddleOCR(
                use_doc_orientation_classify=False, use_doc_unwarping=False, lang="es"
            )
            logger.info("✅ PaddleOCR inicializado")
        except Exception as e:
            logger.error(f"❌ Error inicializando PaddleOCR: {e}")
            raise

    def procesar_imagen(self, img_path: str, lineas_array: List[float]) -> ExcelResult:
        """
        Procesa imagen con OCR usando array de líneas

        Args:
            img_path: Ruta a la imagen
            lineas_array: Array de posiciones Y de líneas [100, 300, 500]

        Returns:
            ExcelResult con DataFrame procesado
        """
        try:
            img_path = Path(img_path)

            if not img_path.exists():
                return ExcelResult(
                    success=False, error_msg=f"Imagen no encontrada: {img_path}"
                )

            logger.info(
                f"🔍 Procesando {img_path.name} con {len(lineas_array)} líneas..."
            )

            # Ejecutar OCR
            ocr_result = self.ocr.ocr(str(img_path))

            if not ocr_result or not ocr_result[0]:
                return ExcelResult(
                    success=False, error_msg=f"OCR no extrajo texto de {img_path.name}"
                )

            # Convertir OCR a DataFrame
            df = self._ocr_to_dataframe(ocr_result[0], lineas_array)

            logger.info(f"✅ {img_path.name}: {len(df)} registros extraídos")

            # Limpiar memoria
            del ocr_result
            gc.collect()

            return ExcelResult(
                success=True, df=df, output_path=None, image_path=str(img_path)
            )

        except Exception as e:
            logger.error(f"Error adentro procesando {img_path}: {e}")
            return ExcelResult(success=False, error_msg=str(e))

    def _ocr_to_dataframe(self, result, lineas_array=None):
        texts = result["rec_texts"]
        boxes = result["rec_boxes"]

        print(f"✅ OCR extrajo {len(texts)} textos")
        print(f"✅ OCR extrajo {len(boxes)} cajas")
        print("🚀 Ordenando textos por posición...")
        print(f"Líneas para cortes: {lineas_array}")

        # Extraer coordenadas y asociar texto
        data = []
        for text, box in zip(texts, boxes):
            x_min, y_min = box[0], box[1]
            text = text.strip()
            data.append({"text": text, "x": x_min, "y": y_min})

        # Ordenar primero por Y (vertical) y luego por X (horizontal)
        data = sorted(data, key=lambda d: (d["y"], d["x"]))

        # Agrupamos por líneas (Y)
        ordered_lines = []
        current_line = []
        last_y = None

        for item in data:
            if last_y is None or abs(item["y"] - last_y) <= self.line_gap:
                current_line.append(item)
            else:
                ordered_lines.append(current_line)
                current_line = [item]
            last_y = item["y"]

        if current_line:
            ordered_lines.append(current_line)

        # Si no se pasan cortes, devolvemos normal
        if not lineas_array:
            max_len = max(len(line) for line in ordered_lines)
            ordered_filled = [
                [i["text"] for i in line] + [""] * (max_len - len(line))
                for line in ordered_lines
            ]
            return pd.DataFrame(ordered_filled)

        # --- Usar cortes en X para dividir en secciones ---
        cortes = sorted(lineas_array)
        n_sections = len(cortes) + 1

        all_rows = []
        for line in ordered_lines:
            row = [""] * n_sections
            for item in line:
                x = item["x"]
                text = item["text"]

                # Buscar en qué sección cae
                section_idx = 0
                for c in cortes:
                    if x > c:
                        section_idx += 1
                    else:
                        break
                row[section_idx] += " " + text if row[section_idx] else text

            all_rows.append(row)

        df = pd.DataFrame(all_rows)
        return df

    def procesar_lote_completo(self, carpeta_originales: str, json_data: dict) -> dict:
        """
        Procesa múltiples imágenes con sus arrays de líneas

        Args:
            carpeta_originales: Ruta a carpeta con imágenes
            json_data: Dict con estructura {'lines': {'imagen.jpg': [100, 300, ...]}}

        Returns:
            Dict con resultados por imagen
        """
        resultados = {}
        carpeta = Path(carpeta_originales)

        lines_data = json_data.get("lines", {})
        total = len(lines_data)

        logger.info(f"🚀 Iniciando procesamiento de {total} imágenes...")

        for idx, (filename, lineas_array) in enumerate(lines_data.items(), 1):
            img_path = carpeta / filename

            if not img_path.exists():
                logger.warning(f"⚠️ [{idx}/{total}] No encontrada: {filename}")
                continue

            result = self.procesar_imagen(str(img_path), lineas_array)
            resultados[filename] = result

            progress = int((idx / total) * 100)
            logger.info(f"[{progress}%] {idx}/{total} procesadas")

        return resultados

    def generar_excel(self, dfs: List[pd.DataFrame], output_path: str) -> bool:
        """
        Genera archivo Excel a partir de lista de DataFrames

        Args:
            dfs: Lista de DataFrames procesados
            output_path: Ruta donde guardar Excel

        Returns:
            True si se guardó correctamente
        """
        try:
            if not dfs:
                logger.error("No hay DataFrames para guardar")
                return False

            # Concatenar todos los DataFrames
            df_final = pd.concat(dfs, ignore_index=True)

            # Guardar Excel
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            df_final.to_excel(output_path, index=False)

            logger.info(f"✅ Excel guardado: {output_path} ({len(df_final)} registros)")
            return True

        except Exception as e:
            logger.error(f"❌ Error guardando Excel: {e}")
            return False

    def procesar_excel_completo(self, input_df, json_path, output_path):
        """Procesa el Excel completo con marca, modelo, año y versión"""
        try:
            logger.info("=== Procesando Excel Completo ===")

            # 1. Cargar datos de referencia
            logger.info("Cargando datos de referencia...")
            marcas_validas, modelos_por_marca = cargar_datos_referencia(json_path)
            logger.info(
                f"Marcas: {len(marcas_validas)}, Modelos: {sum(len(v) for v in modelos_por_marca.values())}"
            )

            # 2. Copiar DataFrame
            df = input_df.copy()

            # 3. Detectar marcas y modelos
            logger.info("Detectando marcas y modelos...")
            marcas, modelos = detectar_marcas_modelos(
                df, marcas_validas, modelos_por_marca, columnas=[0, 1, 2, 3]
            )
            df["marca"] = marcas
            df["modelo"] = modelos

            # 4. Detectar año y texto
            logger.info("Procesando años...")
            anio_resto = df.iloc[:, 1].apply(separar_anio_y_resto)
            df["año"] = anio_resto[0]
            df["texto"] = anio_resto[1]
            df["año"] = df["año"].ffill()

            # 5. Detectar versiones
            logger.info("Detectando versiones...")
            versiones = []
            for idx, texto in enumerate(df["texto"]):
                modelo_actual = df["modelo"].iloc[idx]
                if modelo_actual and isinstance(texto, str) and texto.strip():
                    texto_upper = texto.strip().upper()
                    versiones.append(
                        texto.strip() if texto_upper != modelo_actual else np.nan
                    )
                else:
                    versiones.append(np.nan)
            df["version"] = versiones

            # 6. Agregar valores originales
            df["valor_c"] = df.iloc[:, 2] if len(df.columns) > 2 else np.nan
            df["valor_d"] = df.iloc[:, 3] if len(df.columns) > 3 else np.nan

            # 7. Reordenar columnas
            columnas_base = ["marca", "modelo", "año", "version", "valor_c", "valor_d"]
            columnas_extras = [
                col
                for col in df.columns
                if col not in columnas_base + [0, 1, 2, 3, "texto"]
            ]
            excel_df = df[columnas_base + columnas_extras]

            # 8. Guardar
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            excel_df.to_excel(output_path, index=False, header=False)

            logger.info(f"✅ Excel procesado guardado en: {output_path}")
            logger.info(
                f"Filas: {len(excel_df)}, Marcas únicas: {excel_df['marca'].nunique()}, Modelos: {excel_df['modelo'].nunique()}"
            )

            return excel_df

        except Exception as e:
            logger.error(f"❌ Error procesando Excel: {e}")
            return None
