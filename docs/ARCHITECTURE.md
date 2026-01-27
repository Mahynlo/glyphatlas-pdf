# 🚀 Sistema OCR con PaddleOCR v5

Sistema inteligente de OCR con detección automática de tipo de documento, validaciones, profiling y protecciones integradas.

---

## 📁 Arquitectura del Proyecto

```
OCR_paddle/
├── main_refactored.py       # 🎯 Script principal (nueva versión modular)
├── main.py                   # 📜 Script original (deprecado)
├── config.py                 # ⚙️ Configuración centralizada
├── pyproject.toml            # 📦 Dependencias (uv)
├── README.md                 # 📖 Documentación principal
│
├── docs/                     # 📚 Documentación técnica
│   └── ARCHITECTURE.md       # Este archivo
│
├── src/                      # 📦 Código fuente modular
│   ├── pdf/                  # 📄 Procesamiento de PDFs
│   │   ├── analyzer.py       # Detectar tipo de PDF
│   │   ├── text_extractor.py # Extraer texto nativo
│   │   ├── image_extractor.py # Extraer imágenes embebidas
│   │   ├── converter.py      # Convertir PDF a imágenes
│   │   └── generator.py      # Generar PDFs mejorados
│   │
│   ├── ocr/                  # 🔍 Motor OCR
│   │   ├── engine.py         # Inicializar y ejecutar OCR
│   │   └── word_splitter.py  # Dividir boxes por palabra
│   │
│   ├── visualization/        # 🎨 Visualización
│   │   └── drawer.py         # Dibujar boxes en imágenes
│   │
│   └── utils/                # 🛠️ Utilidades
│       ├── io.py             # Guardar/cargar resultados
│       ├── validators.py     # Validación de PDFs
│       └── profiler.py       # Profiling de rendimiento
│
├── tools/                    # 🔧 Herramientas auxiliares
│   ├── censura.py            # Sistema de censura de documentos
│   └── analyze_performance.py # Análisis de perfiles históricos
│
├── output_ocr/               # 📁 Resultados OCR y JSONs
│   └── profiles/             # 📊 Perfiles de rendimiento
├── output_real/              # 🖼️ Imágenes anotadas en resolución original
├── images_scaled/            # 📸 Imágenes temporales (850px)
├── pdf_ejemplo/              # 📚 PDFs de prueba
└── pruebas/                  # 🧪 Scripts de prueba
```

---

## 🎯 Características Principales

### 1. **Detección Inteligente de Tipo de Documento**
- **Texto Nativo**: Extrae directamente sin OCR
- **Texto + Imágenes**: OCR solo en imágenes embebidas
- **Escaneado**: OCR completo en todas las páginas

### 2. **Procesamiento Optimizado**
- Evita OCR innecesario en documentos con texto nativo
- Transformación de coordenadas para imágenes embebidas
- División automática en palabras (configurable)

### 3. **Validaciones y Protecciones** ⭐ NUEVO
- **Límites configurables**: Tamaño máximo de archivo y número de páginas
- **Timeout automático**: Detiene el procesamiento si excede el límite de tiempo
- **Advertencias proactivas**: Estima tiempo de procesamiento antes de empezar
- **Validación de archivos**: Verifica integridad y compatibilidad

### 4. **Profiling de Rendimiento** ⭐ NUEVO
- **Registro automático**: Mide tiempo por etapa
- **Detección de hardware**: Identifica CPU/GPU disponibles
- **Métricas detalladas**: Páginas/seg, MB/seg, desglose por etapa
- **Análisis histórico**: Compara rendimiento entre ejecuciones

### 5. **Salidas Opcionales Configurables** ⭐ NUEVO
- Activa/desactiva generación de visualizaciones
- Activa/desactiva PDFs mejorados individualmente
- Optimiza velocidad deshabilitando salidas innecesarias

### 6. **Múltiples Salidas**
- **JSON**: Resultados estructurados con metadata
- **PDF Anotado**: Boxes de colores sobre el original
- **PDF Seleccionable**: Texto invisible para búsqueda/copia
- **PDF Editable**: Texto visible y modificable
- **Imágenes**: Visualización con boxes dibujados

---

## ⚙️ Configuración

Edita `config.py`:

```python
# PDF a procesar
PDF_PATH = "mi_documento.pdf"

# Directorios
IMG_DIR = "images_scaled"
OUT_DIR = "output_ocr"
OUT_ANNOTATED = "output_real"

# Parámetros OCR
MAX_SIDE = 850          # Tamaño máximo para optimización (px)
CPU_THREADS = 4         # Hilos de CPU
MIN_CONFIDENCE = 0.5    # Confianza mínima (0.0 - 1.0)

# División por palabras
SPLIT_BY_WORDS = True           # True = palabras, False = líneas
WORD_SPACING_THRESHOLD = 0.1    # Factor de espaciado entre palabras

# Salidas opcionales ⭐ NUEVO
GENERATE_VISUALIZATIONS = True  # Imágenes con boxes dibujados
GENERATE_ANNOTATED_PDF = True   # PDF con boxes de colores
GENERATE_SEARCHABLE_PDF = True  # PDF con texto seleccionable
GENERATE_EDITABLE_PDF = True    # PDF con texto editable

# Límites de procesamiento ⭐ NUEVO
MAX_FILE_SIZE_MB = 50          # Tamaño máximo del PDF
MAX_PAGES = 100                # Número máximo de páginas
MAX_PROCESSING_TIME_SEC = 300  # Timeout en segundos (5 min)
WARN_FILE_SIZE_MB = 20         # Advertir si supera este tamaño
WARN_PAGES = 50                # Advertir si supera este número

# Profiling ⭐ NUEVO
ENABLE_PROFILING = True                    # Activar registro de rendimiento
PROFILE_OUTPUT_DIR = "output_ocr/profiles" # Directorio para perfiles
PROFILE_SAVE_JSON = True                   # Guardar perfil en JSON
PROFILE_SHOW_SUMMARY = True                # Mostrar resumen al final
```

---

## 🚀 Uso

```bash
# Ejecutar versión refactorizada
uv run python main_refactored.py

# O versión original
uv run python main.py
```

## 📦 Módulos

### `src/pdf/`
- **analyzer.py**: Detecta tipo de PDF (texto/imágenes/escaneado)
- **text_extractor.py**: Extrae texto nativo con coordenadas exactas
- **image_extractor.py**: Extrae imágenes embebidas con posición
- **converter.py**: Convierte páginas PDF a imágenes
- **generator.py**: Crea PDFs anotados/seleccionables/editables

### `src/ocr/`
- **engine.py**: Inicializa PaddleOCR y ejecuta reconocimiento
- **word_splitter.py**: Divide boxes de líneas en palabras

### `src/visualization/`
- **drawer.py**: Dibuja boxes sobre imágenes en resolución original

### `src/utils/`
- **io.py**: Guarda resultados en JSON con metadata
- **validators.py**: Validación de PDFs (tamaño, páginas) ⭐ NUEVO
- **profiler.py**: Profiling de rendimiento ⭐ NUEVO

### `tools/`
- **censura.py**: Censura palabras/patrones (emails, teléfonos, DNI)
- **analyze_performance.py**: Análisis de perfiles históricos ⭐ NUEVO

---

## 🛡️ Sistema de Validación ⭐ NUEVO

El sistema valida automáticamente cada PDF antes de procesar:

**Ejemplo de salida:**
```
📊 Validando PDF...
  📦 Tamaño: 15.30 MB
  📄 Páginas: 35
  ✅ Validación exitosa
```

**Con advertencias:**
```
📊 Validando PDF...
  📦 Tamaño: 25.80 MB
  📄 Páginas: 75
  ⚠️  ADVERTENCIA: Archivo grande (25.8MB)
     El procesamiento puede tardar varios minutos
  ⚠️  ADVERTENCIA: 75 páginas
     Tiempo estimado (CPU): ~1.9 minutos
     Considera usar GPU para acelerar el proceso
  ✅ Validación exitosa
```

**Excediendo límites:**
```
📊 Validando PDF...
  📦 Tamaño: 65.20 MB
❌ Archivo demasiado grande: 65.2MB
   Máximo permitido: 50MB
   Considera dividir el PDF o aumentar MAX_FILE_SIZE_MB en config.py
```

**Timeout alcanzado:**
```
⏱️ LÍMITE DE TIEMPO ALCANZADO
============================================================
❌ El procesamiento excedió el límite de 300 segundos (5.0 minutos)

💡 Recomendaciones:
   • Divide el PDF en archivos más pequeños
   • Aumenta MAX_PROCESSING_TIME_SEC en config.py
   • Usa GPU para acelerar el proceso
   • Reduce el número de páginas (MAX_PAGES)
```

---

## 📊 Sistema de Profiling ⭐ NUEVO

### Registro Automático

El profiler registra automáticamente:

**Hardware:**
- Sistema operativo y versión
- Procesador (CPU)
- Número de núcleos
- GPU disponible (detecta NVIDIA automáticamente)

**PDF:**
- Tipo de documento
- Número de páginas
- Tamaño en MB
- Páginas por segundo
- MB por segundo

**Etapas:**
- Detección tipo PDF
- Extracción texto nativo
- Procesamiento híbrido
- OCR documento escaneado
- División por palabras
- Guardado de resultados
- Generación de visualizaciones
- Generación de PDFs mejorados

### Ejemplo de Resumen

```
============================================================
📊 RESUMEN DE RENDIMIENTO
============================================================

💻 Hardware:
  Sistema: Windows 11
  Procesador: Intel64 Family 6 Model 154
  CPU: 8 núcleos

📄 PDF Procesado:
  Tipo: text_and_images
  Páginas: 35
  Tamaño: 15.3 MB

⏱️  Rendimiento:
  Tiempo total: 52.45 segundos (0.87 min)
  Velocidad: 0.67 páginas/seg
  Throughput: 0.29 MB/seg

📈 Desglose por Etapas:
  Detección tipo PDF: 0.25s (0.5%)
  Procesamiento híbrido (texto + OCR imágenes): 48.12s (91.7%)
  División por palabras: 1.83s (3.5%)
  Guardado de resultados: 0.52s (1.0%)
  Generación de visualizaciones: 0.98s (1.9%)
  Generación de PDFs mejorados: 0.75s (1.4%)
============================================================
```

### Archivo de Perfil JSON

Cada ejecución guarda un perfil en `output_ocr/profiles/profile_YYYYMMDD_HHMMSS.json`:

```json
{
  "timestamp": "2026-01-24T15:30:45.123456",
  "total_time_seconds": 52.451,
  "hardware": {
    "system": "Windows",
    "release": "11",
    "processor": "Intel64 Family 6 Model 154",
    "cpu_count": 8,
    "gpu_available": false
  },
  "pdf": {
    "type": "text_and_images",
    "num_pages": 35,
    "file_size_mb": 15.3,
    "pages_per_second": 0.67,
    "mb_per_second": 0.29
  },
  "stages": [
    {
      "name": "Detección tipo PDF",
      "start": 1234567.890,
      "end": 1234568.140,
      "duration": 0.250
    }
  ],
  "timings": {
    "Detección tipo PDF": 0.250,
    "Procesamiento híbrido": 48.120
  }
}
```

### Análisis Histórico

```bash
uv run python tools/analyze_performance.py
```

**Ejemplo de salida:**

```
📊 RENDIMIENTO POR TIPO DE PDF
============================================================
📄 TEXT_AND_IMAGES
  Documentos procesados: 12
  Tiempo promedio: 45.32s
  Páginas promedio: 28.5
  Velocidad promedio: 0.63 pág/seg

📄 SCANNED
  Documentos procesados: 5
  Tiempo promedio: 125.67s
  Páginas promedio: 82.0
  Velocidad promedio: 0.65 pág/seg

💻 RENDIMIENTO POR HARDWARE
============================================================
⚙️  CPU
  Ejecuciones: 15
  Tiempo promedio: 62.18s
  Velocidad promedio: 0.64 pág/seg

⚙️  GPU
  Ejecuciones: 2
  Tiempo promedio: 5.32s
  Velocidad promedio: 9.42 pág/seg

⏱️  TIEMPO PROMEDIO POR ETAPA
============================================================
  Detección tipo PDF: 0.23s promedio (6 ejecuciones)
  Procesamiento híbrido: 35.67s promedio (10 ejecuciones)
  OCR documento escaneado: 98.45s promedio (5 ejecuciones)

🔄 COMPARACIÓN: Primera vs Última Ejecución
============================================================
📅 Primera ejecución: 2026-01-20
  Tiempo: 68.50s
  Velocidad: 0.51 pág/seg

📅 Última ejecución: 2026-01-24
  Tiempo: 52.45s
  Velocidad: 0.67 pág/seg

✅ Mejora de rendimiento: 23.4% más rápido
```

---

## 📊 Resultados

El sistema genera:

1. **`ocr_results.json`**: Resultados completos estructurados
   ```json
   {
     "metadata": {
       "pdf_type": "text_and_images",
       "timestamp": "2026-01-24 10:30:15",
       "config": {...}
     },
     "pages": [
       {
         "page_num": 1,
         "text_regions": [
           {
             "bbox": [[x0,y0], [x1,y1], [x2,y2], [x3,y3]],
             "text": "palabra",
             "confidence": 0.98,
             "source": "native"
           }
         ]
       }
     ]
   }
   ```

2. **`documento_anotado.pdf`**: Boxes de colores
   - 🟢 Verde: Texto nativo
   - 🟠 Naranja: OCR de imágenes
   - 🔴 Rojo: OCR de páginas escaneadas

3. **`documento_seleccionable.pdf`**: Texto invisible para búsqueda/copia

4. **`documento_editable.pdf`**: Texto visible y modificable

5. **Imágenes anotadas**: En `output_real/` con boxes dibujados

## 🔧 Herramientas

### Sistema de Censura

```python
from tools.censura import (
    buscar_palabras_a_censurar,
    buscar_por_patron,
    aplicar_censura,
    censurar_emails,
    censurar_telefonos,
    censurar_dni
)

# Cargar resultados OCR
with open("output_ocr/ocr_results.json") as f:
    resultados = json.load(f)

# Censurar emails
matches = censurar_emails("documento.pdf", resultados, "documento_censurado.pdf")
```

## 🎨 Tipos de Extracción

### Texto Nativo (SPLIT_BY_WORDS=True)
- Usa `page.get_text("words")` para coordenadas exactas
- Cada palabra tiene su bbox precisa
- Ideal para documentos con texto seleccionable

### OCR (SPLIT_BY_WORDS=True)
- Primero extrae líneas completas
- Divide proporcionalmente por caracteres
- Útil para documentos escaneados

### Imágenes Embebidas
- Extrae imagen del PDF
- Aplica OCR a la imagen
- Transforma coordenadas al espacio del PDF
- Combina con texto nativo

## 📝 Notas de Migración

Si usabas `main.py`, puedes migrar a `main_refactored.py`:

1. ✅ Mantiene toda la funcionalidad original
2. ✅ Código más limpio y mantenible
3. ✅ Fácil de extender con nuevas características
4. ✅ Mejor separación de responsabilidades
5. ✅ Imports organizados por dominio

**Diferencias**:
- `main.py`: Monolítico (1516 líneas)
- `main_refactored.py`: Modular (~350 líneas + módulos)

## 🚀 Próximas Mejoras

- [ ] Soporte GPU para PaddleOCR
- [ ] Procesamiento paralelo de páginas
- [ ] Interfaz web con FastAPI
- [ ] Empaquetado con PyInstaller/Docker
- [ ] Tests unitarios
- [ ] CI/CD con GitHub Actions

## 📄 Licencia

MIT
