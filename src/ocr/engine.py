"""
Módulo para el motor OCR con PaddleOCR.
"""

import os
import time
import json
from paddleocr import PaddleOCR
from config import MAX_SIDE, CPU_THREADS, MIN_CONFIDENCE, OUT_DIR


def log_time(label, start):
    """Helper para medir tiempo de ejecución."""
    elapsed = time.perf_counter() - start
    print(f"⏱️ {label}: {elapsed:.3f} s")
    return elapsed


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
            text_recognition_model_name="latin_PP-OCRv5_mobile_rec",  # modelo de reconocimiento
            text_det_limit_side_len=MAX_SIDE,  # límite de longitud
            cpu_threads=CPU_THREADS, 
            use_doc_orientation_classify=False,  # orientación
            use_doc_unwarping=False, 
            use_textline_orientation=False,
            enable_mkldnn=True,  # acelera inferencia en CPU
            # disable_onnxruntime=False  # usa ONNX si está disponible
        )

        log_time("Inicialización OCR", t0)
        return ocr
        
    except Exception as e:
        print(f"❌ Error inicializando OCR: {e}")
        raise


def run_ocr(images, ocr):
    """
    Ejecuta OCR en todas las imágenes y guarda resultados estructurados.
    
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
