"""
Analizador de perfiles de rendimiento históricos - MEJORADO
Características:
- Gráficos ASCII
- Análisis de tendencias
- Detección de cuellos de botella
- Recomendaciones automáticas
- Exportación HTML
"""
import json
import os
from pathlib import Path
from collections import defaultdict
from datetime import datetime
import statistics


# ===============================
# UTILIDADES DE VISUALIZACIÓN
# ===============================
def create_bar_chart(values, labels, max_width=40, show_values=True):
    """Crea un gráfico de barras ASCII."""
    if not values:
        return ""
    
    max_val = max(values)
    if max_val == 0:
        return ""
    
    lines = []
    for label, value in zip(labels, values):
        bar_len = int((value / max_val) * max_width)
        bar = "█" * bar_len
        value_str = f" {value:.2f}" if show_values else ""
        lines.append(f"  {label:20} {bar}{value_str}")
    
    return "\n".join(lines)


def create_trend_line(values, width=50):
    """Crea una línea de tendencia ASCII."""
    if len(values) < 2:
        return "Insuficientes datos"
    
    min_val = min(values)
    max_val = max(values)
    range_val = max_val - min_val
    
    if range_val == 0:
        return "▬" * width
    
    # Normalizar valores
    normalized = [(v - min_val) / range_val for v in values]
    
    # Crear línea
    chars = " ▁▂▃▄▅▆▇█"
    line = ''.join(chars[int(n * (len(chars) - 1))] for n in normalized)
    
    # Trend direction
    slope = (values[-1] - values[0]) / len(values)
    trend = "📈" if slope > 0 else "📉" if slope < 0 else "➡️"
    
    return f"{trend} {line}"


def format_duration(seconds):
    """Formatea duración en formato legible."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = seconds % 60
        return f"{mins}m {secs:.0f}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


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
    
    print("\n" + "="*70)
    print("📊 RENDIMIENTO POR TIPO DE PDF")
    print("="*70)
    
    for pdf_type, type_profiles in by_type.items():
        if not type_profiles:
            continue
        
        times = [p['total_time_seconds'] for p in type_profiles]
        pages = [p['pdf']['num_pages'] for p in type_profiles]
        speeds = [p['pdf'].get('pages_per_second', 0) for p in type_profiles]
        
        avg_time = statistics.mean(times)
        median_time = statistics.median(times)
        std_time = statistics.stdev(times) if len(times) > 1 else 0
        avg_pages = statistics.mean(pages)
        avg_speed = statistics.mean(speeds)
        
        print(f"\n📄 {pdf_type.upper()}")
        print(f"  Documentos procesados: {len(type_profiles)}")
        print(f"  Tiempo promedio: {avg_time:.2f}s (±{std_time:.2f}s)")
        print(f"  Tiempo mediano: {median_time:.2f}s")
        print(f"  Páginas promedio: {avg_pages:.1f}")
        print(f"  Velocidad promedio: {avg_speed:.2f} pág/seg")
        print(f"  Rango: {min(times):.2f}s - {max(times):.2f}s")
        
        # Tendencia si hay suficientes datos
        if len(times) >= 3:
            print(f"\n  Tendencia temporal:")
            print(f"  {create_trend_line(times)}")


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
    """Analiza qué etapas consumen más tiempo con gráficos."""
    stage_times = defaultdict(list)
    
    for profile in profiles:
        for stage in profile.get('stages', []):
            stage_times[stage['name']].append(stage['duration'])
    
    print("\n" + "="*70)
    print("⏱️  TIEMPO PROMEDIO POR ETAPA")
    print("="*70)
    
    # Calcular promedios y ordenar
    stage_avgs = {name: statistics.mean(times) for name, times in stage_times.items()}
    sorted_stages = sorted(stage_avgs.items(), key=lambda x: x[1], reverse=True)
    
    # Mostrar gráfico de barras
    labels = [name[:18] for name, _ in sorted_stages]
    values = [avg for _, avg in sorted_stages]
    
    print("\n" + create_bar_chart(values, labels, max_width=40))
    
    # Detalles por etapa
    print(f"\n📊 Detalles:")
    total_avg = sum(values)
    
    for name, avg in sorted_stages:
        times = stage_times[name]
        percentage = (avg / total_avg) * 100 if total_avg > 0 else 0
        std = statistics.stdev(times) if len(times) > 1 else 0
        
        print(f"  {name:25} {avg:6.2f}s ({percentage:5.1f}%) ±{std:.2f}s | {len(times)} ejecuciones")
    
    # Identificar cuellos de botella
    print(f"\n🔍 Análisis de cuellos de botella:")
    if sorted_stages:
        slowest_name, slowest_time = sorted_stages[0]
        print(f"  ⚠️  Etapa más lenta: '{slowest_name}' ({slowest_time:.2f}s)")
        
        if slowest_time / total_avg > 0.5:
            print(f"  🚨 ¡CUELLO DE BOTELLA! Representa {(slowest_time/total_avg)*100:.1f}% del tiempo total")
        
        # Sugerencias
        if 'OCR' in slowest_name.upper():
            print(f"  💡 Sugerencia: Considera reducir DPI o usar modelos más rápidos")
        elif 'PDF' in slowest_name.upper() and 'GENERAR' in slowest_name.upper():
            print(f"  💡 Sugerencia: La generación de PDFs es costosa, considera cachear resultados")


def compare_first_vs_last(profiles):
    """Compara el rendimiento de la primera vs última ejecución."""
    if len(profiles) < 2:
        return
    
    # Ordenar por timestamp
    sorted_profiles = sorted(profiles, key=lambda p: p['timestamp'])
    
    first = sorted_profiles[0]
    last = sorted_profiles[-1]
    
    print("\n" + "="*70)
    print("🔄 COMPARACIÓN: Primera vs Última Ejecución")
    print("="*70)
    
    print(f"\n📅 Primera ejecución: {first['timestamp'][:19]}")
    print(f"  Tiempo: {first['total_time_seconds']:.2f}s")
    print(f"  Velocidad: {first['pdf'].get('pages_per_second', 0):.2f} pág/seg")
    
    print(f"\n📅 Última ejecución: {last['timestamp'][:19]}")
    print(f"  Tiempo: {last['total_time_seconds']:.2f}s")
    print(f"  Velocidad: {last['pdf'].get('pages_per_second', 0):.2f} pág/seg")
    
    # Mejora
    time_diff = ((last['total_time_seconds'] - first['total_time_seconds']) / first['total_time_seconds']) * 100
    speed_diff = ((last['pdf'].get('pages_per_second', 0) - first['pdf'].get('pages_per_second', 0)) / first['pdf'].get('pages_per_second', 1)) * 100
    
    print(f"\n📈 Cambios:")
    if time_diff < 0:
        print(f"  ✅ Tiempo: {abs(time_diff):.1f}% más rápido")
    elif time_diff > 0:
        print(f"  ⚠️ Tiempo: {time_diff:.1f}% más lento")
    else:
        print(f"  ➡️ Tiempo: Sin cambios")
    
    if speed_diff > 0:
        print(f"  ✅ Velocidad: {speed_diff:.1f}% más rápido")
    elif speed_diff < 0:
        print(f"  ⚠️ Velocidad: {abs(speed_diff):.1f}% más lento")


def analyze_performance_trends(profiles):
    """Analiza tendencias de rendimiento a lo largo del tiempo."""
    if len(profiles) < 3:
        print("\n⚠️ Se necesitan al menos 3 perfiles para análisis de tendencias")
        return
    
    # Ordenar por timestamp
    sorted_profiles = sorted(profiles, key=lambda p: p['timestamp'])
    
    times = [p['total_time_seconds'] for p in sorted_profiles]
    speeds = [p['pdf'].get('pages_per_second', 0) for p in sorted_profiles]
    
    print("\n" + "="*70)
    print("📈 ANÁLISIS DE TENDENCIAS")
    print("="*70)
    
    print(f"\n⏱️  Tiempo de procesamiento (últimas {len(times)} ejecuciones):")
    print(create_trend_line(times, width=60))
    print(f"  Promedio: {statistics.mean(times):.2f}s | Mejor: {min(times):.2f}s | Peor: {max(times):.2f}s")
    
    print(f"\n🚀 Velocidad (páginas/segundo):")
    print(create_trend_line(speeds, width=60))
    print(f"  Promedio: {statistics.mean(speeds):.2f} pág/s | Mejor: {max(speeds):.2f} | Peor: {min(speeds):.2f}")
    
    # Calcular tendencia lineal simple
    n = len(times)
    x_mean = (n - 1) / 2
    y_mean = statistics.mean(times)
    
    slope = sum((i - x_mean) * (t - y_mean) for i, t in enumerate(times)) / sum((i - x_mean) ** 2 for i in range(n))
    
    print(f"\n📊 Tendencia lineal:")
    if abs(slope) < 0.01:
        print(f"  ➡️ Estable (cambio: {slope:.4f}s por ejecución)")
    elif slope < 0:
        print(f"  ✅ Mejorando ({abs(slope):.4f}s más rápido por ejecución)")
    else:
        print(f"  ⚠️ Degradando ({slope:.4f}s más lento por ejecución)")


def generate_recommendations(profiles):
    """Genera recomendaciones automáticas basadas en el análisis."""
    if not profiles:
        return
    
    print("\n" + "="*70)
    print("💡 RECOMENDACIONES AUTOMÁTICAS")
    print("="*70)
    
    recommendations = []
    
    # Analizar velocidad promedio
    avg_speed = statistics.mean([p['pdf'].get('pages_per_second', 0) for p in profiles])
    
    if avg_speed < 0.3:
        recommendations.append({
            'priority': '🔴 ALTA',
            'title': 'Velocidad muy baja detectada',
            'details': f'Velocidad promedio: {avg_speed:.2f} pág/s (objetivo: >0.4 pág/s)',
            'actions': [
                'Reducir RENDER_DPI en config.py (300 → 200)',
                'Usar modelos más pequeños (si disponible)',
                'Verificar si GPU está siendo utilizada'
            ]
        })
    
    # Analizar variabilidad
    times = [p['total_time_seconds'] for p in profiles]
    if len(times) > 1:
        std_dev = statistics.stdev(times)
        cv = std_dev / statistics.mean(times)  # Coeficiente de variación
        
        if cv > 0.3:
            recommendations.append({
                'priority': '🟡 MEDIA',
                'title': 'Alta variabilidad en tiempos de ejecución',
                'details': f'Desviación estándar: ±{std_dev:.2f}s (CV: {cv*100:.1f}%)',
                'actions': [
                    'Cerrar aplicaciones en segundo plano durante las pruebas',
                    'Procesar documentos de tamaño similar para comparar',
                    'Verificar temperatura del CPU (throttling?)'
                ]
            })
    
    # Analizar etapas
    stage_times = defaultdict(list)
    for profile in profiles:
        for stage in profile.get('stages', []):
            stage_times[stage['name']].append(stage['duration'])
    
    if stage_times:
        stage_avgs = {name: statistics.mean(times) for name, times in stage_times.items()}
        total_avg = sum(stage_avgs.values())
        slowest = max(stage_avgs.items(), key=lambda x: x[1])
        
        if slowest[1] / total_avg > 0.6:
            recommendations.append({
                'priority': '🔴 ALTA',
                'title': f'Cuello de botella detectado: {slowest[0]}',
                'details': f'Representa {(slowest[1]/total_avg)*100:.1f}% del tiempo total',
                'actions': [
                    f'Optimizar específicamente la etapa: {slowest[0]}',
                    'Considerar procesamiento paralelo si es posible',
                    'Revisar configuración de esta etapa'
                ]
            })
    
    # Analizar uso de hardware
    gpu_count = sum(1 for p in profiles if p.get('hardware', {}).get('gpu_available'))
    if gpu_count == 0 and len(profiles) > 0:
        recommendations.append({
            'priority': '🟢 BAJA',
            'title': 'GPU no detectada/utilizada',
            'details': 'Todas las ejecuciones usan CPU',
            'actions': [
                'Verificar si tienes GPU disponible',
                'Instalar drivers GPU si corresponde',
                'Considerar usar servicios en la nube con GPU para producción'
            ]
        })
    
    # Mostrar recomendaciones
    if not recommendations:
        print("\n  ✅ No se detectaron problemas significativos")
        print("  ✨ El rendimiento está dentro de los parámetros esperados")
    else:
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['priority']} {rec['title']}")
            print(f"   📝 {rec['details']}")
            print(f"   🔧 Acciones sugeridas:")
            for action in rec['actions']:
                print(f"      • {action}")


def export_to_html(profiles, output_path="output_ocr/performance_report.html"):
    """Exporta un reporte HTML interactivo."""
    if not profiles:
        return
    
    # Calcular estadísticas
    times = [p['total_time_seconds'] for p in profiles]
    speeds = [p['pdf'].get('pages_per_second', 0) for p in profiles]
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Reporte de Rendimiento OCR</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .stat-box {{ background: #ecf0f1; padding: 15px; border-radius: 5px; border-left: 4px solid #3498db; }}
        .stat-label {{ font-size: 12px; color: #7f8c8d; text-transform: uppercase; }}
        .stat-value {{ font-size: 24px; font-weight: bold; color: #2c3e50; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #34495e; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        .good {{ color: #27ae60; }}
        .warning {{ color: #f39c12; }}
        .bad {{ color: #e74c3c; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Reporte de Rendimiento OCR</h1>
        <p>Generado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>📈 Resumen General</h2>
        <div class="stats">
            <div class="stat-box">
                <div class="stat-label">Total Ejecuciones</div>
                <div class="stat-value">{len(profiles)}</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Tiempo Promedio</div>
                <div class="stat-value">{statistics.mean(times):.2f}s</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Velocidad Promedio</div>
                <div class="stat-value">{statistics.mean(speeds):.2f} pág/s</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Mejor Tiempo</div>
                <div class="stat-value class="good">{min(times):.2f}s</div>
            </div>
        </div>
        
        <h2>📋 Histórico de Ejecuciones</h2>
        <table>
            <tr>
                <th>Fecha</th>
                <th>Tipo PDF</th>
                <th>Páginas</th>
                <th>Tiempo</th>
                <th>Velocidad</th>
                <th>Hardware</th>
            </tr>
"""
    
    sorted_profiles = sorted(profiles, key=lambda p: p['timestamp'], reverse=True)
    
    for p in sorted_profiles[:20]:  # Últimas 20
        pdf_type = p.get('pdf', {}).get('type', 'unknown')
        num_pages = p.get('pdf', {}).get('num_pages', 0)
        time_taken = p['total_time_seconds']
        speed = p.get('pdf', {}).get('pages_per_second', 0)
        gpu = '🎮 GPU' if p.get('hardware', {}).get('gpu_available') else '💻 CPU'
        
        time_class = 'good' if time_taken < statistics.mean(times) else 'warning'
        
        html += f"""
            <tr>
                <td>{p['timestamp'][:19]}</td>
                <td>{pdf_type}</td>
                <td>{num_pages}</td>
                <td class="{time_class}">{time_taken:.2f}s</td>
                <td>{speed:.2f} pág/s</td>
                <td>{gpu}</td>
            </tr>
"""
    
    html += """
        </table>
    </div>
</body>
</html>
"""
    
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n📄 Reporte HTML exportado: {output_path}")
    except Exception as e:
        print(f"\n⚠️ Error exportando HTML: {e}")


def main():
    """Función principal."""
    print("="*70)
    print("📈 ANÁLISIS AVANZADO DE PERFILES DE RENDIMIENTO")
    print("="*70)
    
    profiles = load_profiles()
    
    if not profiles:
        print("\n❌ No se encontraron perfiles para analizar")
        print("💡 Ejecuta el procesamiento OCR con ENABLE_PROFILING=True en config.py")
        return
    
    print(f"\n✅ {len(profiles)} perfiles cargados correctamente")
    
    # Análisis tradicionales mejorados
    analyze_by_pdf_type(profiles)
    analyze_by_hardware(profiles)
    analyze_stages(profiles)
    
    # Análisis nuevos
    analyze_performance_trends(profiles)
    compare_first_vs_last(profiles)
    generate_recommendations(profiles)
    
    # Exportar HTML
    export_to_html(profiles)
    
    print("\n" + "="*70)
    print("✅ Análisis completado")
    print("="*70)


if __name__ == "__main__":
    main()
