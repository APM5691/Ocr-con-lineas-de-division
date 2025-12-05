from paddleocr import PaddleOCR
import pandas as pd
import numpy as np
import unicodedata
import re
import cv2
import os


class OCRProcessor:
    def __init__(self, lang="es"):
        """Inicializa el procesador OCR"""
        self.ocr = PaddleOCR(
            use_doc_orientation_classify=False, use_doc_unwarping=False, lang=lang
        )
        pd.set_option("future.no_silent_downcasting", True)

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

    def procesar_imagen(self, img_path, cortes=[120, 680, 800], line_gap=6.5):
        """Procesa una imagen completa y retorna DataFrame y ruta de imagen con líneas"""
        # Ejecutar OCR
        res = self.ocr.predict(img_path)

        # Convertir a DataFrame
        df = self.ocr_to_multidimensional_sections(
            res[0], line_gap=line_gap, cortes=cortes
        )

        # Crear imagen con líneas
        img_con_lineas = self.crear_imagen_con_lineas(img_path, cortes)

        # Procesar dataframe
        df_procesado = self.procesar_dataframe(df)

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
