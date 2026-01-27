import os
import time
import json
from pathlib import Path
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
from paddleocr import PaddleOCR

os.environ['DISABLE_MODEL_SOURCE_CHECK'] = 'True'

# ===============================
# CONFIGURACIÓN
# ===============================
PDF_PATH = "Para probar la eficiencia de PaddleOCR 3.pdf"  # nombre de pdf
IMG_DIR = "images_scaled"  # imágenes redimensionadas
OUT_DIR = "output_ocr"  # imágenes comparativas y json de resultados
OUT_ANNOTATED = "output_real"  # imágenes anotadas en resolución original
JSON_OUTPUT = "output_ocr/ocr_results.json"  # resultado consolidado

MAX_SIDE = 850  # tamaño máximo para optimización
CPU_THREADS = 4  # hilos de CPU para OCR
MIN_CONFIDENCE = 0.5  # confianza mínima para resultados

# Configuración de división por palabras
SPLIT_BY_WORDS = True  # True = dividir boxes por palabra, False = mantener por línea
WORD_SPACING_THRESHOLD = 0.1  # Factor para detectar espacios entre palabras (0.3 = 30% del ancho promedio de caracteres)

os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(OUT_ANNOTATED, exist_ok=True)

# ===============================
# TIMER helper
# ===============================
def log_time(label, start):
    elapsed = time.perf_counter() - start
    print(f"⏱️ {label}: {elapsed:.3f} s")
    return elapsed


# ===============================
# ✂️ Dividir box de línea en palabras
# ===============================
def split_line_box_into_words(bbox, text, confidence=1.0, source="unknown"):
    """
    Divide una bounding box de línea en boxes individuales por palabra.
    Usa proporción visual basada en la longitud de caracteres y espacios.
    
    Args:
        bbox: [[x0,y0], [x1,y1], [x2,y2], [x3,y3]] - box de la línea completa
        text: Texto completo de la línea
        confidence: Confianza del OCR para esta línea
        source: Fuente del texto (native, ocr, etc.)
        
    Returns:
        Lista de boxes, una por cada palabra
    """
    if not text or not bbox:
        return []
    
    # Dividir texto en palabras
    words = text.split()
    
    if len(words) <= 1:
        # Si solo hay una palabra, devolver la box original
        return [{
            "bbox": bbox,
            "text": text,
            "confidence": confidence,
            "source": source
        }]
    
    # Extraer coordenadas de la box (asumiendo rectángulo aproximado)
    x_coords = [p[0] for p in bbox]
    y_coords = [p[1] for p in bbox]
    
    x0 = min(x_coords)  # izquierda
    x1 = max(x_coords)  # derecha
    y0 = min(y_coords)  # arriba
    y1 = max(y_coords)  # abajo
    
    total_width = x1 - x0
    total_chars = sum(len(word) for word in words)
    
    # Calcular ancho por carácter (aproximado)
    char_width = total_width / total_chars if total_chars > 0 else 0
    
    word_boxes = []
    current_x = x0
    
    for i, word in enumerate(words):
        # Calcular ancho de esta palabra basado en proporción de caracteres
        word_chars = len(word)
        word_width = char_width * word_chars
        
        # Calcular posición de la palabra
        word_x0 = current_x
        word_x1 = current_x + word_width
        
        # Asegurar que no exceda el límite derecho en la última palabra
        if i == len(words) - 1:
            word_x1 = x1
        
        # Crear box para esta palabra (formato de 4 puntos)
        word_bbox = [
            [word_x0, y0],  # top-left
            [word_x1, y0],  # top-right
            [word_x1, y1],  # bottom-right
            [word_x0, y1]   # bottom-left
        ]
        
        word_boxes.append({
            "bbox": word_bbox,
            "text": word,
            "confidence": confidence,
            "source": source,
            "is_word": True  # Marca para identificar que es una palabra individual
        })
        
        # Avanzar posición para la siguiente palabra
        # Agregar espacio entre palabras (usando el threshold configurado)
        space_width = char_width * WORD_SPACING_THRESHOLD
        current_x = word_x1 + space_width
    
    return word_boxes


# ===============================
# 🔄 Aplicar división por palabras a resultados
# ===============================
def apply_word_splitting(results_data):
    """
    Aplica división por palabras a todos los resultados.
    Solo aplica a regiones que NO son palabras individuales (is_word != True).
    
    Args:
        results_data: Diccionario con resultados estructurados
        
    Returns:
        Resultados con boxes divididas por palabra
    """
    if not SPLIT_BY_WORDS:
        return results_data
    
    print("\n✂️ Dividiendo boxes de línea en palabras (solo OCR)...")
    
    for page_data in results_data.get('pages', []):
        page_num = page_data['page_num']
        original_regions = page_data.get('text_regions', [])
        word_regions = []
        
        for region in original_regions:
            # Si ya es una palabra individual (texto nativo extraído por palabra), no dividir
            if region.get('is_word', False):
                word_regions.append(region)
                continue
            
            bbox = region.get('bbox')
            text = region.get('text', '')
            confidence = region.get('confidence', 1.0)
            source = region.get('source', 'unknown')
            
            # Dividir esta línea en palabras (solo para OCR)
            word_boxes = split_line_box_into_words(bbox, text, confidence, source)
            word_regions.extend(word_boxes)
        
        # Actualizar regiones con las divididas por palabra
        original_count = len(original_regions)
        word_count = len(word_regions)
        page_data['text_regions'] = word_regions
        page_data['original_line_count'] = original_count
        
        print(f"  ✓ Página {page_num}: {original_count} líneas → {word_count} palabras")
    
    return results_data


# ===============================
# 🔍 Detectar tipo de PDF
# ===============================
def detect_pdf_type(pdf_path):
    """
    Detecta si el PDF contiene texto nativo, imágenes, o es un documento escaneado.
    
    Returns:
        Dict con información por página:
        {
            'type': 'text_only' | 'text_and_images' | 'scanned',
            'pages': [
                {
                    'page_num': 1,
                    'has_text': True/False,
                    'has_images': True/False,
                    'text_blocks': int,
                    'image_count': int
                },
                ...
            ]
        }
    """
    print("\n🔍 Analizando tipo de PDF...")
    
    try:
        doc = fitz.open(pdf_path)
        pages_info = []
        
        total_text_blocks = 0
        total_images = 0
        
        for i, page in enumerate(doc):
            text = page.get_text("text").strip()
            text_blocks = len(page.get_text("blocks"))
            images = page.get_images(full=True)
            
            has_text = len(text) > 50  # Al menos 50 caracteres
            has_images = len(images) > 0
            
            pages_info.append({
                'page_num': i + 1,
                'has_text': has_text,
                'has_images': has_images,
                'text_blocks': text_blocks,
                'image_count': len(images)
            })
            
            total_text_blocks += text_blocks
            total_images += len(images)
            
            status = []
            if has_text:
                status.append(f"📝 {text_blocks} bloques de texto")
            if has_images:
                status.append(f"🖼️ {len(images)} imagen(es)")
            if not has_text and not has_images:
                status.append("📄 Página vacía")
            
            print(f"  Página {i+1}: {', '.join(status)}")
        
        doc.close()
        
        # Determinar tipo general del documento
        pages_with_text = sum(1 for p in pages_info if p['has_text'])
        pages_with_images = sum(1 for p in pages_info if p['has_images'])
        total_pages = len(pages_info)
        
        if pages_with_text == total_pages and pages_with_images == 0:
            doc_type = 'text_only'
            icon = "📝"
            description = "Solo texto nativo (no necesita OCR)"
        elif pages_with_text > 0 and pages_with_images > 0:
            doc_type = 'text_and_images'
            icon = "📝🖼️"
            description = "Texto nativo + imágenes (OCR solo para imágenes)"
        elif pages_with_images > 0:
            doc_type = 'scanned'
            icon = "🖼️"
            description = "Documento escaneado (requiere OCR completo)"
        else:
            doc_type = 'scanned'  # Por defecto, usar OCR
            icon = "❓"
            description = "Tipo desconocido (usar OCR)"
        
        result = {
            'type': doc_type,
            'pages': pages_info,
            'summary': {
                'total_pages': total_pages,
                'pages_with_text': pages_with_text,
                'pages_with_images': pages_with_images,
                'description': description
            }
        }
        
        print(f"\n{icon} Tipo de documento: {description}")
        print(f"   Total: {total_pages} páginas | {pages_with_text} con texto | {pages_with_images} con imágenes")
        
        return result
        
    except Exception as e:
        print(f"❌ Error detectando tipo de PDF: {e}")
        return {'type': 'scanned', 'pages': [], 'summary': {}}


# ===============================
# 📄 Extraer texto nativo del PDF
# ===============================
def extract_native_text_with_boxes(pdf_path, page_nums=None):
    """
    Extrae texto nativo del PDF con sus bounding boxes.
    Si SPLIT_BY_WORDS está activado, extrae palabra por palabra.
    Si está desactivado, extrae por bloques.
    
    Args:
        pdf_path: Ruta al PDF
        page_nums: Lista de números de página a procesar (None = todas)
    
    Returns:
        Dict con resultados por página
    """
    print(f"\n📄 Extrayendo texto nativo con bounding boxes ({'por palabra' if SPLIT_BY_WORDS else 'por bloque'})...")
    
    try:
        doc = fitz.open(pdf_path)
        results = {'pages': []}
        
        pages_to_process = page_nums if page_nums else range(len(doc))
        
        for page_idx in pages_to_process:
            page = doc[page_idx]
            page_num = page_idx + 1
            
            text_regions = []
            full_text = ""
            
            if SPLIT_BY_WORDS:
                # Método 1: Extraer palabra por palabra con coordenadas exactas
                words = page.get_text("words")  # Devuelve (x0, y0, x1, y1, "word", block_no, line_no, word_no)
                
                for word_info in words:
                    if len(word_info) < 5:
                        continue
                    
                    x0, y0, x1, y1, word_text = word_info[0], word_info[1], word_info[2], word_info[3], word_info[4]
                    
                    # Convertir a formato de 4 puntos
                    bbox_4points = [
                        [x0, y0],  # top-left
                        [x1, y0],  # top-right
                        [x1, y1],  # bottom-right
                        [x0, y1]   # bottom-left
                    ]
                    
                    text_regions.append({
                        "bbox": bbox_4points,
                        "text": word_text,
                        "confidence": 1.0,  # Texto nativo = 100% confianza
                        "source": "native",
                        "is_word": True
                    })
                    full_text += word_text + " "
                
                print(f"  ✓ Página {page_num}: {len(text_regions)} palabras extraídas")
                
            else:
                # Método 2: Extraer por bloques (comportamiento anterior)
                blocks = page.get_text("dict")["blocks"]
                
                for block in blocks:
                    if block.get("type") == 0:  # Tipo 0 = texto
                        bbox = block["bbox"]  # (x0, y0, x1, y1)
                        
                        # Extraer todo el texto del bloque
                        block_text = ""
                        for line in block.get("lines", []):
                            for span in line.get("spans", []):
                                block_text += span.get("text", "")
                            block_text += " "
                        
                        block_text = block_text.strip()
                        
                        if block_text:
                            # Convertir bbox de (x0,y0,x1,y1) a formato de 4 puntos
                            x0, y0, x1, y1 = bbox
                            bbox_4points = [
                                [x0, y0],  # top-left
                                [x1, y0],  # top-right
                                [x1, y1],  # bottom-right
                                [x0, y1]   # bottom-left
                            ]
                            
                            text_regions.append({
                                "bbox": bbox_4points,
                                "text": block_text,
                                "confidence": 1.0,
                                "source": "native"
                            })
                            full_text += block_text + "\n"
                
                print(f"  ✓ Página {page_num}: {len(text_regions)} bloques de texto extraídos")
            
            results['pages'].append({
                "page_num": page_num,
                "text_regions": text_regions,
                "full_text": full_text.strip()
            })
        
        doc.close()
        return results
        
    except Exception as e:
        print(f"❌ Error extrayendo texto nativo: {e}")
        return {'pages': []}


# ===============================
# 🖼️ Extraer imágenes embebidas del PDF
# ===============================
def extract_images_from_pdf(pdf_path, page_nums=None):
    """
    Extrae imágenes embebidas del PDF y guarda sus coordenadas.
    
    Returns:
        Lista de imágenes con sus ubicaciones en el PDF
    """
    print("\n🖼️ Extrayendo imágenes embebidas del PDF...")
    
    try:
        doc = fitz.open(pdf_path)
        extracted_images = []
        
        pages_to_process = page_nums if page_nums else range(len(doc))
        
        for page_idx in pages_to_process:
            page = doc[page_idx]
            page_num = page_idx + 1
            images = page.get_images(full=True)
            
            for img_idx, img in enumerate(images):
                xref = img[0]
                
                try:
                    # Obtener la imagen
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    
                    # Guardar imagen temporalmente
                    img_path = f"{IMG_DIR}/page_{page_num}_img_{img_idx}.{image_ext}"
                    with open(img_path, "wb") as img_file:
                        img_file.write(image_bytes)
                    
                    # Obtener coordenadas de la imagen en la página
                    # Buscar todas las instancias de esta imagen en la página
                    image_rects = page.get_image_rects(xref)
                    
                    # Si hay múltiples instancias, usar la primera
                    if image_rects:
                        rect = image_rects[0]  # fitz.Rect object
                        # Convertir a formato de 4 puntos
                        x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
                        bbox = [
                            [x0, y0],  # top-left
                            [x1, y0],  # top-right  
                            [x1, y1],  # bottom-right
                            [x0, y1]   # bottom-left
                        ]
                    else:
                        bbox = None
                    
                    extracted_images.append({
                        "page_num": page_num,
                        "image_path": img_path,
                        "bbox": bbox,
                        "image_index": img_idx
                    })
                    
                except Exception as img_error:
                    print(f"    ⚠️ Error con imagen {img_idx}: {img_error}")
                    continue
            
            if images:
                print(f"  ✓ Página {page_num}: {len(images)} imagen(es) extraídas")
        
        doc.close()
        return extracted_images
        
    except Exception as e:
        print(f"❌ Error extrayendo imágenes: {e}")
        return []


# ===============================
# 1️⃣ PDF → imágenes escaladas
# ===============================
def pdf_to_scaled_images(pdf_path):
    """
    Convierte un PDF a imágenes PNG escaladas.
    
    Args:
        pdf_path: Ruta al archivo PDF
        
    Returns:
        Lista de diccionarios con información de cada imagen generada
    """
    t0 = time.perf_counter()
    
    try:
        doc = fitz.open(pdf_path)
        images = []
        total_pages = len(doc)
        
        print(f"📖 PDF tiene {total_pages} página(s)")

        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)

            w, h = pix.width, pix.height
            max_dim = max(w, h)
            scale = min(1.0, MAX_SIDE / max_dim)

            new_w = int(w * scale)
            new_h = int(h * scale)

            img_original = Image.frombytes("RGB", (w, h), pix.samples)
            img = img_original.copy()

            if scale < 1.0:
                img = img.resize((new_w, new_h), Image.LANCZOS)

            img_path = f"{IMG_DIR}/page_{i+1}.png"
            img.save(img_path, optimize=True, quality=95)
            
            # Guardar imagen original para anotaciones posteriores
            orig_path = f"{OUT_ANNOTATED}/page_{i+1}_original.png"
            img_original.save(orig_path, optimize=True, quality=95)

            images.append({
                "page_num": i + 1,
                "path": img_path,
                "original_path": orig_path,
                "scale": scale,
                "orig_size": (w, h),
                "new_size": (new_w, new_h)
            })

            print(f"📄 Página {i+1}/{total_pages}: {w}x{h} → {new_w}x{new_h} (scale {scale:.4f})")

        doc.close()
        log_time("Render + escalado", t0)
        return images
        
    except Exception as e:
        print(f"❌ Error procesando PDF: {e}")
        raise


# ===============================
# 2️⃣ Inicializar OCR (UNA VEZ)
# ===============================
def init_ocr():
    """
    Inicializa el motor PaddleOCR con configuración optimizada.
    
    Returns:
        Instancia de PaddleOCR configurada
    """
    t0 = time.perf_counter()
    
    try:
        ocr = PaddleOCR(
            ocr_version="PP-OCRv5",  # versión de modelo
            lang="es",  # lenguaje preferido
            text_detection_model_name="PP-OCRv5_mobile_det",  # modelo de detección
            text_recognition_model_name="PP-OCRv5_mobile_rec",  # modelo de reconocimiento
            text_det_limit_side_len=MAX_SIDE,  # límite de longitud
            cpu_threads=CPU_THREADS, 
            use_doc_orientation_classify=False,  # orientación
            use_doc_unwarping=False, 
            use_textline_orientation=False,
            enable_mkldnn=True,  # acelera inferencia en CPU
            
        )

        log_time("Inicialización OCR", t0)
        return ocr
        
    except Exception as e:
        print(f"❌ Error inicializando OCR: {e}")
        raise


# ===============================
# 3️⃣ OCR (inferencia y guardado)
# ===============================
def run_ocr(images, ocr):
    """
    Ejecuta OCR en todas las imágenes y guarda resultados estructurados.
    
    Args:
        images: Lista de diccionarios con info de imágenes
        ocr: Instancia de PaddleOCR
        
    Returns:
        Diccionario con todos los resultados del OCR
    """
    ocr_total = 0.0
    all_results = {
        "metadata": {
            "total_pages": len(images),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "config": {
                "max_side": MAX_SIDE,
                "min_confidence": MIN_CONFIDENCE
            }
        },
        "pages": []
    }

    for i, img in enumerate(images):
        page_start = time.perf_counter()
        page_num = img['page_num']

        print(f"\n🔍 OCR en página {page_num}/{len(images)}")
        
        try:
            result = ocr.predict(img["path"])
            page_time = log_time(f"OCR página {page_num}", page_start)
            ocr_total += page_time

            # Procesar y estructurar resultados
            page_data = {
                "page_num": page_num,
                "image_path": img["path"],
                "scale": img["scale"],
                "processing_time": round(page_time, 3),
                "text_regions": [],
                "full_text": ""
            }

            if result and isinstance(result, list):
                # El resultado es una lista de objetos
                print(f"📋 Resultado es lista con {len(result)} elemento(s)")
                
                rec_texts = []
                rec_scores = []
                rec_polys = []
                
                # Procesar cada elemento de la lista
                for idx, res in enumerate(result):
                    print(f"  📋 Elemento {idx}: tipo={type(res).__name__}")
                    
                    # Guardar con métodos nativos si existen
                    if hasattr(res, 'save_to_img'):
                        res.save_to_img(OUT_DIR)
                        print(f"  ✓ Imagen guardada")
                    if hasattr(res, 'save_to_json'):
                        res.save_to_json(OUT_DIR)
                        print(f"  ✓ JSON guardado")
                    
                    # Intentar extraer datos del objeto
                    if hasattr(res, 'json'):
                        result_json = res.json
                        rec_texts = result_json.get('rec_texts', [])
                        rec_scores = result_json.get('rec_scores', [])
                        rec_polys = result_json.get('rec_polys', [])
                        print(f"  ✓ Extraídos {len(rec_texts)} textos desde .json")
                    elif hasattr(res, 'rec_texts'):
                        rec_texts = res.rec_texts
                        rec_scores = getattr(res, 'rec_scores', [])
                        rec_polys = getattr(res, 'rec_polys', [])
                        print(f"  ✓ Extraídos {len(rec_texts)} textos desde atributos")
                    elif isinstance(res, dict):
                        rec_texts = res.get('rec_texts', [])
                        rec_scores = res.get('rec_scores', [])
                        rec_polys = res.get('rec_polys', [])
                        print(f"  ✓ Extraídos {len(rec_texts)} textos desde dict")
                
                # Procesar cada región detectada
                for i in range(len(rec_texts)):
                    text = rec_texts[i]
                    confidence = rec_scores[i] if i < len(rec_scores) else 0.0
                    poly = rec_polys[i] if i < len(rec_polys) else None
                    
                    # Filtrar por confianza mínima
                    if confidence >= MIN_CONFIDENCE:
                        # Convertir numpy array a lista si es necesario
                        if poly is not None:
                            if hasattr(poly, 'tolist'):
                                bbox = poly.tolist()
                            else:
                                bbox = poly
                        else:
                            bbox = None
                        
                        page_data["text_regions"].append({
                            "bbox": bbox,
                            "text": text,
                            "confidence": float(confidence)
                        })
                        page_data["full_text"] += text + "\n"
                
                # Si no se extrajeron datos, intentar leer el JSON generado
                if len(page_data["text_regions"]) == 0:
                    # Buscar archivo JSON generado por save_to_json
                    json_pattern = f"{OUT_DIR}/page_{page_num}_res.json"
                    if os.path.exists(json_pattern):
                        print(f"  📂 Leyendo JSON generado: {json_pattern}")
                        with open(json_pattern, 'r', encoding='utf-8') as f:
                            saved_json = json.load(f)
                            rec_texts = saved_json.get('rec_texts', [])
                            rec_scores = saved_json.get('rec_scores', [])
                            rec_polys = saved_json.get('rec_polys', [])
                            
                            for i in range(len(rec_texts)):
                                text = rec_texts[i]
                                confidence = rec_scores[i] if i < len(rec_scores) else 0.0
                                poly = rec_polys[i] if i < len(rec_polys) else None
                                
                                if confidence >= MIN_CONFIDENCE and poly is not None:
                                    page_data["text_regions"].append({
                                        "bbox": poly,
                                        "text": text,
                                        "confidence": float(confidence)
                                    })
                                    page_data["full_text"] += text + "\n"
                            
                            print(f"  ✓ Cargados {len(page_data['text_regions'])} textos desde JSON")
                
                text_regions = len(page_data["text_regions"])
                if text_regions > 0:
                    print(f"✓ Total: {text_regions} región(es) de texto")
                else:
                    print(f"⚠️ No se detectaron textos en esta página")
            else:
                print(f"⚠️ Resultado vacío o formato inesperado")

            all_results["pages"].append(page_data)
            
        except Exception as e:
            print(f"❌ Error en OCR página {page_num}: {e}")
            all_results["pages"].append({
                "page_num": page_num,
                "error": str(e)
            })

    print(f"\n⏱️ OCR total: {ocr_total:.3f} s")
    
    # Guardar resultados consolidados
    save_results(all_results)
    
    return all_results


# ===============================
# 4️⃣ Guardar resultados
# ===============================
def save_results(results):
    """
    Guarda los resultados del OCR en formato JSON.
    
    Args:
        results: Diccionario con resultados estructurados
    """
    try:
        with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Resultados guardados en: {JSON_OUTPUT}")
        
        # Estadísticas resumidas
        total_pages = len(results.get("pages", []))
        if "metadata" in results and "total_pages" in results["metadata"]:
            total_pages = results["metadata"]["total_pages"]
        
        pages_with_text = sum(1 for p in results.get("pages", []) if p.get("text_regions"))
        print(f"📊 Resumen: {pages_with_text}/{total_pages} páginas con texto detectado")
        
    except Exception as e:
        print(f"⚠️ Error guardando resultados: {e}")
        import traceback
        traceback.print_exc()


# ===============================
# 5️⃣ Dibujar boxes en resolución original
# ===============================
def draw_boxes_original_scale(images, ocr_results):
    """
    Dibuja las bounding boxes en las imágenes originales (resolución completa).
    Re-escala las coordenadas de las boxes desde la imagen escalada a la original.
    
    Args:
        images: Lista de diccionarios con info de imágenes
        ocr_results: Resultados estructurados del OCR con boxes
    """
    print("\n🎨 Dibujando boxes en resolución original...")
    
    for img_info in images:
        page_num = img_info['page_num']
        original_path = img_info['original_path']
        scale = img_info['scale']
        
        # Buscar resultados OCR de esta página
        page_results = next((p for p in ocr_results['pages'] if p['page_num'] == page_num), None)
        
        if not page_results or 'error' in page_results:
            print(f"⚠️ Página {page_num}: Sin resultados OCR válidos")
            continue
        
        text_regions = page_results.get('text_regions', [])
        if not text_regions:
            print(f"⚠️ Página {page_num}: No hay regiones de texto para dibujar")
            continue
            
        try:
            # Cargar imagen original
            img = Image.open(original_path)
            draw = ImageDraw.Draw(img)
            
            # Intentar cargar fuente, si falla usar default
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                try:
                    font = ImageFont.truetype("Arial.ttf", 24)
                except:
                    font = ImageFont.load_default()
            
            boxes_drawn = 0
            
            print(f"  📝 Procesando {len(text_regions)} regiones de texto...")
            
            # Dibujar cada región de texto
            for idx, region in enumerate(text_regions):
                if 'bbox' not in region:
                    continue
                    
                bbox = region['bbox']
                text = region.get('text', '')
                confidence = region.get('confidence', 0)
                
                # PaddleOCR devuelve bbox en formato [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]
                if isinstance(bbox, list) and len(bbox) == 4 and isinstance(bbox[0], list):
                    # Re-escalar coordenadas a escala original
                    scaled_bbox = [[int(x/scale), int(y/scale)] for x, y in bbox]
                    
                    # Dibujar polígono (cuadrilátero)
                    points = [tuple(point) for point in scaled_bbox]
                    draw.polygon(points, outline='red', width=4)
                    
                    # Dibujar texto y confianza (opcional)
                    if text and len(scaled_bbox) > 0:
                        # Posición para el texto (arriba del box)
                        text_pos = (scaled_bbox[0][0], scaled_bbox[0][1] - 30)
                        label = f"{confidence:.2f}"
                        draw.text(text_pos, label, fill='blue', font=font)
                    
                    boxes_drawn += 1
                else:
                    print(f"    ⚠️ Región {idx}: Formato de bbox no reconocido: {type(bbox)}")
            
            if boxes_drawn > 0:
                # Guardar imagen anotada
                annotated_path = f"{OUT_ANNOTATED}/page_{page_num}_annotated.png"
                img.save(annotated_path, quality=95)
                print(f"  ✓ Página {page_num}: {boxes_drawn} boxes dibujadas → {img.size[0]}x{img.size[1]}px")
                print(f"    💾 Guardado: {annotated_path}")
            else:
                print(f"  ⚠️ Página {page_num}: No se dibujaron boxes")
            
        except Exception as e:
            print(f"  ❌ Error dibujando boxes en página {page_num}: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n📁 Imágenes anotadas guardadas en: {OUT_ANNOTATED}/")


# ===============================
# 🎨 Dibujar boxes de texto nativo
# ===============================
def draw_native_text_boxes(pdf_path, results_data):
    """
    Dibuja las bounding boxes del texto nativo directamente desde el PDF.
    
    Args:
        pdf_path: Ruta al PDF original
        results_data: Resultados con las boxes del texto nativo
    """
    print("\n🎨 Generando visualización del texto nativo...")
    
    try:
        doc = fitz.open(pdf_path)
        
        for page_data in results_data['pages']:
            page_num = page_data['page_num']
            page = doc[page_num - 1]
            
            # Renderizar página a imagen en alta resolución
            mat = fitz.Matrix(3, 3)  # 3x escala para alta calidad
            pix = page.get_pixmap(matrix=mat, alpha=False)
            
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            draw = ImageDraw.Draw(img)
            
            # Cargar fuente
            try:
                font = ImageFont.truetype("arial.ttf", 24)
            except:
                font = ImageFont.load_default()
            
            text_regions = page_data.get('text_regions', [])
            
            for region in text_regions:
                bbox = region.get('bbox')
                confidence = region.get('confidence', 1.0)
                
                if bbox and len(bbox) == 4:
                    # Escalar coordenadas por la matriz de renderizado
                    scaled_bbox = [[int(x * 3), int(y * 3)] for x, y in bbox]
                    points = [tuple(point) for point in scaled_bbox]
                    
                    # Color según fuente
                    color = 'green' if region.get('source') == 'native' else 'red'
                    
                    draw.polygon(points, outline=color, width=4)
                    
                    # Etiqueta con confianza
                    label = f"{confidence:.2f}"
                    text_pos = (scaled_bbox[0][0], scaled_bbox[0][1] - 30)
                    draw.text(text_pos, label, fill='blue', font=font)
            
            # Guardar
            annotated_path = f"{OUT_ANNOTATED}/page_{page_num}_annotated.png"
            img.save(annotated_path, quality=95)
            
            print(f"  ✓ Página {page_num}: {len(text_regions)} boxes dibujadas → {img.size[0]}x{img.size[1]}px")
            print(f"    💾 Guardado: {annotated_path}")
        
        doc.close()
        print(f"\n📁 Visualizaciones guardadas en: {OUT_ANNOTATED}/")
        
    except Exception as e:
        print(f"❌ Error generando visualización: {e}")
        import traceback
        traceback.print_exc()


# ===============================
# 📄 Crear PDF con regiones anotadas
# ===============================
def create_annotated_pdf(original_pdf_path, results_json_path, output_pdf_path):
    """
    Crea un nuevo PDF basado en el original con las regiones de texto marcadas.
    
    Args:
        original_pdf_path: Ruta al PDF original
        results_json_path: Ruta al JSON con resultados
        output_pdf_path: Ruta donde guardar el PDF anotado
    """
    print("\n📄 Creando PDF con regiones anotadas...")
    
    try:
        # Leer resultados JSON
        with open(results_json_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        # Abrir PDF original
        doc = fitz.open(original_pdf_path)
        
        for page_data in results.get('pages', []):
            page_num = page_data['page_num']
            page = doc[page_num - 1]
            
            text_regions = page_data.get('text_regions', [])
            
            for region in text_regions:
                bbox = region.get('bbox')
                text = region.get('text', '')
                confidence = region.get('confidence', 1.0)
                source = region.get('source', 'unknown')
                
                if not bbox or len(bbox) != 4:
                    continue
                
                try:
                    # Convertir bbox de 4 puntos a rectángulo
                    # bbox = [[x0,y0], [x1,y1], [x2,y2], [x3,y3]]
                    x_coords = [p[0] for p in bbox if p and len(p) >= 2]
                    y_coords = [p[1] for p in bbox if p and len(p) >= 2]
                    
                    if not x_coords or not y_coords:
                        continue
                    
                    # Validar que no haya valores None o infinitos
                    x_coords = [x for x in x_coords if x is not None and abs(x) != float('inf')]
                    y_coords = [y for y in y_coords if y is not None and abs(y) != float('inf')]
                    
                    if not x_coords or not y_coords:
                        continue
                    
                    x0, y0 = min(x_coords), min(y_coords)
                    x1, y1 = max(x_coords), max(y_coords)
                    
                    # Validar que el rectángulo tenga área
                    if x0 >= x1 or y0 >= y1:
                        continue
                    
                    rect = fitz.Rect(x0, y0, x1, y1)
                    
                    # Verificar que el rectángulo es válido
                    if rect.is_empty or rect.is_infinite:
                        continue
                    
                    # Color según fuente
                    if source == 'native':
                        color = (0, 1, 0)  # Verde para texto nativo
                    elif source == 'ocr_from_image':
                        color = (1, 0.5, 0)  # Naranja para OCR de imágenes
                    else:
                        color = (1, 0, 0)  # Rojo para OCR de escaneados
                    
                    # Agregar anotación de rectángulo
                    annot = page.add_rect_annot(rect)
                    annot.set_border(width=2)
                    annot.set_colors(stroke=color)
                    annot.set_opacity(0.3)
                    
                    # Agregar info en el popup
                    info_text = f"Texto: {text[:50]}...\n"
                    info_text += f"Confianza: {confidence:.2f}\n"
                    info_text += f"Fuente: {source}"
                    annot.set_info(content=info_text)
                    annot.update()
                        
                except (TypeError, ValueError, IndexError) as e:
                    print(f"    ⚠️ Bbox inválida en página {page_num}: {e}")
                    continue
            
            print(f"  ✓ Página {page_num}: {len(text_regions)} regiones anotadas")
        
        # Guardar PDF anotado
        doc.save(output_pdf_path, garbage=4, deflate=True)
        doc.close()
        
        print(f"\n💾 PDF anotado guardado: {output_pdf_path}")
        print(f"📌 Las regiones están marcadas con colores:")
        print(f"   🟢 Verde = Texto nativo")
        print(f"   🟠 Naranja = OCR de imágenes")
        print(f"   🔴 Rojo = OCR de documentos escaneados")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando PDF anotado: {e}")
        import traceback
        traceback.print_exc()
        return False


# ===============================
# 📄 Crear PDF con texto seleccionable
# ===============================
def create_searchable_pdf(original_pdf_path, results_json_path, output_pdf_path):
    """
    Crea un PDF donde el texto detectado es seleccionable y buscable.
    Útil para PDFs escaneados sin texto.
    
    Args:
        original_pdf_path: Ruta al PDF original
        results_json_path: Ruta al JSON con resultados
        output_pdf_path: Ruta donde guardar el PDF
    """
    print("\n📄 Creando PDF con texto seleccionable...")
    
    try:
        # Leer resultados JSON
        with open(results_json_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        # Abrir PDF original
        doc = fitz.open(original_pdf_path)
        
        for page_data in results.get('pages', []):
            page_num = page_data['page_num']
            page = doc[page_num - 1]
            
            text_regions = page_data.get('text_regions', [])
            
            for region in text_regions:
                bbox = region.get('bbox')
                text = region.get('text', '')
                
                if not bbox or len(bbox) != 4 or not text:
                    continue
                
                try:
                    # Convertir bbox a rectángulo
                    x_coords = [p[0] for p in bbox if p and len(p) >= 2]
                    y_coords = [p[1] for p in bbox if p and len(p) >= 2]
                    
                    if not x_coords or not y_coords:
                        continue
                    
                    # Validar que no haya valores None o infinitos
                    x_coords = [x for x in x_coords if x is not None and abs(x) != float('inf')]
                    y_coords = [y for y in y_coords if y is not None and abs(y) != float('inf')]
                    
                    if not x_coords or not y_coords:
                        continue
                    
                    x0, y0 = min(x_coords), min(y_coords)
                    x1, y1 = max(x_coords), max(y_coords)
                    
                    # Validar que el rectángulo tenga área
                    if x0 >= x1 or y0 >= y1:
                        continue
                    
                    rect = fitz.Rect(x0, y0, x1, y1)
                    
                    # Verificar que el rectángulo es válido
                    if rect.is_empty or rect.is_infinite:
                        continue
                    
                    # Calcular tamaño de fuente aproximado
                    height = y1 - y0
                    fontsize = max(1, height * 0.8)  # Mínimo 1px, 80% de la altura del bbox
                    
                    # Insertar texto invisible (para búsqueda) o visible
                    page.insert_textbox(
                        rect,
                        text,
                        fontsize=fontsize,
                        fontname="helv",
                        color=(0, 0, 0),
                        align=fitz.TEXT_ALIGN_LEFT,
                        render_mode=3  # Invisible pero seleccionable
                    )
                    
                except (TypeError, ValueError, IndexError) as e:
                    print(f"    ⚠️ Bbox inválida en página {page_num}: {e}")
                    continue
            
            print(f"  ✓ Página {page_num}: {len(text_regions)} textos insertados")
        
        # Guardar PDF
        doc.save(output_pdf_path, garbage=4, deflate=True)
        doc.close()
        
        print(f"\n💾 PDF con texto seleccionable guardado: {output_pdf_path}")
        print(f"📌 Ahora puedes buscar y copiar el texto del PDF")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando PDF seleccionable: {e}")
        import traceback
        traceback.print_exc()
        return False


# ===============================
# ✏️ Crear PDF con texto editable
# ===============================
def create_editable_pdf(original_pdf_path, results_json_path, output_pdf_path):
    """
    Crea un PDF donde el texto detectado es completamente editable.
    El texto se inserta como texto real (no invisible) que puede ser modificado.
    
    Args:
        original_pdf_path: Ruta al PDF original
        results_json_path: Ruta al JSON con resultados
        output_pdf_path: Ruta donde guardar el PDF
    """
    print("\n✏️ Creando PDF con texto editable...")
    
    try:
        # Leer resultados JSON
        with open(results_json_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        # Abrir PDF original
        doc = fitz.open(original_pdf_path)
        
        for page_data in results.get('pages', []):
            page_num = page_data['page_num']
            page = doc[page_num - 1]
            
            # Para PDFs escaneados, limpiar el fondo primero
            # (opcional: descomentar si quieres remover la imagen de fondo)
            # page.clean_contents()
            
            text_regions = page_data.get('text_regions', [])
            
            for region in text_regions:
                bbox = region.get('bbox')
                text = region.get('text', '')
                
                if not bbox or len(bbox) != 4 or not text:
                    continue
                
                try:
                    # Convertir bbox a rectángulo
                    x_coords = [p[0] for p in bbox if p and len(p) >= 2]
                    y_coords = [p[1] for p in bbox if p and len(p) >= 2]
                    
                    if not x_coords or not y_coords:
                        continue
                    
                    # Validar valores
                    x_coords = [x for x in x_coords if x is not None and abs(x) != float('inf')]
                    y_coords = [y for y in y_coords if y is not None and abs(y) != float('inf')]
                    
                    if not x_coords or not y_coords:
                        continue
                    
                    x0, y0 = min(x_coords), min(y_coords)
                    x1, y1 = max(x_coords), max(y_coords)
                    
                    if x0 >= x1 or y0 >= y1:
                        continue
                    
                    rect = fitz.Rect(x0, y0, x1, y1)
                    
                    if rect.is_empty or rect.is_infinite:
                        continue
                    
                    # Calcular tamaño de fuente
                    height = y1 - y0
                    fontsize = max(6, height * 0.7)  # Mínimo 6px
                    
                    # Insertar texto visible y editable
                    rc = page.insert_textbox(
                        rect,
                        text,
                        fontsize=fontsize,
                        fontname="helv",
                        color=(0, 0, 0),
                        align=fitz.TEXT_ALIGN_LEFT,
                        render_mode=0  # 0 = visible y editable
                    )
                    
                    # Si el texto no cabe, intentar con fuente más pequeña
                    if rc < 0:  # rc < 0 significa que no cupo todo el texto
                        fontsize = max(4, fontsize * 0.8)
                        page.insert_textbox(
                            rect,
                            text,
                            fontsize=fontsize,
                            fontname="helv",
                            color=(0, 0, 0),
                            align=fitz.TEXT_ALIGN_LEFT,
                            render_mode=0
                        )
                    
                except (TypeError, ValueError, IndexError) as e:
                    print(f"    ⚠️ Bbox inválida en página {page_num}: {e}")
                    continue
            
            print(f"  ✓ Página {page_num}: {len(text_regions)} textos insertados como editables")
        
        # Guardar PDF
        doc.save(output_pdf_path, garbage=4, deflate=True)
        doc.close()
        
        print(f"\n💾 PDF editable guardado: {output_pdf_path}")
        print(f"📌 El texto ahora es completamente editable en cualquier editor de PDF")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando PDF editable: {e}")
        import traceback
        traceback.print_exc()
        return False


# ===============================
# 6️⃣ Ejecución
# ===============================
if __name__ == "__main__":
    total_start = time.perf_counter()
    
    print("="*60)
    print("🚀 PADDLE OCR - Sistema de Extracción de Texto")
    print("="*60)

    if not os.path.exists(PDF_PATH):
        print(f"❌ Archivo no encontrado: {PDF_PATH}")
        print("💡 Verifica la ruta del archivo PDF")
        exit(1)
    
    try:
        print(f"\n📄 Procesando PDF: {PDF_PATH}")
        file_size = os.path.getsize(PDF_PATH) / 1024 / 1024
        print(f"📦 Tamaño: {file_size:.2f} MB")

        # Paso 1: Detectar tipo de PDF
        print("\n" + "="*60)
        print("🔍 PASO 1: Detectar tipo de documento")
        print("="*60)
        pdf_type_info = detect_pdf_type(PDF_PATH)
        pdf_type = pdf_type_info['type']
        
        all_results = {
            "metadata": {
                "pdf_type": pdf_type,
                "pdf_type_info": pdf_type_info['summary'],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "config": {
                    "max_side": MAX_SIDE,
                    "min_confidence": MIN_CONFIDENCE
                }
            },
            "pages": []
        }

        # Paso 2: Procesar según el tipo de documento
        if pdf_type == 'text_only':
            # Solo texto nativo - No necesita OCR
            print("\n" + "="*60)
            print("📝 PASO 2: Extraer texto nativo (sin OCR)")
            print("="*60)
            native_results = extract_native_text_with_boxes(PDF_PATH)
            
            for page_data in native_results['pages']:
                all_results['pages'].append({
                    **page_data,
                    "processing_method": "native_text",
                    "scale": 1.0
                })
            
            images = []  # No necesitamos imágenes
            
        elif pdf_type == 'text_and_images':
            # Texto nativo + imágenes - OCR solo para imágenes
            print("\n" + "="*60)
            print("📝 PASO 2A: Extraer texto nativo")
            print("="*60)
            native_results = extract_native_text_with_boxes(PDF_PATH)
            
            print("\n" + "="*60)
            print("🖼️ PASO 2B: Extraer y procesar imágenes embebidas")
            print("="*60)
            embedded_images = extract_images_from_pdf(PDF_PATH)
            
            # Inicializar OCR solo si hay imágenes
            ocr_results_by_page = {}
            if embedded_images:
                print("\n" + "="*60)
                print("🧠 PASO 3: Inicializar motor OCR para imágenes")
                print("="*60)
                ocr = init_ocr()
                
                print("\n" + "="*60)
                print("🔍 PASO 4: Aplicar OCR a imágenes embebidas")
                print("="*60)
                
                for img_info in embedded_images:
                    img_path = img_info['image_path']
                    page_num = img_info['page_num']
                    img_bbox_in_pdf = img_info['bbox']
                    
                    print(f"\n🔍 OCR en imagen de página {page_num}")
                    
                    try:
                        # Obtener dimensiones de la imagen extraída
                        img_pil = Image.open(img_path)
                        img_width, img_height = img_pil.size
                        img_pil.close()
                        
                        result = ocr.predict(img_path)
                        
                        if result and isinstance(result, list):
                            for res in result:
                                if hasattr(res, 'save_to_json'):
                                    res.save_to_json(OUT_DIR)
                                
                                # Leer JSON generado
                                img_basename = os.path.splitext(os.path.basename(img_path))[0]
                                json_path = f"{OUT_DIR}/{img_basename}_res.json"
                                
                                if os.path.exists(json_path):
                                    with open(json_path, 'r', encoding='utf-8') as f:
                                        img_ocr_data = json.load(f)
                                        
                                        rec_texts = img_ocr_data.get('rec_texts', [])
                                        rec_scores = img_ocr_data.get('rec_scores', [])
                                        rec_polys = img_ocr_data.get('rec_polys', [])
                                        
                                        # Guardar resultados OCR por página
                                        if page_num not in ocr_results_by_page:
                                            ocr_results_by_page[page_num] = []
                                        
                                        print(f"  📐 Imagen extraída: {img_width}x{img_height}px")
                                        if img_bbox_in_pdf:
                                            print(f"  📍 Posición en PDF: {img_bbox_in_pdf}")
                                        
                                        for i in range(len(rec_texts)):
                                            if rec_scores[i] >= MIN_CONFIDENCE:
                                                poly = rec_polys[i]
                                                
                                                # Transformar coordenadas del espacio de la imagen al espacio del PDF
                                                if img_bbox_in_pdf and poly:
                                                    # Bbox de la imagen en el PDF: [[x0,y0], [x1,y1], [x2,y2], [x3,y3]]
                                                    pdf_x0, pdf_y0 = img_bbox_in_pdf[0]  # esquina superior izquierda
                                                    pdf_x1, pdf_y1 = img_bbox_in_pdf[2]  # esquina inferior derecha
                                                    
                                                    # Dimensiones del bbox en el PDF
                                                    pdf_width = pdf_x1 - pdf_x0
                                                    pdf_height = pdf_y1 - pdf_y0
                                                    
                                                    # Factores de escala
                                                    scale_x = pdf_width / img_width
                                                    scale_y = pdf_height / img_height
                                                    
                                                    # Transformar cada punto del polígono
                                                    transformed_poly = []
                                                    for point in poly:
                                                        x_img, y_img = point
                                                        # Escalar y trasladar
                                                        x_pdf = (x_img * scale_x) + pdf_x0
                                                        y_pdf = (y_img * scale_y) + pdf_y0
                                                        transformed_poly.append([x_pdf, y_pdf])
                                                    
                                                    poly = transformed_poly
                                                
                                                ocr_results_by_page[page_num].append({
                                                    "bbox": poly,
                                                    "text": rec_texts[i],
                                                    "confidence": float(rec_scores[i]),
                                                    "source": "ocr_from_image"
                                                })
                                        
                                        texts_added = sum(1 for i in range(len(rec_texts)) if rec_scores[i] >= MIN_CONFIDENCE)
                                        print(f"  ✓ {texts_added} textos detectados y transformados al espacio del PDF")
                    except Exception as e:
                        print(f"  ❌ Error en OCR de imagen: {e}")
                        import traceback
                        traceback.print_exc()
            
            # Combinar resultados: texto nativo + OCR de imágenes
            for page_data in native_results['pages']:
                page_num = page_data['page_num']
                
                # Agregar texto nativo
                combined_regions = page_data['text_regions'].copy()
                
                # Agregar resultados OCR de imágenes si existen
                if page_num in ocr_results_by_page:
                    combined_regions.extend(ocr_results_by_page[page_num])
                
                all_results['pages'].append({
                    "page_num": page_num,
                    "text_regions": combined_regions,
                    "full_text": page_data['full_text'],
                    "processing_method": "hybrid",
                    "scale": 1.0
                })
            
            images = []
            
        else:  # 'scanned'
            # Documento escaneado - OCR completo
            print("\n" + "="*60)
            print("📸 PASO 2: Convertir PDF a imágenes")
            print("="*60)
            images = pdf_to_scaled_images(PDF_PATH)
            
            if not images:
                print("❌ No se pudieron generar imágenes del PDF")
                exit(1)

            print("\n" + "="*60)
            print("🧠 PASO 3: Inicializar motor OCR")
            print("="*60)
            ocr = init_ocr()

            print("\n" + "="*60)
            print("🔍 PASO 4: Ejecutar OCR en todas las páginas")
            print("="*60)
            ocr_results = run_ocr(images, ocr)
            
            # Usar resultados del OCR
            all_results = ocr_results

        # Guardar resultados consolidados
        if SPLIT_BY_WORDS:
            all_results = apply_word_splitting(all_results)
        
        save_results(all_results)
        
        # Paso final: Dibujar boxes en resolución original
        if pdf_type == 'scanned' and images:
            print("\n" + "="*60)
            print("🎨 PASO FINAL: Generar imágenes anotadas en resolución original")
            print("="*60)
            draw_boxes_original_scale(images, all_results)
        elif pdf_type in ['text_only', 'text_and_images']:
            print("\n" + "="*60)
            print("🎨 PASO FINAL: Generar visualización del texto nativo")
            print("="*60)
            draw_native_text_boxes(PDF_PATH, all_results)

        # Resumen final
        print("\n" + "="*60)
        total_time = log_time("⏱️ TIEMPO TOTAL", total_start)
        print("="*60)
        
        # Generar PDFs adicionales
        print("\n" + "="*60)
        print("📄 GENERANDO PDFs MEJORADOS")
        print("="*60)
        
        # 1. PDF con anotaciones de colores (visual)
        annotated_pdf = f"{OUT_DIR}/documento_anotado.pdf"
        create_annotated_pdf(PDF_PATH, JSON_OUTPUT, annotated_pdf)
        
        # 2. PDF con texto seleccionable (búsqueda y copia)
        searchable_pdf = f"{OUT_DIR}/documento_seleccionable.pdf"
        create_searchable_pdf(PDF_PATH, JSON_OUTPUT, searchable_pdf)
        
        # 3. PDF con texto editable (modificable)
        editable_pdf = f"{OUT_DIR}/documento_editable.pdf"
        create_editable_pdf(PDF_PATH, JSON_OUTPUT, editable_pdf)
        
        print("\n✅ Proceso completado exitosamente")
        print(f"📁 Revisa la carpeta '{OUT_DIR}' para ver los resultados")
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Proceso interrumpido por el usuario")
        exit(1)
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        exit(1)