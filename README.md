# 🌍 GlyphAtlas PDF
### Deciphering Content. Mapping Context.

> Motor de procesamiento inteligente para documentos PDF. Descifra (Glyph) el contenido y mapea (Atlas) su estructura espacial para editores.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)]()
[![Format](https://img.shields.io/badge/Format-PDF-red.svg)]()

---

## 🚀 ¿Qué es GlyphAtlas PDF?

**GlyphAtlas PDF** es un motor de backend diseñado para transformar archivos PDF en estructuras de datos editables. 

A diferencia de un OCR tradicional que solo extrae texto plano, **GlyphAtlas PDF** genera un mapa de coordenadas `(x, y, w, h)` preciso, fusionando la capa de texto nativo del PDF con el reconocimiento visual de PaddleOCR.

### 🎯 Objetivo
Permitir que cualquier editor de PDF pueda "entender" dónde está cada palabra, ya sea en un documento digital limpio o en un escaneo antiguo.Sistema profesional de OCR que detecta automáticamente el tipo de documento y aplica el procesamiento óptimo. Incluye validaciones, profiling, timeouts y múltiples formatos de salida.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PaddleOCR](https://img.shields.io/badge/PaddleOCR-3.3.3-green.svg)](https://github.com/PaddlePaddle/PaddleOCR)


---

## ✨ Características Principales

### 🎯 Procesamiento Inteligente
- **Detección automática de tipo de PDF**: Distingue entre texto nativo, mixto o escaneado
- **Procesamiento optimizado**: Evita OCR innecesario en documentos con texto seleccionable
- **Transformación de coordenadas**: Para imágenes embebidas en PDFs mixtos
- **División por palabras**: Extrae bounding boxes a nivel de palabra (configurable)

### 🛡️ Protecciones y Validaciones
- **Límites configurables**: Tamaño máximo, número de páginas
- **Timeout automático**: Detiene procesamiento si excede tiempo límite
- **Advertencias proactivas**: Estimación de tiempo antes de procesar
- **Validación de archivos**: Verifica integridad y compatibilidad

### 📊 Análisis de Rendimiento
- **Profiling automático**: Registra tiempos por etapa
- **Detección de hardware**: Identifica CPU/GPU disponibles
- **Métricas detalladas**: Páginas/seg, MB/seg, tiempo por etapa
- **Análisis histórico**: Compara rendimiento entre ejecuciones

### 📄 Múltiples Formatos de Salida
- **JSON estructurado**: Resultados completos con metadata
- **PDF anotado**: Boxes de colores sobre el documento original
- **PDF seleccionable**: Texto invisible para búsqueda y copia
- **PDF editable**: Texto visible y modificable
- **Visualizaciones**: Imágenes con boxes dibujados

### 🔧 Herramientas Adicionales
- **Sistema de censura**: Oculta información sensible (emails, teléfonos, DNI)
- **Análisis de rendimiento**: Estadísticas comparativas históricas

---

## 📁 Estructura del Proyecto

```
OCR_paddle/
├── main_refactored.py          # 🎯 Script principal modular
├── config.py                    # ⚙️ Configuración centralizada
├── pyproject.toml               # 📦 Dependencias (uv)
├── README.md                    # 📖 Este archivo
├── ARCHITECTURE.md              # 📐 Documentación técnica detallada
│
├── src/                         # 📦 Código fuente modular
│   ├── pdf/                     # 📄 Procesamiento de PDFs
│   │   ├── analyzer.py          # Detección tipo de PDF
│   │   ├── text_extractor.py    # Extracción texto nativo
│   │   ├── image_extractor.py   # Extracción imágenes embebidas
│   │   ├── converter.py         # Conversión PDF → imágenes
│   │   └── generator.py         # Generación PDFs mejorados
│   │
│   ├── ocr/                     # 🔍 Motor OCR
│   │   ├── engine.py            # Inicialización y ejecución
│   │   └── word_splitter.py     # División por palabras
│   │
│   ├── visualization/           # 🎨 Visualización
│   │   └── drawer.py            # Dibujo de boxes
│   │
│   └── utils/                   # 🛠️ Utilidades
│       ├── io.py                # Entrada/Salida
│       ├── validators.py        # Validación de PDFs
│       └── profiler.py          # Profiling de rendimiento
│
├── tools/                       # 🔧 Herramientas
│   ├── censura.py               # Sistema de censura
│   └── analyze_performance.py   # Análisis de perfiles
│
├── output_ocr/                  # 📁 Resultados
│   └── profiles/                # 📊 Perfiles de rendimiento
├── output_real/                 # 🖼️ Visualizaciones
├── images_scaled/               # 📸 Temporales
└── pdf_ejemplo/                 # 📚 PDFs de prueba
```

---

## 🚀 Instalación

### Requisitos
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (gestor de paquetes)
- Windows/Linux/macOS

### Pasos

```bash
# 1. Clonar el repositorio
cd tu-carpeta-destino
git clone https://github.com/Mahynlo/glyphatlas-pdf.git

# 2. Instalar dependencias
uv sync

```

---

## ⚙️ Configuración

Edita [`config.py`](config.py) para personalizar:

### Rutas
```python
PDF_PATH = "mi_documento.pdf"          # PDF a procesar
OUT_DIR = "output_ocr"                 # Directorio de salida
```

### Parámetros OCR
```python
MAX_SIDE = 850                         # Resolución máxima (px)
CPU_THREADS = 4                        # Hilos de CPU
MIN_CONFIDENCE = 0.5                   # Confianza mínima (0.0-1.0)
```

### División por Palabras
```python
SPLIT_BY_WORDS = True                  # True = palabras, False = líneas
WORD_SPACING_THRESHOLD = 0.1           # Factor de espaciado
```

### Salidas Opcionales
```python
GENERATE_VISUALIZATIONS = True         # Imágenes con boxes
GENERATE_ANNOTATED_PDF = True          # PDF con boxes de colores
GENERATE_SEARCHABLE_PDF = True         # PDF seleccionable
GENERATE_EDITABLE_PDF = True           # PDF editable
```

### Límites de Procesamiento
```python
MAX_FILE_SIZE_MB = 50                  # Tamaño máximo PDF
MAX_PAGES = 100                        # Páginas máximas
MAX_PROCESSING_TIME_SEC = 300          # Timeout (5 min)
WARN_FILE_SIZE_MB = 20                 # Umbral advertencia tamaño
WARN_PAGES = 50                        # Umbral advertencia páginas
```

### Profiling
```python
ENABLE_PROFILING = True                # Activar registro de rendimiento
PROFILE_OUTPUT_DIR = "output_ocr/profiles"
PROFILE_SAVE_JSON = True               # Guardar perfiles en JSON
PROFILE_SHOW_SUMMARY = True            # Mostrar resumen al final
```

---

## 📖 Uso

### Básico

```bash
# Procesar PDF
uv run python main_refactored.py
```

### Ejemplos de Salida

**Validación automática:**
```
📊 Validando PDF...
  📦 Tamaño: 15.30 MB
  📄 Páginas: 35
  ✅ Validación exitosa
```

**Detección de tipo:**
```
📝🖼️ Tipo de documento: Texto nativo + imágenes (OCR solo para imágenes)
   Total: 35 páginas | 32 con texto | 8 con imágenes
```

**Procesamiento:**
```
📝 PASO 2A: Extraer texto nativo
  ✓ Página 1: 245 palabras extraídas
  
🖼️ PASO 2B: Extraer y procesar imágenes embebidas
🔍 OCR en imagen de página 5
  ✓ 18 textos detectados y transformados
```

**Resumen de rendimiento:**
```
📊 RESUMEN DE RENDIMIENTO
============================================================
💻 Hardware:
  Sistema: Windows 11
  CPU: 8 núcleos

📄 PDF Procesado:
  Tipo: text_and_images
  Páginas: 35
  Tamaño: 15.3 MB

⏱️  Rendimiento:
  Tiempo total: 52.45 segundos (0.87 min)
  Velocidad: 0.67 páginas/seg

📈 Desglose por Etapas:
  Procesamiento híbrido: 48.12s (91.7%)
  División por palabras: 1.83s (3.5%)
  ...
```

---

## 📊 Análisis de Rendimiento

```bash
# Ver análisis histórico de todos los perfiles
uv run python tools/analyze_performance.py
```

**Ejemplo de salida:**
```
📊 RENDIMIENTO POR TIPO DE PDF
============================================================
📄 TEXT_AND_IMAGES
  Documentos procesados: 12
  Tiempo promedio: 45.32s
  Velocidad promedio: 0.63 pág/seg

💻 RENDIMIENTO POR HARDWARE
============================================================
⚙️  CPU
  Ejecuciones: 15
  Velocidad promedio: 0.64 pág/seg

⚙️  GPU
  Ejecuciones: 2
  Velocidad promedio: 9.42 pág/seg  (14x más rápido!)
```

---

## 🔧 Herramienta de Censura

```python
from tools.censura import (
    censurar_emails,
    censurar_telefonos,
    censurar_dni
)

# Cargar resultados OCR
with open("output_ocr/ocr_results.json") as f:
    resultados = json.load(f)

# Censurar información sensible
censurar_emails("documento.pdf", resultados, "documento_censurado.pdf")
censurar_telefonos("documento.pdf", resultados, "documento_censurado.pdf")
censurar_dni("documento.pdf", resultados, "documento_censurado.pdf")
```

---

## 🎯 Casos de Uso

### 1. PDF Solo con Texto
- ✅ Extracción directa sin OCR (instantáneo)
- ✅ Coordenadas exactas por palabra
- ✅ PDF seleccionable y editable

### 2. PDF Mixto (Texto + Imágenes)
- ✅ Texto nativo: extracción directa
- ✅ Imágenes: OCR con transformación de coordenadas
- ✅ Resultados combinados

### 3. Documento Escaneado
- ✅ OCR completo en todas las páginas
- ✅ División por palabras opcional
- ✅ Visualización con boxes

---

## 📊 Formatos de Salida

### 1. JSON Estructurado (`ocr_results.json`)

```json
{
  "metadata": {
    "pdf_type": "text_and_images",
    "timestamp": "2026-01-24 15:30:45"
  },
  "pages": [
    {
      "page_num": 1,
      "text_regions": [
        {
          "bbox": [[x0,y0], [x1,y1], [x2,y2], [x3,y3]],
          "text": "palabra",
          "confidence": 0.98,
          "source": "native",
          "is_word": true
        }
      ]
    }
  ]
}
```

### 2. PDF Anotado

- 🟢 Verde: Texto nativo
- 🟠 Naranja: OCR de imágenes
- 🔴 Rojo: OCR de páginas escaneadas

### 3. PDF Seleccionable

Texto invisible para búsqueda/copia (Ctrl+F funciona)

### 4. PDF Editable

Texto visible y modificable en cualquier editor PDF

---

### Procesamiento muy lento

1. ✅ Usa GPU (14x speedup)
2. ✅ Desactiva salidas opcionales no necesarias
3. ✅ Reduce `MAX_SIDE` a 640px

### "Límite de tiempo alcanzado"

```python
# Aumentar timeout en config.py
MAX_PROCESSING_TIME_SEC = 600  # 10 minutos
```

---

## 📝 Notas Técnicas

### Coordenadas

- **Texto nativo**: Coordenadas exactas de PyMuPDF
- **OCR**: Coordenadas transformadas del espacio de imagen al espacio PDF
- **Formato**: `[[x0,y0], [x1,y1], [x2,y2], [x3,y3]]` (4 puntos)

### Fuentes de Texto

- `native`: Texto seleccionable del PDF
- `ocr_from_image`: OCR de imágenes embebidas
- `scanned`: OCR de documento escaneado completo

---

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## 📄 Licencia

MIT License - ver archivo LICENSE para detalles

---

## 🙏 Agradecimientos

- [PaddleOCR](https://github.com/PaddlePaddle/PaddleOCR) - Motor OCR
- [PyMuPDF](https://pymupdf.readthedocs.io/) - Manipulación de PDFs
- [Pillow](https://python-pillow.org/) - Procesamiento de imágenes

---

## 📚 Documentación Adicional

- [`ARCHITECTURE.md`](ARCHITECTURE.md) - Arquitectura técnica detallada
- [`config.py`](config.py) - Todas las opciones de configuración
- [`tools/`](tools/) - Herramientas auxiliares

---
