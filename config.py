"""
Configuración centralizada del sistema OCR.
"""
import os

# ===============================
# RUTAS DE ARCHIVOS Y DIRECTORIOS
# ===============================
PDF_PATH = "pdf_ejemplo/ejemplo_scan127.pdf"  # PDF de entrada
IMG_DIR = "images_scaled"  # Imágenes redimensionadas
OUT_DIR = "output_ocr"  # Resultados de OCR y JSON
OUT_ANNOTATED = "output_real"  # Imágenes anotadas en resolución original
JSON_OUTPUT = "output_ocr/ocr_results.json"  # Resultado consolidado

# ===============================
# PARÁMETROS DE OCR
# ===============================
MAX_SIDE = 850  # Tamaño máximo para optimización (px)
CPU_THREADS = 4  # Hilos de CPU para OCR
MIN_CONFIDENCE = 0.5  # Confianza mínima para aceptar resultados (0.0 - 1.0)

# ===============================
# DIVISIÓN POR PALABRAS
# ===============================
SPLIT_BY_WORDS = True  # True = dividir boxes por palabra, False = mantener por línea
WORD_SPACING_THRESHOLD = 0.1  # Factor para detectar espacios entre palabras (0.1 = 10% del ancho promedio de caracteres)

# ===============================
# SALIDAS OPCIONALES
# ===============================
GENERATE_VISUALIZATIONS = True  # True = generar imágenes con boxes dibujados
GENERATE_ANNOTATED_PDF = True   # True = generar PDF con boxes de colores
GENERATE_SEARCHABLE_PDF = False  # True = generar PDF con texto seleccionable
GENERATE_EDITABLE_PDF = True    # True = generar PDF con texto editable

# ===============================
# LÍMITES DE PROCESAMIENTO
# ===============================
MAX_FILE_SIZE_MB = 50          # Tamaño máximo del PDF
MAX_PAGES = 100                # Número máximo de páginas
MAX_PROCESSING_TIME_SEC = 300  # Timeout en segundos (5 min) - detiene todo al alcanzar límite
WARN_FILE_SIZE_MB = 20         # Advertir si supera este tamaño
WARN_PAGES = 50                # Advertir si supera este número

# ===============================
# REGISTRO DE RENDIMIENTO
# ===============================
ENABLE_PROFILING = True                    # True = registrar tiempos y rendimiento
PROFILE_OUTPUT_DIR = "output_ocr/profiles"  # Directorio para guardar registros de rendimiento
PROFILE_SAVE_JSON = True                    # Guardar perfil en JSON
PROFILE_SHOW_SUMMARY = True                 # Mostrar resumen al final

# ===============================
# VARIABLES DE ENTORNO
# ===============================
os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

# ===============================
# CREAR DIRECTORIOS
# ===============================
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(OUT_ANNOTATED, exist_ok=True)
