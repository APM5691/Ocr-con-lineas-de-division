from paddleocr import PaddleOCR
import pandas as pd
import numpy as np
import unicodedata
import re
import cv2
import os


def check_gpu_available():
    """Verifica si GPU está realmente disponible"""
    try:
        import paddle
        # Verificar si CUDA está disponible
        gpu_available = paddle.device.cuda.is_available()
        print(f"✓ GPU disponible: {gpu_available}")
        return gpu_available
    except Exception as e:
        print(f"⚠️  No se pudo verificar GPU: {e}")
        return False


class OCRProcessor:
    def __init__(self, lang="es", use_fast_model=True, use_gpu=True):
        """
        Inicializa el procesador OCR con optimizaciones
        
        Args:
            lang: Idioma a usar
            use_fast_model: Usar modelos móviles más rápidos (PP-OCRv3_mobile)
            use_gpu: Usar GPU si está disponible
        """
        # Verificar disponibilidad real de GPU
        gpu_available = check_gpu_available() if use_gpu else False
        actual_use_gpu = use_gpu and gpu_available
        
        print(f"🚀 Inicializando OCRProcessor (GPU: {actual_use_gpu}, FastModel: {use_fast_model})...")
        
        try:
            if use_fast_model:
                # Modelos móviles - 10x más rápidos pero ligeramente menos precisos
                self.ocr = PaddleOCR(
                    use_angle_cls=False,
                    use_det=True,
                    use_rec=True,
                    use_cls=False,
                    det_db_thresh=0.3,
                    det_db_box_thresh=0.5,
                    det_db_unclip_ratio=1.6,
                    use_dilation=False,
                    use_gpu=actual_use_gpu,
                    enable_mkldnn=not actual_use_gpu,
                    cpu_threads=8 if not actual_use_gpu else None,
                    lang=lang,
                    ocr_version="PP-OCRv3"
                )
            else:
                # Modelos estándar - más precisos pero más lentos
                self.ocr = PaddleOCR(
                    use_angle_cls=False,
                    use_det=True,
                    use_rec=True,
                    use_cls=False,
                    use_gpu=actual_use_gpu,
                    lang=lang
                )
            
            self.use_fast_model = use_fast_model
            self.use_gpu = actual_use_gpu
            pd.set_option("future.no_silent_downcasting", True)
            print("✅ OCRProcessor listo")
            
        except Exception as e:
            print(f"❌ Error inicializando: {e}")
            print("⚠️  Reintentando sin GPU...")
            
            try:
                self.ocr = PaddleOCR(
                    use_angle_cls=False,
                    use_det=True,
                    use_rec=True,
                    use_cls=False,
                    use_gpu=False,
                    enable_mkldnn=True,
                    cpu_threads=8,
                    lang=lang
                )
                self.use_fast_model = use_fast_model
                self.use_gpu = False
                pd.set_option("future.no_silent_downcasting", True)
                print("✅ OCRProcessor listo (modo CPU)")
            except Exception as e2:
                print(f"❌ Error crítico: {e2}")
                raise

    def clean_text_simple(self, text):
        """Limpia y normaliza el texto"""
        if not isinstance(text, str):
            return text

        default_remove = ["continua...", "continua", "ejemplo", "borrar"]
        s = text.strip()

        # Normalizar y eliminar diacríticos
        s = unicodedata.normalize("NFKD", s)
        s = s.encode("ascii", "ignore").decode("ascii")

        # Eliminar apóstrofes y guiones bajos
        s = re.sub(r"[\'\u2019_]", "", s)

        # Eliminar palabras específicas
        escaped = [re.escape(r) for r in default_remove if r]
        if escaped:
            pattern = r"\b(?:" + "|".join(escaped) + r")\b"
            s = re.sub(pattern, " ", s, flags=re.IGNORECASE)

        # Remover múltiples espacios
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def ocr_to_multidimensional_sections(self, result, line_gap=6.5, cortes=None):
        """Convierte resultado OCR en DataFrame con secciones"""
        texts = result["rec_texts"]
        boxes = result["rec_boxes"]

        # Extraer coordenadas y asociar texto
        data = []
        for text, box in zip(texts, boxes):
            x_min, y_min = box[0], box[1]
            text = self.clean_text_simple(text)
            data.append({"text": text, "x": x_min, "y": y_min})

        # Ordenar por Y y luego por X
        data = sorted(data, key=lambda d: (d["y"], d["x"]))

        # Agrupar por líneas
        ordered_lines = []
        current_line = []
        last_y = None

        for item in data:
            if last_y is None or abs(item["y"] - last_y) <= line_gap:
                current_line.append(item)
            else:
                ordered_lines.append(current_line)
                current_line = [item]
            last_y = item["y"]

        if current_line:
            ordered_lines.append(current_line)

        # Sin cortes
        if not cortes:
            max_len = max(len(line) for line in ordered_lines)
            ordered_filled = [
                [i["text"] for i in line] + [""] * (max_len - len(line))
                for line in ordered_lines
            ]
            return pd.DataFrame(ordered_filled)

        # Con cortes en X
        cortes = sorted(cortes)
        n_sections = len(cortes) + 1

        all_rows = []
        for line in ordered_lines:
            row = [""] * n_sections
            for item in line:
                x = item["x"]
                text = item["text"]

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

    def crear_imagen_con_lineas(self, img_path, promedios, output_dir="./temp_lineas"):
        """Crea imagen con líneas verticales dibujadas"""
        os.makedirs(output_dir, exist_ok=True)

        img = cv2.imread(img_path)
        if img is None:
            raise ValueError(f"No se pudo leer la imagen: {img_path}")

        height, width, _ = img.shape

        # Dibujar cada línea
        for x in promedios:
            color = (0, 255, 0)  # Verde
            thickness = 2
            cv2.line(img, (int(x), 0), (int(x), height), color, thickness)

        # Guardar nueva imagen
        output_path = os.path.join(output_dir, os.path.basename(img_path))
        cv2.imwrite(output_path, img)
        return output_path

    def separar_anio_y_resto(self, texto):
        """Separa año del resto del texto"""
        if not isinstance(texto, str):
            return np.nan, texto
        partes = texto.strip().split(maxsplit=1)
        if len(partes) == 0:
            return np.nan, texto
        primer = partes[0]
        resto = partes[1] if len(partes) > 1 else ""
        if primer.isdigit() and 1900 <= int(primer) <= 2099:
            return primer, resto
        return np.nan, texto

    def procesar_dataframe(self, df):
        """Procesa el dataframe para extraer año, modelo y versión"""
        df = df.copy()

        # Detectar año y resto
        anio_resto = df[1].apply(lambda x: pd.Series(self.separar_anio_y_resto(x)))
        df["año"] = anio_resto[0]
        df["texto"] = anio_resto[1]

        # Propagar el año hacia abajo
        df["año"] = df["año"].ffill()

        # Detectar modelo y versión
        modelos = []
        versiones = []
        modelo_actual = None

        for texto in df["texto"]:
            if isinstance(texto, str) and texto.strip() != "":
                if len(texto.split()) <= 3:
                    modelo_actual = texto.strip()
                    modelos.append(modelo_actual)
                    versiones.append(np.nan)
                else:
                    modelos.append(modelo_actual)
                    versiones.append(texto.strip())
            else:
                modelos.append(modelo_actual)
                versiones.append(np.nan)

        df["modelo"] = modelos
        df["version"] = versiones

        # Reordenar columnas
        columnas_ordenadas = ["año", "modelo", "version"] + [
            col
            for col in df.columns
            if col not in [0, 1, "texto", "modelo", "version", "año"]
        ]

        excel_df = df[columnas_ordenadas]

        # Eliminar filas vacías
        excel_df = excel_df.replace(r"^\s*$", np.nan, regex=True)
        excel_df = excel_df.dropna(how="all")

        return excel_df

    def procesar_imagen(self, img_path, cortes=[120, 680, 800], line_gap=6.5, resize_for_ocr=True):
        """
        Procesa una imagen completa y retorna DataFrame y ruta de imagen con líneas
        
        Args:
            img_path: Ruta de la imagen
            cortes: Posiciones X donde dividir columnas
            line_gap: Espaciado vertical para agrupar líneas
            resize_for_ocr: Redimensionar imagen para OCR más rápido (1200px ancho max)
        """
        # Redimensionar si la imagen es muy grande
        if resize_for_ocr:
            img_temp = cv2.imread(img_path)
            if img_temp is not None:
                h, w = img_temp.shape[:2]
                if w > 1200:
                    # Redimensionar pero mantener proporción
                    scale = 1200 / w
                    img_resized = cv2.resize(img_temp, (1200, int(h * scale)))
                    # Guardar temporalmente
                    temp_path = img_path.replace('.jpg', '_temp.jpg')
                    cv2.imwrite(temp_path, img_resized)
                    img_to_process = temp_path
                else:
                    img_to_process = img_path
            else:
                img_to_process = img_path
        else:
            img_to_process = img_path
        
        # Ejecutar OCR
        res = self.ocr.predict(img_to_process)

        # Convertir a DataFrame
        df = self.ocr_to_multidimensional_sections(
            res[0], line_gap=line_gap, cortes=cortes
        )

        # Crear imagen con líneas (usar original)
        img_con_lineas = self.crear_imagen_con_lineas(img_path, cortes)

        # Procesar dataframe
        df_procesado = self.procesar_dataframe(df)
        
        # Limpiar temporal si se creó
        if resize_for_ocr and img_to_process != img_path:
            try:
                os.remove(img_to_process)
            except:
                pass

        return df_procesado, img_con_lineas

    def procesar_carpeta(
        self, carpeta_path, cortes=[120, 680, 800], line_gap=6.5, limit=None
    ):
        """Procesa todas las imágenes de una carpeta"""
        image_extensions = [".jpg", ".jpeg", ".png", ".bmp"]

        image_files = sorted(
            [
                os.path.join(carpeta_path, f)
                for f in os.listdir(carpeta_path)
                if os.path.splitext(f)[1].lower() in image_extensions
            ],
            key=lambda x: (
                int(os.path.splitext(os.path.basename(x))[0])
                if os.path.splitext(os.path.basename(x))[0].isdigit()
                else os.path.basename(x)
            ),
        )

        if limit:
            image_files = image_files[:limit]

        resultados = []
        for img_path in image_files:
            try:
                df, img_lineas = self.procesar_imagen(img_path, cortes, line_gap)
                resultados.append(
                    {
                        "imagen_original": img_path,
                        "imagen_con_lineas": img_lineas,
                        "dataframe": df,
                    }
                )
            except Exception as e:
                resultados.append({"imagen_original": img_path, "error": str(e)})

        # Concatenar todos los DataFrames
        all_dfs = [r["dataframe"] for r in resultados if "dataframe" in r]
        if all_dfs:
            df_final = pd.concat(all_dfs, ignore_index=True)
            df_final = df_final.replace(r"^\s*$", np.nan, regex=True)
            df_final = df_final.dropna(how="all")
        else:
            df_final = pd.DataFrame()

        return resultados, df_final
