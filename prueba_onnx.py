import time
import os
import sys
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.patches as patches
from onnxtr.io import DocumentFile
from onnxtr.models import ocr_predictor

# ==========================================
# 1. CARGA Y CONFIGURACIÓN
# ==========================================
print("📂 Cargando documento y modelo...")

# Ruta de tu archivo local
pdf_path = "pdf_ejemplo/ejemplo_scan127.pdf"

# Validación rápida: Si el archivo no existe, avisamos
if not os.path.exists(pdf_path):
    print(f"❌ ERROR: No encuentro el archivo: {pdf_path}")
    print("   Asegúrate de crear la carpeta 'pdf_ejemplo' y poner el PDF dentro.")
    sys.exit()

# Cargar el PDF (Esto crea una lista de imágenes numpy arrays)
single_img_doc = DocumentFile.from_pdf(pdf_path)

# Configurar modelo
predictor = ocr_predictor(
    det_arch="db_mobilenet_v3_large", 
    reco_arch="crnn_mobilenet_v3_large",
    detect_language=False
)

# ==========================================
# 2. EJECUCIÓN CON MEDICIÓN DE TIEMPO
# ==========================================
print("⚡ Iniciando inferencia OCR...")

start_time = time.perf_counter()

# --- PROCESO PRINCIPAL ---
res = predictor(single_img_doc)
# -------------------------

end_time = time.perf_counter()
total_time = end_time - start_time

num_pages = len(single_img_doc)
print(f"\n⏱️ RESULTADOS DE TIEMPO:")
print(f"   - Páginas procesadas: {num_pages}")
print(f"   - Tiempo Total: {total_time:.4f} segundos")
print(f"   - Promedio por página: {total_time / num_pages:.4f} segundos")

# ==========================================
# 3. GENERAR PDF CON MARCADORES (Visualización)
# ==========================================
print("\n🎨 Generando PDF con cajas delimitadoras...")
output_pdf = "resultado_con_cajas.pdf"  # Guardar en la misma carpeta del script

try:
    with PdfPages(output_pdf) as pdf:
        # CORRECCIÓN IMPORTANTE:
        # Usamos zip() para unir la imagen original (page_img) con los datos del OCR (page_pred)
        # Esto evita el error de "dtype <U2220"
        for i, (page_img, page_pred) in enumerate(zip(single_img_doc, res.pages)):
            
            # Crear figura
            fig, ax = plt.subplots(figsize=(10, 10))
            
            # Mostrar la imagen ORIGINAL
            ax.imshow(page_img)
            
            # Obtener dimensiones reales de la imagen (Alto, Ancho)
            h, w = page_img.shape[:2]
            
            # Recorrer la jerarquía: Bloques -> Líneas -> Palabras
            for block in page_pred.blocks:
                for line in block.lines:
                    for word in line.words:
                        # Geometría relativa (0.0 a 1.0)
                        (xmin, ymin), (xmax, ymax) = word.geometry
                        
                        # Convertir a píxeles absolutos
                        rect_x = xmin * w
                        rect_y = ymin * h
                        rect_w = (xmax - xmin) * w
                        rect_h = (ymax - ymin) * h
                        
                        # Dibujar rectángulo rojo
                        rect = patches.Rectangle(
                            (rect_x, rect_y), rect_w, rect_h,
                            linewidth=1, edgecolor='r', facecolor='none'
                        )
                        ax.add_patch(rect)
            
            # Limpiar gráfica y guardar página
            plt.axis('off')
            plt.title(f"Página {i+1} - {w}x{h}px", fontsize=10)
            pdf.savefig(fig, bbox_inches='tight')
            plt.close(fig)
            
    print(f"✅ ¡Listo! PDF generado en: {os.path.abspath(output_pdf)}")

except Exception as e:
    print(f"❌ Error generando el PDF visual: {e}")
    # Esto imprime el error completo para saber qué pasó
    import traceback
    traceback.print_exc()



