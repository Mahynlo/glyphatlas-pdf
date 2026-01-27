"""
División de bounding boxes de líneas en palabras.
"""
from config import SPLIT_BY_WORDS, WORD_SPACING_THRESHOLD


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
