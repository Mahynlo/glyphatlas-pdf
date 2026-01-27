"""
Módulo para visualización y dibujo de bounding boxes.
"""

import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
from config import OUT_ANNOTATED


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
