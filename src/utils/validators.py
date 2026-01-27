"""
Validadores para PDFs y límites de procesamiento.
"""
import os
import fitz
from config import MAX_FILE_SIZE_MB, MAX_PAGES, WARN_FILE_SIZE_MB, WARN_PAGES


def validate_pdf(pdf_path):
    """
    Valida que el PDF cumpla con los límites establecidos.
    
    Args:
        pdf_path: Ruta al archivo PDF
        
    Returns:
        tuple: (num_pages, size_mb)
        
    Raises:
        FileNotFoundError: Si el PDF no existe
        ValueError: Si excede los límites máximos
    """
    # Verificar que existe
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"❌ No se encontró el PDF: {pdf_path}")
    
    # Verificar tamaño del archivo
    size_bytes = os.path.getsize(pdf_path)
    size_mb = size_bytes / (1024 * 1024)
    
    print(f"\n📊 Validando PDF...")
    print(f"  📦 Tamaño: {size_mb:.2f} MB")
    
    if size_mb > MAX_FILE_SIZE_MB:
        raise ValueError(
            f"❌ Archivo demasiado grande: {size_mb:.1f}MB\n"
            f"   Máximo permitido: {MAX_FILE_SIZE_MB}MB\n"
            f"   Considera dividir el PDF o aumentar MAX_FILE_SIZE_MB en config.py"
        )
    
    # Verificar número de páginas
    try:
        doc = fitz.open(pdf_path)
        num_pages = len(doc)
        doc.close()
    except Exception as e:
        raise ValueError(f"❌ Error al leer PDF: {e}")
    
    print(f"  📄 Páginas: {num_pages}")
    
    if num_pages > MAX_PAGES:
        raise ValueError(
            f"❌ Demasiadas páginas: {num_pages}\n"
            f"   Máximo permitido: {MAX_PAGES} páginas\n"
            f"   Considera dividir el PDF o aumentar MAX_PAGES en config.py"
        )
    
    # Advertencias (no bloquean, solo informan)
    if size_mb > WARN_FILE_SIZE_MB:
        print(f"  ⚠️  ADVERTENCIA: Archivo grande ({size_mb:.1f}MB)")
        print(f"     El procesamiento puede tardar varios minutos")
    
    if num_pages > WARN_PAGES:
        estimated_time_cpu = num_pages * 1.5  # ~1.5 seg por página en CPU
        estimated_min = estimated_time_cpu / 60
        print(f"  ⚠️  ADVERTENCIA: {num_pages} páginas")
        print(f"     Tiempo estimado (CPU): ~{estimated_min:.1f} minutos")
        print(f"     Considera usar GPU para acelerar el proceso")
    
    print(f"  ✅ Validación exitosa")
    
    return num_pages, size_mb


def get_pdf_info(pdf_path):
    """
    Obtiene información básica del PDF sin validar límites.
    
    Args:
        pdf_path: Ruta al archivo PDF
        
    Returns:
        dict: Información del PDF
    """
    if not os.path.exists(pdf_path):
        return None
    
    size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    
    try:
        doc = fitz.open(pdf_path)
        info = {
            'num_pages': len(doc),
            'size_mb': size_mb,
            'metadata': doc.metadata,
            'is_encrypted': doc.is_encrypted,
        }
        doc.close()
        return info
    except:
        return None
