"""
Sistema de profiling y medición de rendimiento.
"""
import time
import json
import os
import platform
from datetime import datetime
from pathlib import Path


class PerformanceProfiler:
    """
    Registra y analiza el rendimiento del procesamiento OCR.
    """
    
    def __init__(self, enabled=True):
        self.enabled = enabled
        self.start_time = None
        self.timings = {}
        self.stages = []
        self.current_stage = None
        self.hardware_info = self._get_hardware_info()
        self.pdf_info = {}
        
    def start(self):
        """Inicia el profiling."""
        if not self.enabled:
            return
        self.start_time = time.perf_counter()
        
    def stage_start(self, stage_name):
        """Inicia medición de una etapa."""
        if not self.enabled:
            return
        
        self.current_stage = {
            'name': stage_name,
            'start': time.perf_counter(),
            'end': None,
            'duration': None
        }
        
    def stage_end(self, stage_name=None):
        """Finaliza medición de una etapa."""
        if not self.enabled or not self.current_stage:
            return
        
        end_time = time.perf_counter()
        self.current_stage['end'] = end_time
        self.current_stage['duration'] = end_time - self.current_stage['start']
        
        self.stages.append(self.current_stage.copy())
        self.timings[self.current_stage['name']] = self.current_stage['duration']
        self.current_stage = None
        
    def set_pdf_info(self, pdf_type, num_pages, file_size_mb):
        """Registra información del PDF procesado."""
        if not self.enabled:
            return
        
        self.pdf_info = {
            'type': pdf_type,
            'num_pages': num_pages,
            'file_size_mb': round(file_size_mb, 2),
            'pages_per_second': 0,  # Se calculará al final
            'mb_per_second': 0
        }
        
    def get_total_time(self):
        """Obtiene el tiempo total transcurrido."""
        if not self.enabled or not self.start_time:
            return 0
        return time.perf_counter() - self.start_time
        
    def get_summary(self):
        """Genera resumen de rendimiento."""
        if not self.enabled:
            return {}
        
        total_time = self.get_total_time()
        
        # Calcular métricas
        if self.pdf_info.get('num_pages', 0) > 0:
            self.pdf_info['pages_per_second'] = round(
                self.pdf_info['num_pages'] / total_time, 2
            ) if total_time > 0 else 0
            
        if self.pdf_info.get('file_size_mb', 0) > 0:
            self.pdf_info['mb_per_second'] = round(
                self.pdf_info['file_size_mb'] / total_time, 2
            ) if total_time > 0 else 0
        
        summary = {
            'timestamp': datetime.now().isoformat(),
            'total_time_seconds': round(total_time, 3),
            'hardware': self.hardware_info,
            'pdf': self.pdf_info,
            'stages': self.stages,
            'timings': {k: round(v, 3) for k, v in self.timings.items()}
        }
        
        return summary
        
    def save_profile(self, output_dir):
        """Guarda el perfil de rendimiento en JSON."""
        if not self.enabled:
            return None
        
        os.makedirs(output_dir, exist_ok=True)
        
        summary = self.get_summary()
        
        # Nombre de archivo con timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"profile_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        return filepath
        
    def print_summary(self):
        """Imprime resumen de rendimiento en consola."""
        if not self.enabled:
            return
        
        summary = self.get_summary()
        
        print("\n" + "="*60)
        print("📊 RESUMEN DE RENDIMIENTO")
        print("="*60)
        
        # Hardware
        hw = summary['hardware']
        print(f"\n💻 Hardware:")
        print(f"  Sistema: {hw['system']} {hw['release']}")
        print(f"  Procesador: {hw['processor']}")
        print(f"  CPU: {hw['cpu_count']} núcleos")
        if hw.get('gpu_available'):
            print(f"  GPU: {hw.get('gpu_name', 'Disponible')}")
        
        # PDF
        pdf = summary['pdf']
        print(f"\n📄 PDF Procesado:")
        print(f"  Tipo: {pdf['type']}")
        print(f"  Páginas: {pdf['num_pages']}")
        print(f"  Tamaño: {pdf['file_size_mb']} MB")
        
        # Rendimiento
        total = summary['total_time_seconds']
        print(f"\n⏱️  Rendimiento:")
        print(f"  Tiempo total: {total:.2f} segundos ({total/60:.2f} min)")
        print(f"  Velocidad: {pdf.get('pages_per_second', 0):.2f} páginas/seg")
        print(f"  Throughput: {pdf.get('mb_per_second', 0):.2f} MB/seg")
        
        # Desglose por etapas
        if summary['stages']:
            print(f"\n📈 Desglose por Etapas:")
            for stage in summary['stages']:
                duration = stage['duration']
                percentage = (duration / total * 100) if total > 0 else 0
                print(f"  {stage['name']}: {duration:.2f}s ({percentage:.1f}%)")
        
        print("="*60)
        
    def _get_hardware_info(self):
        """Obtiene información del hardware."""
        info = {
            'system': platform.system(),
            'release': platform.release(),
            'machine': platform.machine(),
            'processor': platform.processor(),
            'cpu_count': os.cpu_count(),
            'gpu_available': False,
            'gpu_name': None
        }
        
        # Detectar GPU NVIDIA
        try:
            import subprocess
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader'],
                capture_output=True,
                text=True,
                timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                info['gpu_available'] = True
                info['gpu_name'] = result.stdout.strip().split('\n')[0]
        except:
            pass
        
        return info


# Instancia global del profiler
_profiler = None


def get_profiler(enabled=True):
    """Obtiene o crea la instancia global del profiler."""
    global _profiler
    if _profiler is None:
        _profiler = PerformanceProfiler(enabled=enabled)
    return _profiler


def reset_profiler():
    """Reinicia el profiler global."""
    global _profiler
    _profiler = None
