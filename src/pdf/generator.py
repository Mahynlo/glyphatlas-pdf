"""
Módulo para generación de PDFs con anotaciones y texto.
"""

import json
import fitz  # PyMuPDF


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
                    
                    # Calcular tamaño de fuente basándose en ancho Y altura del bbox
                    height = y1 - y0
                    width = x1 - x0
                    
                    # Comenzar con tamaño basado en altura
                    fontsize = max(6, height * 0.8)
                    fontname = "helv"
                    
                    # Ajustar tamaño de fuente para que el texto quepa en el ancho del bbox
                    # PyMuPDF puede calcular el ancho del texto renderizado
                    text_length = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)
                    
                    # Si el texto es más ancho que el bbox, reducir el tamaño de fuente
                    if text_length > width:
                        # Calcular factor de ajuste basado en la proporción
                        scale_factor = width / text_length
                        fontsize = fontsize * scale_factor * 0.95  # 0.95 para dar margen
                        fontsize = max(4, fontsize)  # Mínimo 4px
                    
                    # Verificar nuevamente con el tamaño ajustado
                    text_length = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)
                    
                    # Si aún no cabe, hacer ajuste fino iterativo
                    attempts = 0
                    while text_length > width and fontsize > 4 and attempts < 5:
                        fontsize *= 0.9
                        text_length = fitz.get_text_length(text, fontname=fontname, fontsize=fontsize)
                        attempts += 1
                    
                    # Insertar texto visible y editable
                    rc = page.insert_textbox(
                        rect,
                        text,
                        fontsize=fontsize,
                        fontname=fontname,
                        color=(0, 0, 0),
                        align=fitz.TEXT_ALIGN_LEFT,
                        render_mode=0  # 0 = visible y editable
                    )
                    
                    # Si aún no cabe (rc < 0), hacer un último intento más agresivo
                    if rc < 0:
                        fontsize = max(3, fontsize * 0.7)
                        page.insert_textbox(
                            rect,
                            text,
                            fontsize=fontsize,
                            fontname=fontname,
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
