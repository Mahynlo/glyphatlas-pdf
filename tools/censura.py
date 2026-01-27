import os
import json
import fitz  # PyMuPDF
import re
from pathlib import Path

# ===============================
# CONFIGURACIÓN
# ===============================
PDF_ORIGINAL = "Para probar la eficiencia de PaddleOCR 3.pdf"  # PDF original
JSON_RESULTS = "output_ocr/ocr_results.json"  # JSON con resultados del OCR
OUTPUT_CENSORED = "output_ocr/documento_censurado.pdf"  # PDF censurado de salida

# Lista de palabras o frases a censurar (case insensitive)
PALABRAS_A_CENSURAR = [
    "confidencial",
    "privado",
    "ALBERTO",
    "LUIS",
    "valdez",
    "MORALES",
    "de",
    "oficio",
    "ocr",
    "documento",
    "para",
    "probar",
    # Agregar más palabras aquí
]

# Configuración de censura
CENSURA_COLOR = (0, 0, 0)  # Negro RGB (puedes cambiar a otro color)
CENSURA_OPACITY = 1.0  # 1.0 = opaco, 0.5 = semi-transparente
MARGEN_EXTRA = 1  # Píxeles extra alrededor de la palabra para asegurar cobertura completa


# ===============================
# 🔍 Buscar palabras en resultados
# ===============================
def buscar_palabras_a_censurar(results_data, palabras_objetivo):
    """
    Busca palabras específicas en los resultados del OCR.
    
    Args:
        results_data: Diccionario con resultados del JSON
        palabras_objetivo: Lista de palabras/frases a buscar
        
    Returns:
        Dict con boxes a censurar por página
    """
    print("\n🔍 Buscando palabras a censurar...")
    
    boxes_a_censurar = {}  # {page_num: [boxes]}
    palabras_lower = [p.lower() for p in palabras_objetivo]
    
    for page_data in results_data.get('pages', []):
        page_num = page_data['page_num']
        text_regions = page_data.get('text_regions', [])
        
        page_boxes = []
        
        for region in text_regions:
            text = region.get('text', '').strip()
            bbox = region.get('bbox')
            
            if not text or not bbox:
                continue
            
            # Buscar coincidencias (case insensitive)
            text_lower = text.lower()
            
            for palabra_objetivo in palabras_objetivo:
                palabra_lower = palabra_objetivo.lower()
                
                # Búsqueda exacta de palabra completa o frase
                if palabra_lower in text_lower:
                    # Verificar si es palabra completa o parte de frase
                    pattern = r'\b' + re.escape(palabra_lower) + r'\b'
                    if re.search(pattern, text_lower):
                        page_boxes.append({
                            'bbox': bbox,
                            'text': text,
                            'palabra_encontrada': palabra_objetivo,
                            'coincidencia_exacta': text_lower == palabra_lower
                        })
                        print(f"  ✓ Página {page_num}: '{text}' → contiene '{palabra_objetivo}'")
                        break  # Evitar duplicados
        
        if page_boxes:
            boxes_a_censurar[page_num] = page_boxes
    
    total_encontradas = sum(len(boxes) for boxes in boxes_a_censurar.values())
    print(f"\n📊 Total: {total_encontradas} coincidencia(s) encontrada(s) en {len(boxes_a_censurar)} página(s)")
    
    return boxes_a_censurar


# ===============================
# ⬛ Aplicar censura al PDF
# ===============================
def aplicar_censura(pdf_path, boxes_por_pagina, output_path):
    """
    Crea un PDF censurado cubriendo las palabras encontradas con rectángulos negros.
    
    Args:
        pdf_path: Ruta al PDF original
        boxes_por_pagina: Dict con boxes a censurar por página
        output_path: Ruta donde guardar el PDF censurado
        
    Returns:
        True si tuvo éxito, False en caso contrario
    """
    print("\n⬛ Aplicando censura al PDF...")
    
    try:
        doc = fitz.open(pdf_path)
        total_censuras = 0
        
        for page_num, boxes in boxes_por_pagina.items():
            page = doc[page_num - 1]
            
            for box_info in boxes:
                bbox = box_info['bbox']
                
                # Convertir bbox de 4 puntos a rectángulo
                x_coords = [p[0] for p in bbox]
                y_coords = [p[1] for p in bbox]
                
                x0 = min(x_coords) - MARGEN_EXTRA
                y0 = min(y_coords) - MARGEN_EXTRA
                x1 = max(x_coords) + MARGEN_EXTRA
                y1 = max(y_coords) + MARGEN_EXTRA
                
                rect = fitz.Rect(x0, y0, x1, y1)
                
                # Dibujar rectángulo negro sólido
                page.draw_rect(rect, color=CENSURA_COLOR, fill=CENSURA_COLOR, width=0)
                
                total_censuras += 1
            
            print(f"  ✓ Página {page_num}: {len(boxes)} región(es) censurada(s)")
        
        # Guardar PDF censurado
        doc.save(output_path, garbage=4, deflate=True)
        doc.close()
        
        print(f"\n💾 PDF censurado guardado: {output_path}")
        print(f"⬛ Total de censuras aplicadas: {total_censuras}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error aplicando censura: {e}")
        import traceback
        traceback.print_exc()
        return False


# ===============================
# 🔍 Buscar por patrón regex
# ===============================
def buscar_por_patron(results_data, patron_regex):
    """
    Busca coincidencias usando expresiones regulares.
    Útil para censurar números de teléfono, emails, DNI, etc.
    
    Args:
        results_data: Diccionario con resultados del JSON
        patron_regex: Patrón regex (ej: r'\d{3}-\d{3}-\d{4}' para teléfonos)
        
    Returns:
        Dict con boxes a censurar por página
    """
    print(f"\n🔍 Buscando patrón: {patron_regex}")
    
    boxes_a_censurar = {}
    pattern = re.compile(patron_regex, re.IGNORECASE)
    
    for page_data in results_data.get('pages', []):
        page_num = page_data['page_num']
        text_regions = page_data.get('text_regions', [])
        
        page_boxes = []
        
        for region in text_regions:
            text = region.get('text', '').strip()
            bbox = region.get('bbox')
            
            if not text or not bbox:
                continue
            
            # Buscar patrón
            if pattern.search(text):
                page_boxes.append({
                    'bbox': bbox,
                    'text': text,
                    'patron': patron_regex
                })
                print(f"  ✓ Página {page_num}: '{text}' → coincide con patrón")
        
        if page_boxes:
            boxes_a_censurar[page_num] = page_boxes
    
    total_encontradas = sum(len(boxes) for boxes in boxes_a_censurar.values())
    print(f"\n📊 Total: {total_encontradas} coincidencia(s) encontrada(s)")
    
    return boxes_a_censurar


# ===============================
# 📋 Generar reporte de censura
# ===============================
def generar_reporte(boxes_por_pagina, output_txt):
    """
    Genera un reporte de texto con las palabras censuradas.
    
    Args:
        boxes_por_pagina: Dict con boxes censuradas
        output_txt: Ruta del archivo de reporte
    """
    print(f"\n📋 Generando reporte de censura...")
    
    try:
        with open(output_txt, 'w', encoding='utf-8') as f:
            f.write("=" * 60 + "\n")
            f.write("REPORTE DE CENSURA\n")
            f.write("=" * 60 + "\n\n")
            
            total = 0
            for page_num in sorted(boxes_por_pagina.keys()):
                boxes = boxes_por_pagina[page_num]
                f.write(f"\nPÁGINA {page_num}:\n")
                f.write("-" * 40 + "\n")
                
                for i, box in enumerate(boxes, 1):
                    text = box.get('text', '')
                    palabra = box.get('palabra_encontrada', box.get('patron', ''))
                    f.write(f"{i}. Texto censurado: '{text}'\n")
                    f.write(f"   Coincide con: '{palabra}'\n")
                    f.write(f"   Coordenadas: {box['bbox']}\n\n")
                    total += 1
            
            f.write("\n" + "=" * 60 + "\n")
            f.write(f"TOTAL DE CENSURAS: {total}\n")
            f.write("=" * 60 + "\n")
        
        print(f"💾 Reporte guardado: {output_txt}")
        
    except Exception as e:
        print(f"⚠️ Error generando reporte: {e}")


# ===============================
# 🚀 Ejecución principal
# ===============================
def main():
    print("=" * 60)
    print("⬛ SISTEMA DE CENSURA DE DOCUMENTOS")
    print("=" * 60)
    
    # Verificar archivos
    if not os.path.exists(PDF_ORIGINAL):
        print(f"❌ PDF original no encontrado: {PDF_ORIGINAL}")
        return
    
    if not os.path.exists(JSON_RESULTS):
        print(f"❌ JSON de resultados no encontrado: {JSON_RESULTS}")
        print("💡 Ejecuta primero main_2.py para generar los resultados")
        return
    
    # Cargar resultados del OCR
    print(f"\n📂 Cargando resultados desde: {JSON_RESULTS}")
    with open(JSON_RESULTS, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    print(f"✓ Resultados cargados: {len(results.get('pages', []))} páginas")
    
    # Mostrar palabras a censurar
    print(f"\n🎯 Palabras objetivo a censurar:")
    for palabra in PALABRAS_A_CENSURAR:
        print(f"  • {palabra}")
    
    # Buscar palabras
    boxes_a_censurar = buscar_palabras_a_censurar(results, PALABRAS_A_CENSURAR)
    
    if not boxes_a_censurar:
        print("\n⚠️ No se encontraron palabras para censurar")
        print("💡 Verifica la lista PALABRAS_A_CENSURAR en la configuración")
        return
    
    # Aplicar censura
    success = aplicar_censura(PDF_ORIGINAL, boxes_a_censurar, OUTPUT_CENSORED)
    
    if success:
        # Generar reporte
        reporte_path = "output_ocr/reporte_censura.txt"
        generar_reporte(boxes_a_censurar, reporte_path)
        
        print("\n" + "=" * 60)
        print("✅ CENSURA COMPLETADA")
        print("=" * 60)
        print(f"📄 PDF censurado: {OUTPUT_CENSORED}")
        print(f"📋 Reporte: {reporte_path}")
    else:
        print("\n❌ No se pudo completar la censura")


# ===============================
# Ejemplos de uso avanzado
# ===============================
def ejemplo_censurar_emails():
    """Ejemplo: Censurar todos los emails en el documento"""
    print("\n📧 Censurando emails...")
    
    with open(JSON_RESULTS, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Patrón regex para emails
    patron_email = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    boxes = buscar_por_patron(results, patron_email)
    
    if boxes:
        aplicar_censura(PDF_ORIGINAL, boxes, "output_ocr/documento_sin_emails.pdf")


def ejemplo_censurar_telefonos():
    """Ejemplo: Censurar números de teléfono"""
    print("\n📞 Censurando teléfonos...")
    
    with open(JSON_RESULTS, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Patrón para teléfonos (varios formatos)
    patron_telefono = r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b'
    boxes = buscar_por_patron(results, patron_telefono)
    
    if boxes:
        aplicar_censura(PDF_ORIGINAL, boxes, "output_ocr/documento_sin_telefonos.pdf")


def ejemplo_censurar_dni():
    """Ejemplo: Censurar DNI/NIE españoles"""
    print("\n🆔 Censurando DNI/NIE...")
    
    with open(JSON_RESULTS, 'r', encoding='utf-8') as f:
        results = json.load(f)
    
    # Patrón para DNI: 8 dígitos + letra
    patron_dni = r'\b\d{8}[A-Z]\b'
    boxes = buscar_por_patron(results, patron_dni)
    
    if boxes:
        aplicar_censura(PDF_ORIGINAL, boxes, "output_ocr/documento_sin_dni.pdf")


if __name__ == "__main__":
    main()
    
    # Descomentar para ejecutar ejemplos:
    # ejemplo_censurar_emails()
    # ejemplo_censurar_telefonos()
    # ejemplo_censurar_dni()
