"""
Módulo para el motor OCR con PaddleOCR y OnnxTR.
Usa OCR_ENGINE de config.py para seleccionar el motor.
"""

import os
import time
import json
from config import MAX_SIDE, CPU_THREADS, MIN_CONFIDENCE, OUT_DIR, OCR_ENGINE

# Imports condicionales según el motor configurado
if OCR_ENGINE == "onnxtr":
    from onnxtr.models import ocr_predictor
    from onnxtr.io import DocumentFile
    import cv2
else:
    from paddleocr import PaddleOCR


def log_time(label, start):
    """Helper para medir tiempo de ejecución."""
    elapsed = time.perf_counter() - start
    print(f"⏱️ {label}: {elapsed:.3f} s")
    return elapsed


def init_ocr():
    """
    Inicializa el motor OCR según OCR_ENGINE en config.py.
    
    Returns:
        Instancia de PaddleOCR o predictor OnnxTR según configuración
    """
    t0 = time.perf_counter()
    
    try:
        if OCR_ENGINE == "onnxtr":
            print("🚀 Inicializando OnnxTR (motor ONNX optimizado)...")
            
            # Configuración optimizada: balance velocidad/calidad
            predictor = ocr_predictor(
                det_arch="db_mobilenet_v3_large",
                reco_arch="crnn_mobilenet_v3_small",
                detect_language=False,
                assume_straight_pages=True,
                straighten_pages=False,
                preserve_aspect_ratio=True,
                symmetric_pad=False,  # Desactivado para velocidad
                
                load_in_8_bit=False
            )
            log_time("Inicialización OnnxTR", t0)
            return predictor
        else:
            print("🔧 Inicializando PaddleOCR...")
            ocr = PaddleOCR(
                ocr_version="PP-OCRv5",
                lang="es",
                text_detection_model_name="PP-OCRv5_mobile_det",
                text_recognition_model_name="PP-OCRv5_mobile_rec",
                text_det_limit_side_len=MAX_SIDE,
                cpu_threads=CPU_THREADS, 
                use_doc_orientation_classify=False,
                use_doc_unwarping=False, 
                use_textline_orientation=False,
                enable_mkldnn=True,
            )
            log_time("Inicialización PaddleOCR", t0)
            return ocr
        
    except Exception as e:
        print(f"❌ Error inicializando {OCR_ENGINE.upper()}: {e}")
        raise


def run_ocr(images, ocr):
    """
    Ejecuta OCR en todas las imágenes usando el motor configurado.
    
    Args:
        images: Lista de diccionarios con info de imágenes
        ocr: Instancia de PaddleOCR o predictor OnnxTR
        
    Returns:
        Diccionario con todos los resultados del OCR
    """
    # Delegar al motor específico
    if OCR_ENGINE == "onnxtr":
        return _run_ocr_onnxtr(images, ocr)
    else:
        return _run_ocr_paddle(images, ocr)


def run_ocr_direct_pdf(pdf_path, ocr, scale=2.0):
    """
    Ejecuta OCR directamente en un PDF usando OnnxTR.from_pdf().
    Más rápido que convertir a imágenes manualmente (usa pypdfium2).
    
    Solo funciona con OnnxTR. Para PDFs escaneados completos.
    
    Args:
        pdf_path: Ruta al archivo PDF
        ocr: Predictor OnnxTR
        scale: Factor de escala de renderizado (1.0=72dpi, 2.0=144dpi, 3.0=216dpi)
        
    Returns:
        Diccionario con todos los resultados del OCR
    """
    if OCR_ENGINE != "onnxtr":
        raise ValueError("run_ocr_direct_pdf solo funciona con OCR_ENGINE='onnxtr'")
    
    import fitz  # Para obtener dimensiones originales del PDF
    from onnxtr.io import DocumentFile
    import numpy as np
    
    t0 = time.perf_counter()
    
    # Calcular DPI equivalente para mostrar
    dpi_equivalent = int(72 * scale)
    
    # Cargar PDF directamente (usa pypdfium2 internamente)
    print(f"\n📄 Cargando PDF con DocumentFile (scale={scale:.1f}, ~{dpi_equivalent} DPI)...")
    doc_images = DocumentFile.from_pdf(pdf_path, scale=scale)
    num_pages = len(doc_images)
    print(f"✅ PDF cargado: {num_pages} página(s)")
    
    # Ejecutar OCR en batch (más rápido)
    print(f"\n🔍 Procesando {num_pages} página(s) con OnnxTR...")
    batch_start = time.perf_counter()
    result = ocr(doc_images)
    log_time("OCR total (batch)", batch_start)
    
    # Obtener dimensiones originales del PDF para coordenadas precisas
    pdf_doc = fitz.open(pdf_path)
    
    all_results = {
        "pages": [],
        "metadata": {
            "ocr_engine": "onnxtr",
            "processing_mode": "direct_pdf",
            "scale": scale,
            "dpi_equivalent": dpi_equivalent,
            "min_confidence": MIN_CONFIDENCE
        }
    }
    
    # Procesar resultados por página
    for page_idx, (page_result, page_img) in enumerate(zip(result.pages, doc_images)):
        page_num = page_idx + 1
        print(f"\n📄 Procesando página {page_num}/{num_pages}")
        
        # Obtener dimensiones de la imagen renderizada
        img_h, img_w = page_img.shape[:2]
        
        # Obtener dimensiones originales del PDF
        pdf_page = pdf_doc[page_idx]
        pdf_w = pdf_page.rect.width
        pdf_h = pdf_page.rect.height
        
        # Factor de escala: imagen_renderizada / PDF_original
        scale_x = img_w / pdf_w
        scale_y = img_h / pdf_h
        
        text_regions = []
        full_text_parts = []
        
        # Iterar sobre bloques -> líneas -> palabras
        for block in page_result.blocks:
            for line in block.lines:
                for word in line.words:
                    # Coordenadas normalizadas (0.0 a 1.0)
                    (xmin, ymin), (xmax, ymax) = word.geometry
                    
                    # Convertir a coordenadas de PDF original
                    # Paso 1: De normalizado a píxeles de imagen renderizada
                    x0_img = xmin * img_w
                    y0_img = ymin * img_h
                    x1_img = xmax * img_w
                    y1_img = ymax * img_h
                    
                    # Paso 2: De imagen renderizada a espacio PDF original
                    x0 = x0_img / scale_x
                    y0 = y0_img / scale_y
                    x1 = x1_img / scale_x
                    y1 = y1_img / scale_y
                    
                    confidence = word.confidence
                    text = word.value
                    
                    if confidence >= MIN_CONFIDENCE:
                        # Formato bbox compatible: [[x0,y0], [x1,y0], [x1,y1], [x0,y1]]
                        bbox = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
                        
                        text_regions.append({
                            "bbox": bbox,
                            "text": text,
                            "confidence": float(confidence)
                        })
                        full_text_parts.append(text)
        
        page_data = {
            "page_num": page_num,
            "text_regions": text_regions,
            "full_text": " ".join(full_text_parts),
            "processing_method": "onnxtr_direct_pdf",
            "scale": 1.0,  # Ya está en coordenadas PDF originales
            "render_scale": scale,
            "img_size": (img_w, img_h),
            "pdf_size": (pdf_w, pdf_h)
        }
        
        all_results["pages"].append(page_data)
        print(f"✓ Total: {len(text_regions)} región(es) de texto")
    
    pdf_doc.close()
    
    total_time = time.perf_counter() - t0
    avg_time = total_time / num_pages if num_pages > 0 else 0
    print(f"\n⏱️ OCR total: {total_time:.3f} s ({avg_time:.3f} s/página)")
    
    return all_results


def _run_ocr_paddle(images, ocr):
    """
    Ejecuta OCR con PaddleOCR (motor original).
    
    Args:
        images: Lista de diccionarios con info de imágenes
        ocr: Instancia de PaddleOCR
        
    Returns:
        Diccionario con todos los resultados del OCR
    """
    from src.utils.io import save_results
    
    ocr_total = 0.0
    all_results = {
        "metadata": {
            "total_pages": len(images),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "engine": "PaddleOCR",
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
                "upscale_factor": img.get("upscale_factor", 1.0),
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
                
                # Obtener factores de escala
                scale = img["scale"]
                upscale_factor = img.get("upscale_factor", 1.0)
                
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
                            
                            # Ajustar coordenadas por upscaling
                            # Las coordenadas están en imagen procesada, ajustar a PDF original
                            if upscale_factor != 1.0:
                                bbox = [[x / upscale_factor, y / upscale_factor] for x, y in bbox]
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
                                    # Ajustar coordenadas por upscaling
                                    if upscale_factor != 1.0:
                                        poly = [[x / upscale_factor, y / upscale_factor] for x, y in poly]
                                    
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


def _run_ocr_onnxtr(images, predictor):
    """
    Ejecuta OCR con OnnxTR (motor optimizado ONNX).
    
    Args:
        images: Lista de diccionarios con info de imágenes
        predictor: Predictor OnnxTR
        
    Returns:
        Diccionario con todos los resultados del OCR
    """
    from src.utils.io import save_results
    
    ocr_total = 0.0
    all_results = {
        "metadata": {
            "total_pages": len(images),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "engine": "OnnxTR",
            "config": {
                "detector": "db_mobilenet_v3_large",
                "recognizer": "crnn_mobilenet_v3_large",
                "min_confidence": MIN_CONFIDENCE
            }
        },
        "pages": []
    }
    
    # Cargar todas las imágenes
    print(f"\n🔍 Procesando {len(images)} página(s) con OnnxTR...")
    image_arrays = []
    
    for img_info in images:
        img = cv2.imread(img_info['path'])
        img_rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        image_arrays.append(img_rgb)
    
    # Ejecutar OCR en batch
    ocr_start = time.perf_counter()
    result = predictor(image_arrays)
    ocr_total = log_time("OCR total (batch)", ocr_start)
    
    # Procesar cada página
    for page_idx, (img_info, page_img, page_pred) in enumerate(zip(images, image_arrays, result.pages)):
        page_num = img_info['page_num']
        
        print(f"\n📄 Procesando página {page_num}/{len(images)}")
        
        h, w = page_img.shape[:2]
        scale = img_info.get('scale', 1.0)
        upscale_factor = img_info.get('upscale_factor', 1.0)
        
        text_regions = []
        full_text_parts = []
        
        # Recorrer jerarquía: Bloques -> Líneas -> Palabras
        for block in page_pred.blocks:
            for line in block.lines:
                for word in line.words:
                    (xmin, ymin), (xmax, ymax) = word.geometry
                    
                    # Convertir a píxeles
                    x0_px = xmin * w
                    y0_px = ymin * h
                    x1_px = xmax * w
                    y1_px = ymax * h
                    
                    # Ajustar por upscaling (si se aplicó)
                    # Las coordenadas están en imagen aumentada, convertir a original
                    x0_px = x0_px / upscale_factor
                    y0_px = y0_px / upscale_factor
                    x1_px = x1_px / upscale_factor
                    y1_px = y1_px / upscale_factor
                    
                    # Aplicar escala inversa para coordenadas finales del PDF
                    x0 = x0_px / scale
                    y0 = y0_px / scale
                    x1 = x1_px / scale
                    y1 = y1_px / scale
                    
                    confidence = word.confidence
                    text = word.value
                    
                    if confidence >= MIN_CONFIDENCE:
                        # Formato bbox compatible: [[x0,y0], [x1,y0], [x1,y1], [x0,y1]]
                        bbox = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
                        
                        text_regions.append({
                            "bbox": bbox,
                            "text": text,
                            "confidence": float(confidence)
                        })
                        full_text_parts.append(text)
        
        page_data = {
            "page_num": page_num,
            "image_path": img_info["path"],
            "scale": scale,
            "upscale_factor": upscale_factor,
            "processing_time": round(ocr_total / len(images), 3),
            "text_regions": text_regions,
            "full_text": " ".join(full_text_parts)
        }
        
        all_results["pages"].append(page_data)
        
        print(f"✓ Total: {len(text_regions)} región(es) de texto")
        
        # Guardar JSON individual
        page_json = {
            "page_num": page_num,
            "text_regions": text_regions
        }
        
        output_path = os.path.join(OUT_DIR, f"page_{page_num}_res.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(page_json, f, ensure_ascii=False, indent=2)
    
    print(f"\n⏱️ OCR total: {ocr_total:.3f} s ({ocr_total/len(images):.3f} s/página)")
    
    # Guardar resultados consolidados
    save_results(all_results)
    
    return all_results
