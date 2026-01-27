"""
Módulo para conversión de PDFs a imágenes.
"""

import time
import fitz  # PyMuPDF
from PIL import Image
from config import MAX_SIDE, IMG_DIR, OUT_ANNOTATED


def log_time(label, start):
    """Helper para medir tiempo de ejecución."""
    elapsed = time.perf_counter() - start
    print(f"⏱️ {label}: {elapsed:.3f} s")
    return elapsed


def pdf_to_scaled_images(pdf_path):
    """
    Convierte un PDF a imágenes PNG escaladas.
    
    Args:
        pdf_path: Ruta al archivo PDF
        
    Returns:
        Lista de diccionarios con información de cada imagen generada
    """
    t0 = time.perf_counter()
    
    try:
        doc = fitz.open(pdf_path)
        images = []
        total_pages = len(doc)
        
        print(f"📖 PDF tiene {total_pages} página(s)")

        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)

            w, h = pix.width, pix.height
            max_dim = max(w, h)
            scale = min(1.0, MAX_SIDE / max_dim)

            new_w = int(w * scale)
            new_h = int(h * scale)

            img_original = Image.frombytes("RGB", (w, h), pix.samples)
            img = img_original.copy()

            if scale < 1.0:
                img = img.resize((new_w, new_h), Image.LANCZOS)

            img_path = f"{IMG_DIR}/page_{i+1}.png"
            img.save(img_path, optimize=True, quality=95)
            
            # Guardar imagen original para anotaciones posteriores
            orig_path = f"{OUT_ANNOTATED}/page_{i+1}_original.png"
            img_original.save(orig_path, optimize=True, quality=95)

            images.append({
                "page_num": i + 1,
                "path": img_path,
                "original_path": orig_path,
                "scale": scale,
                "orig_size": (w, h),
                "new_size": (new_w, new_h)
            })

            print(f"📄 Página {i+1}/{total_pages}: {w}x{h} → {new_w}x{new_h} (scale {scale:.4f})")

        doc.close()
        log_time("Render + escalado", t0)
        return images
        
    except Exception as e:
        print(f"❌ Error procesando PDF: {e}")
        raise
