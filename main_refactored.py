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

def titulo(num_paso):
    print("\n" + " "*5 +"╔"+ "="*ESPACIADO + "="*(len(num_paso) + 1) + "="*ESPACIADO  + "╗" )
    print(" "*5 + "║" + " "*ESPACIADO + " "*(len(num_paso)+1) + " "*ESPACIADO  + "║" + " "*5 )
    print("="*5 + "║" + " "*ESPACIADO + f"{num_paso}" + " "*ESPACIADO  + "║" + "="*5 )
    print(" "*5 + "║" + " "*ESPACIADO + " "*(len(num_paso)+1) + " "*ESPACIADO  + "║" + " "*5 )
    print(" "*5 + "╚" + "="*ESPACIADO + "="*(len(num_paso) + 1) + "="*ESPACIADO  + "╝")


def sub_titulos(num_paso):
    print("\n" + " "*5 +"╔"+ "="*ESPACIADO + "="*(len(num_paso) + 1) + "="*ESPACIADO  + "╗" )
    print("="*5 + "║" + " "*ESPACIADO + f"{num_paso}" + " "*ESPACIADO  + "║" + "="*5 )
    print(" "*5 + "╚" + "="*ESPACIADO + "="*(len(num_paso) + 1) + "="*ESPACIADO  + "╝")

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
    
    #Titulo de la pp en terminal
    titulo(TITULO_APP)
    
    
    # Verificar que existe el PDF
    if not os.path.exists(PDF_PATH):
        print(f"❌ No se encontró el PDF: {PDF_PATH}")
        exit(1)
    
    try:
        # Validar límites del PDF
        num_pages, file_size_mb = validate_pdf(PDF_PATH)
        
        print(f"\n📄 Procesando PDF: {PDF_PATH}")
        
        #paso1_texto="🔍 PASO 1: Detectar tipo de documento"
        
        # PASO 1: Detectar tipo de PDF
        profiler.stage_start("Detección tipo PDF")
        paso1_texto="🔍 PASO 1: Detectar tipo de documento"
        sub_titulos(paso1_texto)
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
            
            paso2_tetxto="📝 PASO 2: Extraer texto nativo (sin OCR)"
            sub_titulos(paso2_tetxto)
            
            
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
    paso2A_texto="📝 PASO 2A: Extraer texto nativo"
    sub_titulos(paso2A_texto)
    native_results = extract_native_text_with_boxes(PDF_PATH)
    
    paso2B_texto_hybrid="🖼️ PASO 2B: Extraer y procesar imágenes embebidas"
    sub_titulos(paso2B_texto_hybrid)
    embedded_images = extract_images_from_pdf(PDF_PATH)
    
    ocr_results_by_page = {}
    
    if embedded_images:
        
        paso3_texto_hybrid="🧠 PASO 3: Inicializar motor OCR para imágenes"
        sub_titulos(paso3_texto_hybrid)
        ocr = init_ocr()
        
        paso4_texto_hybrid="🔍 PASO 4: Aplicar OCR a imágenes embebidas"
        sub_titulos(paso4_texto_hybrid)
        
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

    print("imagenes:",embedded_images)
    
    for img_info in embedded_images:
        img_path = img_info['image_path']
        page_num = img_info['page_num']
        img_bbox_in_pdf = img_info['bbox']

        print("imagen path: ",img_path)

        
        print(f"\n🔍 OCR en imagen de página {page_num}")
        
        try:
            # Obtener dimensiones de la imagen
            img_pil = Image.open(img_path)
            img_width, img_height = img_pil.size
            img_pil.close()
            
            # OnnxTR vs PaddleOCR tienen diferentes métodos
            if OCR_ENGINE == "onnxtr":
                from onnxtr.io import DocumentFile
                doc = DocumentFile.from_images(img_path)
                result = ocr(doc)
                
                # Procesar resultado de OnnxTR (diferente a PaddleOCR)
                if page_num not in ocr_results_by_page:
                    ocr_results_by_page[page_num] = []
                
                print(f"  📐 Imagen: {img_width}x{img_height}px")
                if img_bbox_in_pdf:
                    print(f"  📍 Posición en PDF: {img_bbox_in_pdf}")
                
                # Extraer resultados de OnnxTR
                if hasattr(result, 'pages') and result.pages:
                    page_result = result.pages[0]  # Primera (y única) página
                    texts_added = 0
                    
                    for block in page_result.blocks:
                        for line in block.lines:
                            # Obtener texto y confianza
                            text = " ".join(word.value for word in line.words)
                            confidence = sum(word.confidence for word in line.words) / len(line.words) if line.words else 0
                            
                            if confidence >= MIN_CONFIDENCE:
                                # Obtener coordenadas del box
                                # line.geometry es ((x_min, y_min), (x_max, y_max)) normalizado [0,1]
                                (x_min, y_min), (x_max, y_max) = line.geometry
                                
                                # Convertir a coordenadas de píxeles de la imagen
                                poly = [
                                    [x_min * img_width, y_min * img_height],
                                    [x_max * img_width, y_min * img_height],
                                    [x_max * img_width, y_max * img_height],
                                    [x_min * img_width, y_max * img_height]
                                ]
                                
                                # Transformar a coordenadas PDF si es necesario
                                if img_bbox_in_pdf:
                                    poly = _transform_coords_to_pdf(
                                        poly, img_bbox_in_pdf, img_width, img_height
                                    )
                                
                                ocr_results_by_page[page_num].append({
                                    "bbox": poly,
                                    "text": text,
                                    "confidence": float(confidence),
                                    "source": "ocr_from_image"
                                })
                                texts_added += 1
                    
                    print(f"  ✓ {texts_added} textos detectados y transformados")
                    
            else:
                # PaddleOCR
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
    from src.ocr.engine import run_ocr_direct_pdf
    
    # Inicializar motor OCR primero
    paso3_texto_scaned="🧠 PASO 3: Inicializar motor OCR"
    sub_titulos(paso3_texto_scaned)
    ocr = init_ocr()
    
    # Modo optimizado: pasar PDF directamente a OnnxTR
    if OCR_ENGINE == "onnxtr":
        print("\n⚡ Modo optimizado: Procesando PDF directamente con OnnxTR")
        print("   (sin conversión manual a imágenes, usa pypdfium2 internamente)")
        
        paso4_texto_direct="🔍 PASO 4: Ejecutar OCR directo en PDF"
        sub_titulos(paso4_texto_direct)
        
        # Calcular scale óptimo: balance entre DPI configurado y tamaño razonable
        from config import RENDER_DPI, MAX_SIDE
        import fitz
        
        # Obtener tamaño del PDF
        pdf_doc = fitz.open(PDF_PATH)
        first_page = pdf_doc[0]
        pdf_w, pdf_h = first_page.rect.width, first_page.rect.height
        pdf_max = max(pdf_w, pdf_h)
        pdf_doc.close()
        
        # Calcular scale basado en DPI
        dpi_scale = RENDER_DPI / 72.0
        
        # Calcular scale que daría MAX_SIDE * 1.5 (suficiente para OCR)
        target_size = MAX_SIDE * 1.5  # 1500px es suficiente para buena calidad
        optimal_scale = target_size / pdf_max
        
        # Usar el menor entre ambos para no crear imágenes innecesariamente grandes
        render_scale = min(dpi_scale, optimal_scale)
        
        # Limitar entre 1.2-2.0 para mejor velocidad
        render_scale = max(1.2, min(2.0, render_scale))
        
        ocr_results = run_ocr_direct_pdf(PDF_PATH, ocr, scale=render_scale)
        images = []  # No hay imágenes guardadas en modo directo
        
    else:
        # PaddleOCR: convertir a imágenes primero
        paso2_texto_scaned="📸 PASO 2: Convertir PDF a imágenes"
        sub_titulos(paso2_texto_scaned)
        images = pdf_to_scaled_images(PDF_PATH)
        
        if not images:
            print("❌ No se pudieron generar imágenes del PDF")
            exit(1)
        
        paso4_texto_scaned="🔍 PASO 4: Ejecutar OCR en todas las páginas"
        sub_titulos(paso4_texto_scaned)
        ocr_results = run_ocr(images, ocr)
    
    return images, ocr_results


def _generate_visualizations(pdf_type, images, all_results):
    """Genera visualizaciones de los resultados."""
    from config import GENERATE_VISUALIZATIONS
    
    if not GENERATE_VISUALIZATIONS:
        print("\n⏭️ Visualizaciones deshabilitadas (GENERATE_VISUALIZATIONS=False)")
        return
    
    if pdf_type == 'scanned' and images:
        
        generar_vis="🎨 Generar imágenes anotadas en resolución original"
        sub_titulos(generar_vis)
        draw_boxes_original_scale(images, all_results)
    elif pdf_type in ['text_only', 'text_and_images']:
        
        generar_vis_nat="🎨 Generar visualización del texto nativo"
        sub_titulos(generar_vis_nat)
        draw_native_text_boxes(PDF_PATH, all_results)


def _generate_enhanced_pdfs():
    """Genera PDFs mejorados (anotado, seleccionable, editable)."""
    from config import GENERATE_ANNOTATED_PDF, GENERATE_SEARCHABLE_PDF, GENERATE_EDITABLE_PDF
    
    # Verificar si hay al menos uno habilitado
    if not any([GENERATE_ANNOTATED_PDF, GENERATE_SEARCHABLE_PDF, GENERATE_EDITABLE_PDF]):
        print("\n⏭️ Generación de PDFs mejorados deshabilitada")
        return
    
    
    pdf_mejorado="📄 GENERANDO PDFs MEJORADOS"
    sub_titulos(pdf_mejorado)
    
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
