"""
Módulo para extracción de imágenes embebidas de PDFs.
"""

import fitz  # PyMuPDF
from config import IMG_DIR


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
