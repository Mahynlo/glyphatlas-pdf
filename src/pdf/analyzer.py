"""
Módulo para análisis de PDFs.
Detecta el tipo de documento y sus características.
"""

import fitz  # PyMuPDF


def detect_pdf_type(pdf_path):
    """
    Detecta si el PDF contiene texto nativo, imágenes, o es un documento escaneado.
    
    Returns:
        Dict con información por página:
        {
            'type': 'text_only' | 'text_and_images' | 'scanned',
            'pages': [
                {
                    'page_num': 1,
                    'has_text': True/False,
                    'has_images': True/False,
                    'text_blocks': int,
                    'image_count': int
                },
                ...
            ]
        }
    """
    print("\n🔍 Analizando tipo de PDF...")
    
    try:
        doc = fitz.open(pdf_path)
        pages_info = []
        
        total_text_blocks = 0
        total_images = 0
        
        for i, page in enumerate(doc):
            text = page.get_text("text").strip()
            text_blocks = len(page.get_text("blocks"))
            images = page.get_images(full=True)
            
            has_text = len(text) > 50  # Al menos 50 caracteres
            has_images = len(images) > 0
            
            pages_info.append({
                'page_num': i + 1,
                'has_text': has_text,
                'has_images': has_images,
                'text_blocks': text_blocks,
                'image_count': len(images)
            })
            
            total_text_blocks += text_blocks
            total_images += len(images)
            
            status = []
            if has_text:
                status.append(f"📝 {text_blocks} bloques de texto")
            if has_images:
                status.append(f"🖼️ {len(images)} imagen(es)")
            if not has_text and not has_images:
                status.append("📄 Página vacía")
            
            print(f"  Página {i+1}: {', '.join(status)}")
        
        doc.close()
        
        # Determinar tipo general del documento
        pages_with_text = sum(1 for p in pages_info if p['has_text'])
        pages_with_images = sum(1 for p in pages_info if p['has_images'])
        total_pages = len(pages_info)
        
        if pages_with_text == total_pages and pages_with_images == 0:
            doc_type = 'text_only'
            icon = "📝"
            description = "Solo texto nativo (no necesita OCR)"
        elif pages_with_text > 0 and pages_with_images > 0:
            doc_type = 'text_and_images'
            icon = "📝🖼️"
            description = "Texto nativo + imágenes (OCR solo para imágenes)"
        elif pages_with_images > 0:
            doc_type = 'scanned'
            icon = "🖼️"
            description = "Documento escaneado (requiere OCR completo)"
        else:
            doc_type = 'scanned'  # Por defecto, usar OCR
            icon = "❓"
            description = "Tipo desconocido (usar OCR)"
        
        result = {
            'type': doc_type,
            'pages': pages_info,
            'summary': {
                'total_pages': total_pages,
                'pages_with_text': pages_with_text,
                'pages_with_images': pages_with_images,
                'description': description
            }
        }
        
        print(f"\n{icon} Tipo de documento: {description}")
        print(f"   Total: {total_pages} páginas | {pages_with_text} con texto | {pages_with_images} con imágenes")
        
        return result
        
    except Exception as e:
        print(f"❌ Error detectando tipo de PDF: {e}")
        return {'type': 'scanned', 'pages': [], 'summary': {}}
