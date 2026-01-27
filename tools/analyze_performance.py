"""
Analizador de perfiles de rendimiento históricos.
Lee todos los archivos de perfil y genera estadísticas comparativas.
"""
import json
import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def load_profiles(profile_dir="output_ocr/profiles"):
    """Carga todos los perfiles de rendimiento."""
    profiles = []
    
    if not os.path.exists(profile_dir):
        print(f"❌ No se encontró el directorio: {profile_dir}")
        return profiles
    
    for filename in os.listdir(profile_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(profile_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    profile = json.load(f)
                    profiles.append(profile)
            except Exception as e:
                print(f"⚠️ Error leyendo {filename}: {e}")
    
    return profiles


def analyze_by_pdf_type(profiles):
    """Analiza rendimiento agrupado por tipo de PDF."""
    by_type = defaultdict(list)
    
    for profile in profiles:
        pdf_type = profile.get('pdf', {}).get('type', 'unknown')
        by_type[pdf_type].append(profile)
    
    print("\n" + "="*60)
    print("📊 RENDIMIENTO POR TIPO DE PDF")
    print("="*60)
    
    for pdf_type, type_profiles in by_type.items():
        if not type_profiles:
            continue
        
        times = [p['total_time_seconds'] for p in type_profiles]
        pages = [p['pdf']['num_pages'] for p in type_profiles]
        speeds = [p['pdf'].get('pages_per_second', 0) for p in type_profiles]
        
        avg_time = sum(times) / len(times)
        avg_pages = sum(pages) / len(pages)
        avg_speed = sum(speeds) / len(speeds)
        
        print(f"\n📄 {pdf_type.upper()}")
        print(f"  Documentos procesados: {len(type_profiles)}")
        print(f"  Tiempo promedio: {avg_time:.2f}s")
        print(f"  Páginas promedio: {avg_pages:.1f}")
        print(f"  Velocidad promedio: {avg_speed:.2f} pág/seg")


def analyze_by_hardware(profiles):
    """Analiza rendimiento agrupado por hardware."""
    by_hw = defaultdict(list)
    
    for profile in profiles:
        hw = profile.get('hardware', {})
        cpu = hw.get('processor', 'unknown')
        gpu = 'GPU' if hw.get('gpu_available') else 'CPU'
        
        key = f"{gpu}"
        by_hw[key].append(profile)
    
    print("\n" + "="*60)
    print("💻 RENDIMIENTO POR HARDWARE")
    print("="*60)
    
    for hw_key, hw_profiles in by_hw.items():
        if not hw_profiles:
            continue
        
        times = [p['total_time_seconds'] for p in hw_profiles]
        speeds = [p['pdf'].get('pages_per_second', 0) for p in hw_profiles]
        
        avg_time = sum(times) / len(times)
        avg_speed = sum(speeds) / len(speeds)
        
        print(f"\n⚙️  {hw_key}")
        print(f"  Ejecuciones: {len(hw_profiles)}")
        print(f"  Tiempo promedio: {avg_time:.2f}s")
        print(f"  Velocidad promedio: {avg_speed:.2f} pág/seg")


def analyze_stages(profiles):
    """Analiza qué etapas consumen más tiempo."""
    stage_times = defaultdict(list)
    
    for profile in profiles:
        for stage in profile.get('stages', []):
            stage_times[stage['name']].append(stage['duration'])
    
    print("\n" + "="*60)
    print("⏱️  TIEMPO PROMEDIO POR ETAPA")
    print("="*60)
    
    for stage_name, times in sorted(stage_times.items()):
        avg = sum(times) / len(times)
        total = sum(times)
        print(f"  {stage_name}: {avg:.2f}s promedio ({total:.1f}s total en {len(times)} ejecuciones)")


def compare_first_vs_last(profiles):
    """Compara el rendimiento de la primera vs última ejecución."""
    if len(profiles) < 2:
        return
    
    # Ordenar por timestamp
    sorted_profiles = sorted(profiles, key=lambda p: p['timestamp'])
    
    first = sorted_profiles[0]
    last = sorted_profiles[-1]
    
    print("\n" + "="*60)
    print("🔄 COMPARACIÓN: Primera vs Última Ejecución")
    print("="*60)
    
    print(f"\n📅 Primera ejecución: {first['timestamp'][:10]}")
    print(f"  Tiempo: {first['total_time_seconds']:.2f}s")
    print(f"  Velocidad: {first['pdf'].get('pages_per_second', 0):.2f} pág/seg")
    
    print(f"\n📅 Última ejecución: {last['timestamp'][:10]}")
    print(f"  Tiempo: {last['total_time_seconds']:.2f}s")
    print(f"  Velocidad: {last['pdf'].get('pages_per_second', 0):.2f} pág/seg")
    
    # Mejora
    time_diff = ((last['total_time_seconds'] - first['total_time_seconds']) / first['total_time_seconds']) * 100
    if time_diff < 0:
        print(f"\n✅ Mejora de rendimiento: {abs(time_diff):.1f}% más rápido")
    else:
        print(f"\n⚠️ Degradación: {time_diff:.1f}% más lento")


def main():
    """Función principal."""
    print("="*60)
    print("📈 ANÁLISIS DE PERFILES DE RENDIMIENTO")
    print("="*60)
    
    profiles = load_profiles()
    
    if not profiles:
        print("\n❌ No se encontraron perfiles para analizar")
        print("💡 Ejecuta el procesamiento OCR con ENABLE_PROFILING=True")
        return
    
    print(f"\n✅ {len(profiles)} perfiles cargados")
    
    analyze_by_pdf_type(profiles)
    analyze_by_hardware(profiles)
    analyze_stages(profiles)
    compare_first_vs_last(profiles)
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()
