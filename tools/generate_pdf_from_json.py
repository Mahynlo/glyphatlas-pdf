"""
Script standalone para generar PDF seleccionable desde JSON existente.
Útil para iterar en el cálculo de fontsize sin ejecutar OCR cada vez.

Uso:
    python generate_pdf_from_json.py
"""

import sys
import os

# Agregar el directorio actual al path para importar módulos
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.pdf.generator import create_searchable_pdf
from config import PDF_PATH, JSON_OUTPUT, OUT_DIR

def main():
    """Genera PDF seleccionable desde JSON existente."""
    
    # Verificar que existe el JSON de resultados
    if not os.path.exists(JSON_OUTPUT):
        print(f"❌ Error: No se encontró el archivo JSON: {JSON_OUTPUT}")
        print(f"   Primero ejecuta 'python main_refactored.py' para generar el JSON con OCR")
        return 1
    
    # Verificar que existe el PDF original
    if not os.path.exists(PDF_PATH):
        print(f"❌ Error: No se encontró el PDF original: {PDF_PATH}")
        return 1
    
    # Archivo de salida
    output_pdf = f"{OUT_DIR}/documento_seleccionable.pdf"
    
    print("=" * 60)
    print("🔄 GENERADOR DE PDF SELECCIONABLE (desde JSON existente)")
    print("=" * 60)
    print(f"\n📄 PDF original: {PDF_PATH}")
    print(f"📋 JSON resultados: {JSON_OUTPUT}")
    print(f"💾 PDF salida: {output_pdf}")
    print()
    
    # Generar PDF seleccionable
    success = create_searchable_pdf(PDF_PATH, JSON_OUTPUT, output_pdf)
    
    if success:
        print()
        print("=" * 60)
        print("✅ PDF SELECCIONABLE GENERADO EXITOSAMENTE")
        print("=" * 60)
        print(f"\n📄 Archivo: {output_pdf}")
        print("\nAhora puedes:")
        print("  1. Abrir el PDF y verificar el tamaño del texto")
        print("  2. Ajustar el algoritmo en src/pdf/generator.py")
        print("  3. Ejecutar este script de nuevo (sin esperar OCR)")
        return 0
    else:
        print()
        print("=" * 60)
        print("❌ ERROR AL GENERAR PDF")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
