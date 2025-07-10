import torch
from ultralytics import YOLO

# Importar módulos de ultralytics necesarios para safe_globals
from ultralytics.nn.tasks import DetectionModel
import torch.nn.modules.container
import ultralytics.nn.modules  # Contiene Conv, C2f, Concat, SPPF, etc.
from torch.serialization import add_safe_globals

# Agregar todas las clases personalizadas necesarias para deserialización segura
add_safe_globals([
    DetectionModel,
    torch.nn.modules.container.Sequential,
    ultralytics.nn.modules.Conv,
    ultralytics.nn.modules.C2f,
    ultralytics.nn.modules.Concat,
    ultralytics.nn.modules.SPPF
])

# Optimización: Configurar dispositivo y cargar modelo con optimizaciones
def get_best_device():
    if torch.cuda.is_available():
        # Verificar si hay suficiente memoria GPU
        gpu_memory = torch.cuda.get_device_properties(0).total_memory / (1024**3)  # GB
        print(f"CUDA disponible: {torch.cuda.get_device_name(0)} ({gpu_memory:.1f}GB)")
        
        # Configurar optimizaciones CUDA
        torch.backends.cuda.matmul.allow_tf32 = True
        torch.backends.cudnn.allow_tf32 = True
        torch.backends.cudnn.benchmark = True
        
        return torch.device('cuda')
    elif torch.backends.mps.is_available():
        print("MPS disponible (Apple Silicon)")
        return torch.device('mps')
    else:
        print("Usando CPU")
        return torch.device('cpu')

device = get_best_device()
print(f"Usando dispositivo: {device}")

# Cargar modelo YOLO con optimizaciones
modelo_yolo = YOLO("yolov8n.pt")
modelo_yolo.to(device)

# Optimización: Configurar parámetros para mejor rendimiento
modelo_yolo.conf = 0.5  # Umbral de confianza
modelo_yolo.iou = 0.45  # Umbral de IoU para NMS
modelo_yolo.agnostic = False  # NMS agnóstico de clase
modelo_yolo.max_det = 20  # Máximo número de detecciones

# Optimización: Compilar modelo para mejor rendimiento (PyTorch 2.0+)
try:
    if hasattr(torch, 'compile') and device.type == 'cuda':
        modelo_yolo.model = torch.compile(modelo_yolo.model, mode='reduce-overhead')
        print("✓ Modelo YOLO compilado con torch.compile")
except Exception as e:
    print(f"⚠️ No se pudo compilar el modelo: {e}")

# Optimización: Calentar modelo con un frame dummy
try:
    dummy_frame = torch.zeros(1, 3, 640, 640, device=device)
    with torch.no_grad():
        _ = modelo_yolo.model(dummy_frame)
    print("✓ Modelo YOLO calentado")
except Exception as e:
    print(f"⚠️ No se pudo calentar el modelo: {e}")

print("Modelo YOLO cargado y optimizado")
