"""
Sistema OCR para PDFs con PaddleOCR y OnnxTR.
Detecta automáticamente el tipo de documento y aplica el procesamiento óptimo.
Motor OCR configurable en config.py: OCR_ENGINE = "paddleocr" o "onnxtr"
"""
import os
import time

# Importar configuración
from config import *

# Importar módulos
from src.pdf import (
    detect_pdf_type,
    extract_native_text_with_boxes,
    extract_images_from_pdf,
    pdf_to_scaled_images,
    create_annotated_pdf,
    create_searchable_pdf,
    create_editable_pdf,
)
from src.ocr import init_ocr, run_ocr, apply_word_splitting
from src.utils import save_results, validate_pdf, get_profiler
from src.visualization import draw_boxes_original_scale, draw_native_text_boxes

from PIL import Image
import json
import threading


def log_time(label, start):
    """Helper para medir tiempos de ejecución."""
    elapsed = time.perf_counter() - start
    print(f"⏱️ {label}: {elapsed:.3f} s")
    return elapsed


def main():
    """Función principal de ejecución."""
    from config import MAX_PROCESSING_TIME_SEC
    
    # Variable para detectar timeout
    timeout_occurred = False
    result_container = {'success': False}
    
    def run_with_timeout():
        """Ejecuta el procesamiento con posibilidad de timeout."""
        try:
            _run_main()
            result_container['success'] = True
        except Exception as e:
            result_container['error'] = e
    
    # Iniciar procesamiento en thread para poder hacer timeout
    thread = threading.Thread(target=run_with_timeout, daemon=True)
    thread.start()
    thread.join(timeout=MAX_PROCESSING_TIME_SEC)
    
    if thread.is_alive():
        print("\n" + "="*60)
        print("⏱️ LÍMITE DE TIEMPO ALCANZADO")
        print("="*60)
        print(f"❌ El procesamiento excedió el límite de {MAX_PROCESSING_TIME_SEC} segundos ({MAX_PROCESSING_TIME_SEC/60:.1f} minutos)")
        print(f"\n💡 Recomendaciones:")
        print(f"   • Divide el PDF en archivos más pequeños")
        print(f"   • Aumenta MAX_PROCESSING_TIME_SEC en config.py")
        print(f"   • Usa GPU para acelerar el proceso")
        print(f"   • Reduce el número de páginas (MAX_PAGES)")
        exit(1)
    
    if not result_container['success']:
        if 'error' in result_container:
            raise result_container['error']
        exit(1)


def _run_main():
    """Lógica principal de procesamiento."""
    from config import ENABLE_PROFILING, PROFILE_OUTPUT_DIR, PROFILE_SAVE_JSON, PROFILE_SHOW_SUMMARY
    
    # Inicializar profiler
    profiler = get_profiler(enabled=ENABLE_PROFILING)
    profiler.start()
    
    total_start = time.perf_counter()
    
    print("="*60)
    print("🚀 SISTEMA OCR CON PADDLEOCR v5")
    print("="*60)
    
    # Verificar que existe el PDF
    if not os.path.exists(PDF_PATH):
        print(f"❌ No se encontró el PDF: {PDF_PATH}")
        exit(1)
    
    try:
        # Validar límites del PDF
        num_pages, file_size_mb = validate_pdf(PDF_PATH)
        
        print(f"\n📄 Procesando PDF: {PDF_PATH}")

        # PASO 1: Detectar tipo de PDF
        profiler.stage_start("Detección tipo PDF")
        print("\n" + "="*60)
        print("🔍 PASO 1: Detectar tipo de documento")
        print("="*60)
        pdf_type_info = detect_pdf_type(PDF_PATH)
        pdf_type = pdf_type_info['type']
        profiler.stage_end()
        
        # Registrar info del PDF en profiler
        profiler.set_pdf_info(pdf_type, num_pages, file_size_mb)
        
        all_results = {
            "metadata": {
                "pdf_type": pdf_type,
                "pdf_type_info": pdf_type_info['summary'],
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "config": {
                    "max_side": MAX_SIDE,
                    "min_confidence": MIN_CONFIDENCE,
                    "split_by_words": SPLIT_BY_WORDS
                }
            },
            "pages": []
        }

        # PASO 2: Procesar según el tipo de documento
        if pdf_type == 'text_only':
            # Solo texto nativo - No necesita OCR
            profiler.stage_start("Extracción texto nativo")
            print("\n" + "="*60)
            print("📝 PASO 2: Extraer texto nativo (sin OCR)")
            print("="*60)
            native_results = extract_native_text_with_boxes(PDF_PATH)
            profiler.stage_end()
            
            for page_data in native_results['pages']:
                all_results['pages'].append({
                    **page_data,
                    "processing_method": "native_text",
                    "scale": 1.0
                })
            
            images = []
            
        elif pdf_type == 'text_and_images':
            # Procesamiento híbrido
            profiler.stage_start("Procesamiento híbrido (texto + OCR imágenes)")
            images = _process_hybrid_pdf(all_results)
            profiler.stage_end()
            
        else:  # 'scanned'
            # Documento escaneado - OCR completo
            profiler.stage_start("OCR documento escaneado")
            images, all_results = _process_scanned_pdf()
            profiler.stage_end()

        # Aplicar división por palabras si está activado
        if SPLIT_BY_WORDS:
            profiler.stage_start("División por palabras")
            all_results = apply_word_splitting(all_results)
            profiler.stage_end()
        
        # Guardar resultados
        profiler.stage_start("Guardado de resultados")
        save_results(all_results)
        profiler.stage_end()
        
        # Generar visualizaciones
        profiler.stage_start("Generación de visualizaciones")
        _generate_visualizations(pdf_type, images, all_results)
        profiler.stage_end()

        # Generar PDFs mejorados
        profiler.stage_start("Generación de PDFs mejorados")
        _generate_enhanced_pdfs()
        profiler.stage_end()

        # Resumen final
        print("\n" + "="*60)
        log_time("⏱️ TIEMPO TOTAL", total_start)
        print("="*60)
        
        # Guardar y mostrar perfil de rendimiento
        if ENABLE_PROFILING:
            if PROFILE_SAVE_JSON:
                profile_path = profiler.save_profile(PROFILE_OUTPUT_DIR)
                print(f"\n📊 Perfil de rendimiento guardado: {profile_path}")
            
            if PROFILE_SHOW_SUMMARY:
                profiler.print_summary()
        
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


def _process_hybrid_pdf(all_results):
    """Procesa PDFs con texto nativo e imágenes."""
    print("\n" + "="*60)
    print("📝 PASO 2A: Extraer texto nativo")
    print("="*60)
    native_results = extract_native_text_with_boxes(PDF_PATH)
    
    print("\n" + "="*60)
    print("🖼️ PASO 2B: Extraer y procesar imágenes embebidas")
    print("="*60)
    embedded_images = extract_images_from_pdf(PDF_PATH)
    
    ocr_results_by_page = {}
    
    if embedded_images:
        print("\n" + "="*60)
        print("🧠 PASO 3: Inicializar motor OCR para imágenes")
        print("="*60)
        ocr = init_ocr()
        
        print("\n" + "="*60)
        print("🔍 PASO 4: Aplicar OCR a imágenes embebidas")
        print("="*60)
        
        ocr_results_by_page = _process_embedded_images(embedded_images, ocr)
    
    # Combinar resultados
    for page_data in native_results['pages']:
        page_num = page_data['page_num']
        combined_regions = page_data['text_regions'].copy()
        
        if page_num in ocr_results_by_page:
            combined_regions.extend(ocr_results_by_page[page_num])
        
        all_results['pages'].append({
            "page_num": page_num,
            "text_regions": combined_regions,
            "full_text": page_data['full_text'],
            "processing_method": "hybrid",
            "scale": 1.0
        })
    
    return []


def _process_embedded_images(embedded_images, ocr):
    """Aplica OCR a imágenes embebidas en el PDF."""
    ocr_results_by_page = {}
    
    for img_info in embedded_images:
        img_path = img_info['image_path']
        page_num = img_info['page_num']
        img_bbox_in_pdf = img_info['bbox']
        
        print(f"\n🔍 OCR en imagen de página {page_num}")
        
        try:
            # Obtener dimensiones de la imagen
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
                            
                            if page_num not in ocr_results_by_page:
                                ocr_results_by_page[page_num] = []
                            
                            print(f"  📐 Imagen: {img_width}x{img_height}px")
                            if img_bbox_in_pdf:
                                print(f"  📍 Posición en PDF: {img_bbox_in_pdf}")
                            
                            # Transformar coordenadas
                            for i in range(len(rec_texts)):
                                if rec_scores[i] >= MIN_CONFIDENCE:
                                    poly = rec_polys[i]
                                    
                                    if img_bbox_in_pdf and poly:
                                        poly = _transform_coords_to_pdf(
                                            poly, img_bbox_in_pdf, img_width, img_height
                                        )
                                    
                                    ocr_results_by_page[page_num].append({
                                        "bbox": poly,
                                        "text": rec_texts[i],
                                        "confidence": float(rec_scores[i]),
                                        "source": "ocr_from_image"
                                    })
                            
                            texts_added = sum(1 for i in range(len(rec_texts)) if rec_scores[i] >= MIN_CONFIDENCE)
                            print(f"  ✓ {texts_added} textos detectados y transformados")
        except Exception as e:
            print(f"  ❌ Error en OCR de imagen: {e}")
            import traceback
            traceback.print_exc()
    
    return ocr_results_by_page


def _transform_coords_to_pdf(poly, img_bbox_in_pdf, img_width, img_height):
    """Transforma coordenadas de imagen a espacio PDF."""
    pdf_x0, pdf_y0 = img_bbox_in_pdf[0]
    pdf_x1, pdf_y1 = img_bbox_in_pdf[2]
    
    pdf_width = pdf_x1 - pdf_x0
    pdf_height = pdf_y1 - pdf_y0
    
    scale_x = pdf_width / img_width
    scale_y = pdf_height / img_height
    
    transformed_poly = []
    for point in poly:
        x_img, y_img = point
        x_pdf = (x_img * scale_x) + pdf_x0
        y_pdf = (y_img * scale_y) + pdf_y0
        transformed_poly.append([x_pdf, y_pdf])
    
    return transformed_poly


def _process_scanned_pdf():
    """Procesa PDFs completamente escaneados."""
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
    
    return images, ocr_results


def _generate_visualizations(pdf_type, images, all_results):
    """Genera visualizaciones de los resultados."""
    from config import GENERATE_VISUALIZATIONS
    
    if not GENERATE_VISUALIZATIONS:
        print("\n⏭️ Visualizaciones deshabilitadas (GENERATE_VISUALIZATIONS=False)")
        return
    
    if pdf_type == 'scanned' and images:
        print("\n" + "="*60)
        print("🎨 Generar imágenes anotadas en resolución original")
        print("="*60)
        draw_boxes_original_scale(images, all_results)
    elif pdf_type in ['text_only', 'text_and_images']:
        print("\n" + "="*60)
        print("🎨 Generar visualización del texto nativo")
        print("="*60)
        draw_native_text_boxes(PDF_PATH, all_results)


def _generate_enhanced_pdfs():
    """Genera PDFs mejorados (anotado, seleccionable, editable)."""
    from config import GENERATE_ANNOTATED_PDF, GENERATE_SEARCHABLE_PDF, GENERATE_EDITABLE_PDF
    
    # Verificar si hay al menos uno habilitado
    if not any([GENERATE_ANNOTATED_PDF, GENERATE_SEARCHABLE_PDF, GENERATE_EDITABLE_PDF]):
        print("\n⏭️ Generación de PDFs mejorados deshabilitada")
        return
    
    print("\n" + "="*60)
    print("📄 GENERANDO PDFs MEJORADOS")
    print("="*60)
    
    # 1. PDF con anotaciones de colores
    if GENERATE_ANNOTATED_PDF:
        annotated_pdf = f"{OUT_DIR}/documento_anotado.pdf"
        create_annotated_pdf(PDF_PATH, JSON_OUTPUT, annotated_pdf)
    
    # 2. PDF con texto seleccionable
    if GENERATE_SEARCHABLE_PDF:
        searchable_pdf = f"{OUT_DIR}/documento_seleccionable.pdf"
        create_searchable_pdf(PDF_PATH, JSON_OUTPUT, searchable_pdf)
    
    # 3. PDF con texto editable
    if GENERATE_EDITABLE_PDF:
        editable_pdf = f"{OUT_DIR}/documento_editable.pdf"
        create_editable_pdf(PDF_PATH, JSON_OUTPUT, editable_pdf)


if __name__ == "__main__":
    main()
