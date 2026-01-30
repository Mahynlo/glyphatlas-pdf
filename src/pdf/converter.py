"""
Módulo para conversión de PDFs a imágenes.
"""

import time
import fitz  # PyMuPDF
from PIL import Image
import cv2
import numpy as np
from config import MAX_SIDE, IMG_DIR, OUT_ANNOTATED, ENABLE_UPSCALING, MIN_IMAGE_SIZE, UPSCALE_FACTOR


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
            
            # Guardar dimensiones originales del PDF
            orig_w, orig_h = w, h
            upscale_applied = 1.0  # Factor de upscaling aplicado

            # Aplicar upscaling si la imagen es muy pequeña
            if ENABLE_UPSCALING and max_dim < MIN_IMAGE_SIZE:
                print(f"   🔍 Imagen pequeña detectada ({max_dim}px < {MIN_IMAGE_SIZE}px)")
                print(f"   ⬆️  Aplicando upscaling con factor {UPSCALE_FACTOR}x...")
                img = _upscale_image(img, UPSCALE_FACTOR)
                w, h = img.size
                max_dim = max(w, h)
                upscale_applied = UPSCALE_FACTOR  # Guardar factor para ajustar coordenadas
                print(f"   ✓ Nueva resolución: {w}x{h}px")
                # Recalcular escala con nuevo tamaño
                scale = min(1.0, MAX_SIDE / max_dim)
                new_w = int(w * scale)
                new_h = int(h * scale)
            
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
                "upscale_factor": upscale_applied,  # Nuevo: factor de upscaling
                "orig_size": (orig_w, orig_h),  # Tamaño original del PDF
                "new_size": (new_w, new_h)
            })

            print(f"📄 Página {i+1}/{total_pages}: {orig_w}x{orig_h} → {w}x{h} → {new_w}x{new_h} (scale {scale:.4f}, upscale {upscale_applied:.1f}x)")

        doc.close()
        log_time("Render + escalado", t0)
        return images
        
    except Exception as e:
        print(f"❌ Error procesando PDF: {e}")
        raise


def _upscale_image(img, factor):
    """
    Aumenta resolución de imagen para mejorar OCR usando OpenCV.
    Orden optimizado: Limpieza → Upscaling → Contraste → Nitidez
    
    Args:
        img: Imagen PIL
        factor: Factor de aumento (2.0 = duplicar)
        
    Returns:
        Imagen PIL con mayor resolución
    """
    # Convertir PIL a OpenCV
    img_array = np.array(img)
    img_array = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    h, w = img_array.shape[:2]
    new_w = int(w * factor)
    new_h = int(h * factor)
    
    # 1. LIMPIEZA en imagen pequeña (rápido) - Bilateral Filter
    #    Reduce ruido preservando bordes del texto
    cleaned = cv2.bilateralFilter(img_array, d=5, sigmaColor=50, sigmaSpace=50)
    
    # 2. UPSCALING con INTER_LANCZOS4 - Mejor interpolación
    #    Crece la imagen ya limpia
    upscaled = cv2.resize(cleaned, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
    
    # 3. CONTRASTE con CLAHE - Resalta el texto
    #    Mejora visibilidad en imagen grande
    lab = cv2.cvtColor(upscaled, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
    l = clahe.apply(l)
    enhanced = cv2.merge([l, a, b])
    enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
    
    # 4. NITIDEZ FINAL con Unsharp Mask - Un pase final
    #    Da claridad al texto para mejor OCR
    gaussian = cv2.GaussianBlur(enhanced, (0, 0), 2.0)
    result = cv2.addWeighted(enhanced, 1.5, gaussian, -0.5, 0)
    
    # Convertir de vuelta a PIL RGB
    result = cv2.cvtColor(result, cv2.COLOR_BGR2RGB)
    return Image.fromarray(result)

