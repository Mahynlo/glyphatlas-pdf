"""
Configuración centralizada del sistema OCR.
"""
import os

# ===============================
# RUTAS DE ARCHIVOS Y DIRECTORIOS
# ===============================
#PDF_PATH = "pdf_ejemplo/searchable_document.pdf"  # PDF de entrada
PDF_PATH = "pdf_ejemplo/ejemplo_scan127.pdf"  # PDF de entrada
IMG_DIR = "images_scaled"  # Imágenes redimensionadas
OUT_DIR = "output_ocr"  # Resultados de OCR y JSON
OUT_ANNOTATED = "output_real"  # Imágenes anotadas en resolución original
JSON_OUTPUT = "output_ocr/ocr_results.json"  # Resultado consolidado

# ===============================
# PARÁMETROS DE OCR
# ===============================
# Motor OCR: "paddleocr" (preciso, lento) o "onnxtr" (rápido, ~4s/pág)
OCR_ENGINE = "onnxtr"  # Cambia a "paddleocr" si necesitas máxima precisión

MAX_SIDE = 1000  # Tamaño máximo para optimización (px)
RENDER_DPI = 300  # DPI para renderizado de PDF (150=rápido, 200=estándar, 300=alta calidad)
CPU_THREADS = 4  # Hilos de CPU para OCR
MIN_CONFIDENCE = 0.5  # Confianza mínima para aceptar resultados (0.0 - 1.0)

# ===============================
# UPSCALING DE IMÁGENES PEQUEÑAS
# ===============================
ENABLE_UPSCALING = True  # Hacer upscaling si imagen es muy pequeña
MIN_IMAGE_SIZE = 1000  # Tamaño mínimo (px). Si es menor, se hace upscaling
UPSCALE_FACTOR = 2.0  # Factor de aumento (2.0 = duplicar tamaño)
# Usa Lanczos + Sharpening + CLAHE (OpenCV, rápido y efectivo)
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
GENERATE_SEARCHABLE_PDF = True  # True = generar PDF con texto seleccionable
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
PROFILE_SHOW_SUMMARY = False                 # Mostrar resumen al final


# ===============================
# Configruacionde terminal
# ===============================
TITULO_APP="🚀 Motor GlyfoAtlas by SMEP-OCR"
ESPACIADO=20


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
