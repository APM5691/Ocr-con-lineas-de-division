import pandas as pd
import numpy as np
import unicodedata
import json
import re
import cv2
import os


# Configuración separada
PALABRAS_ELIMINAR = [
    "continua", "ejemplo", "borrar", "DEDUCIR", "EL", "COSTO", 
    "DE", "REACONDICIONAMIENTO", "Linea", "Nueva", "Unidades", 
    "Usadas", "Actualizacion", "Nuevas", "Precios", "Lista",
    "Anterior", "Dolares"
]

FRASES_ELIMINAR = [
    "continua",
    "N D",
    "..."
]

SIGNOS_ELIMINAR = [
    "...",
    ":",
    "-",
    "_",
    ".",
    "/",
    "\\",
    "|",
    "(",
    ")",
    "[",
    "]",
    "{",
    "}",
    "¿",
    "?",
    "¡",
    "!",
    "&",
    "@",
    "é",
    "ó",
    "á",
    "í",
    "ú",
    "ñ",
    "ç",
    "ğ",
    "°",
]

def normalizar_unicode(texto):
    """Reemplaza caracteres acentuados con sus equivalentes sin acento."""
    if not isinstance(texto, str):
        return texto
    
    # Paso 1: Normalizar a forma NFD (descompone caracteres acentuados)
    # Ejemplo: é → e + ´ (acento separado)
    texto = unicodedata.normalize("NFD", texto)
    
    # Paso 2: Eliminar solo los acentos (caracteres combinados)
    # pero mantener el carácter base
    # Esto convierte: é → e, ñ → n, ç → c, etc.
    texto = "".join(c for c in texto if unicodedata.category(c) != "Mn")
    
    return texto


def eliminar_caracteres_especiales(texto):
    """Remueve apostrofes y otros caracteres especiales, pero mantiene letras y números."""
    # Apostrofes rectos y curvos
    texto = re.sub(r"[\'\u2019]", "", texto)
    return texto


def eliminar_palabras_completas(texto, palabras):
    """Elimina palabras completas usando word boundaries."""
    if not palabras:
        return texto
    
    escaped = [re.escape(p) for p in palabras if p]
    pattern = r"\b(?:" + "|".join(escaped) + r")\b"
    return re.sub(pattern, " ", texto, flags=re.IGNORECASE)


def eliminar_signos(texto, signos):
    """Elimina signos de puntuación específicos sin dejar espacios extra."""
    # Crear un patrón regex con todos los signos
    if signos:
        # Escapar cada signo y crear alternancia
        escaped = [re.escape(s) for s in signos if s]
        if escaped:
            pattern = "|".join(escaped)
            # Reemplazar directamente por nada (no por espacio)
            texto = re.sub(pattern, "", texto)
    return texto


def limpiar_espacios(texto):
    """Normaliza espacios múltiples y hace trim."""
    return re.sub(r"\s+", " ", texto).strip()


def clean_text_simple(text, palabras=None, frases=None, signos=None):
    """
    Limpia texto eliminando palabras, frases y signos específicos, y reemplaza acentos.
    
    Args:
        text: Texto a limpiar
        palabras: Lista de palabras a eliminar (usa default si es None)
        frases: Lista de frases a eliminar (usa default si es None)
        signos: Lista de signos a eliminar (usa default si es None)
    
    Returns:
        Texto limpio o el input original si no es string
    """
    if not isinstance(text, str):
        return text
    
    # Usar valores por defecto si no se especifican
    palabras = PALABRAS_ELIMINAR if palabras is None else palabras
    frases = FRASES_ELIMINAR if frases is None else frases
    signos = SIGNOS_ELIMINAR if signos is None else signos
    
    texto = text.strip()
    
    # Pipeline de limpieza - ORDEN IMPORTANTE
    # 1. Normalizar unicode PRIMERO (reemplaza é → e, ñ → n, etc.)
    texto = normalizar_unicode(texto)
    
    # 2. Primero eliminar signos especiales
    texto = eliminar_signos(texto, signos)
    
    # 3. Eliminar caracteres especiales (apostrofes, etc.)
    texto = eliminar_caracteres_especiales(texto)
    
    # 4. Eliminar palabras/frases
    texto = eliminar_palabras_completas(texto, frases + palabras)
    
    # 5. Limpiar espacios finales
    texto = limpiar_espacios(texto)
    
    return texto


def ocr_to_multidimensional_sections(result, line_gap=6.5, cortes=None):
    texts = result["rec_texts"]
    boxes = result["rec_boxes"]

    # Extraer coordenadas y asociar texto
    data = []
    for text, box in zip(texts, boxes):
        x_min, y_min = box[0], box[1]  # esquina superior izq
        text = clean_text_simple(text)
        data.append({"text": text, "x": x_min, "y": y_min})

    # Ordenar primero por Y (vertical) y luego por X (horizontal)
    data = sorted(data, key=lambda d: (d["y"], d["x"]))

    # Agrupamos por líneas (Y)
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

    # Si no se pasan cortes, devolvemos normal
    if not cortes:
        max_len = max(len(line) for line in ordered_lines)
        ordered_filled = [
            [i["text"] for i in line] + [""] * (max_len - len(line))
            for line in ordered_lines
        ]
        return pd.DataFrame(ordered_filled)

    # --- Usar cortes en X para dividir en secciones ---
    cortes = sorted(cortes)  # [178, 286, 373] por ejemplo
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


def buscar_en_fila(row, columnas_indices, valores_buscar):
    """
    Busca valores en múltiples columnas de una fila

    Args:
        row: fila del DataFrame
        columnas_indices: lista de índices de columnas a buscar [0,1,2,3]
        valores_buscar: set de valores a buscar

    Returns:
        valor encontrado o None
    """
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
    """
    Detecta y propaga marcas y modelos en el DataFrame

    Args:
        df: DataFrame a procesar
        marcas_validas: set de marcas válidas
        modelos_por_marca: dict {marca: set(modelos)}
        columnas: lista de índices de columnas donde buscar

    Returns:
        tuple (lista_marcas, lista_modelos)
    """
    marcas = []
    modelos = []
    marca_actual = None
    modelo_actual = None

    for idx, row in df.iterrows():
        # Buscar marca en cualquier columna
        marca_encontrada = buscar_en_fila(row, columnas, marcas_validas)
        if marca_encontrada:
            marca_actual = marca_encontrada
            # ✅ Solo resetea si la marca REALMENTE cambió
            if marca_actual != (marcas[-1] if marcas else None):
                modelo_actual = None
            print(f"Fila {idx}: Nueva marca → {marca_actual}")

        # Buscar modelo
        if marca_actual and marca_actual in modelos_por_marca:
            modelo_encontrado = buscar_en_fila(
                row, columnas, modelos_por_marca[marca_actual]
            )
            if modelo_encontrado:
                modelo_actual = modelo_encontrado
                print(f"Fila {idx}: Nuevo modelo → {modelo_actual}")
            # ✅ Si no encuentra modelo, mantiene modelo_actual (propagación)

        marcas.append(marca_actual)
        modelos.append(modelo_actual)

    return marcas, modelos


def separar_anio_y_resto_mejorado(texto):
    """Separa año del resto del texto, detectando patrones como 2024, 2023Q2, etc."""
    if pd.isna(texto) or texto == "":
        return pd.Series([np.nan, ""])

    texto_str = str(texto).strip()

    import re

    # Patrón 1: Año seguido de Q y número (2023Q2, 2024Q1, etc.)
    match = re.match(r"^(\d{4})Q\d+", texto_str, re.IGNORECASE)
    if match:
        anio = match.group(1)
        print(f"  Detectado año con trimestre: {texto_str} → año: {anio}")
        return pd.Series([anio, ""])

    # Patrón 2: Año seguido de espacio y texto (2024 5p Dynamic...)
    match = re.match(r"^(\d{4})\s+(.+)", texto_str)
    if match:
        return pd.Series([match.group(1), match.group(2)])

    # Patrón 3: Solo año (2024, 2023, etc.)
    match = re.match(r"^(\d{4})$", texto_str)
    if match:
        return pd.Series([match.group(1), ""])

    return pd.Series([np.nan, texto_str])


def crear_imagenes_con_lineas(promedios, image_files):
    output_dir = "./imagenes_con_lineas"
    os.makedirs(output_dir, exist_ok=True)

    for img_path in image_files:
        img = cv2.imread(img_path)
        if img is None:
            print(f"❌ No se pudo leer: {img_path}")
            continue

        # Obtener dimensiones
        height, width, _ = img.shape

        # Dibujar cada línea
        for x in promedios:
            color = (0, 255, 0)  # Verde
            thickness = 2
            cv2.line(img, (int(x), 0), (int(x), height), color, thickness)

        # Guardar nueva imagen
        output_path = os.path.join(output_dir, os.path.basename(img_path))
        cv2.imwrite(output_path, img)
        print(f"✅ Guardada: {output_path}")

def _normalize_text(s):
    if s is None:
        return ""
    s = str(s)
    s = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in s if not unicodedata.combining(ch)).strip()

def cargar_datos_referencia(json_path):
    """Carga data.json y devuelve (marcas_validas, modelos_por_marca).
    Acepta estructuras comunes:
      - { "marca1": [...], "marca2": [...] }
      - { "marcas": { "marca1": [...], ... } }
      - [ {"marca":"X","modelos":["a","b"]}, ... ]
    Retorna:
      marcas_validas: lista de marcas (normalizadas)
      modelos_por_marca: dict { marca: [modelos...] } (modelos normalizados)
    """
    if not os.path.isfile(json_path):
        raise FileNotFoundError(f"No existe el archivo: {json_path}")
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    modelos_por_marca = {}
    if isinstance(data, dict):
        # Soportar { "marcas": {...} } o directamente { marca: modelos }
        source = data.get("marcas") if isinstance(data.get("marcas"), dict) else data
        for marca, modelos in source.items():
            marca_norm = _normalize_text(marca)
            if isinstance(modelos, dict):
                modelos_list = list(modelos.keys())
            elif isinstance(modelos, (list, tuple)):
                modelos_list = modelos
            else:
                modelos_list = [modelos]
            modelos_por_marca[marca_norm] = [m for m in (_normalize_text(m) for m in modelos_list) if m]
    elif isinstance(data, list):
        # Soporta lista de objetos {"marca": "...", "modelos": [...]}
        for item in data:
            if not isinstance(item, dict):
                continue
            marca = item.get("marca") or item.get("brand") or item.get("name")
            modelos = item.get("modelos") or item.get("models") or []
            marca_norm = _normalize_text(marca)
            modelos_por_marca[marca_norm] = [m for m in (_normalize_text(m) for m in modelos) if m]
    else:
        raise ValueError("Formato de JSON no reconocido para cargar datos de referencia")
    marcas_validas = list(modelos_por_marca.keys())
    return marcas_validas, modelos_por_marca

def obtener_dos_numeros(inicio, fin, rango):
    """
    Devuelve dos números aleatorios dentro del rango [inicio, fin] basados en el parámetro rango.
    
    Args:
        inicio: valor inicial del rango
        fin: valor final del rango
        rango: parámetro que define el tamaño de los intervalos
    
    Returns:
        tupla con dos números dentro del rango especificado
    """
    aleatorio = np.random.rand()
    numero1 = int(inicio + (fin - inicio) * aleatorio)
    numero2 = int(inicio + (fin - inicio) * ((aleatorio + rango / (fin - inicio)) % 1))
    return numero1, numero2


def encontrar_marca(texto, marcas_validas):
    if pd.isna(texto):
        return None
    
    texto_str = str(texto).strip()
    texto_lower = texto_str.lower()
    
    marcas_ordenadas = sorted(marcas_validas, key=len, reverse=True)
    
    for marca in marcas_ordenadas:
        marca_lower = marca.lower()
        
        if texto_lower == marca_lower:
            return marca
        
        patron = r'\b' + re.escape(marca_lower) + r'\b'
        if re.search(patron, texto_lower):
            return marca
    
    return None