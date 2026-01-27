"""
Módulo para operaciones de entrada/salida.
"""

import json
from config import JSON_OUTPUT


def save_results(results):
    """
    Guarda los resultados del OCR en formato JSON.
    
    Args:
        results: Diccionario con resultados estructurados
    """
    try:
        with open(JSON_OUTPUT, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Resultados guardados en: {JSON_OUTPUT}")
        
        # Estadísticas resumidas
        total_pages = len(results.get("pages", []))
        if "metadata" in results and "total_pages" in results["metadata"]:
            total_pages = results["metadata"]["total_pages"]
        
        pages_with_text = sum(1 for p in results.get("pages", []) if p.get("text_regions"))
        print(f"📊 Resumen: {pages_with_text}/{total_pages} páginas con texto detectado")
        
    except Exception as e:
        print(f"⚠️ Error guardando resultados: {e}")
        import traceback
        traceback.print_exc()
