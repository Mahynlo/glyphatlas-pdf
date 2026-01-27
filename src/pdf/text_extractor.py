"""
Módulo para extracción de texto nativo de PDFs.
"""

import fitz  # PyMuPDF
from config import SPLIT_BY_WORDS


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
