import os
import numpy as np
from pathlib import Path

# Configuración de rendimiento
PERFORMANCE_CONFIG = {
    'max_fps': 25,
    'frame_width': 640,
    'frame_height': 480,
    'buffer_size': 1,
    'reconnect_attempts': 5,
    'reconnect_delay': 2,
    'yolo_frame_skip': 5,
    'hands_frame_skip': 3,
    'face_frame_skip': 10
}

# Cámaras originales (flujo principal)
canales_originales = ['101', '501', '601', '901']

# Canales secundarios (flujo baja resolución) correspondientes
canales_baja = {
    '101': '102',
    '501': '502',
    '601': '602',
    '901': '902'
}

# Validación de configuración de cámaras
def validate_camera_config():
    """Valida que la configuración de cámaras sea consistente"""
    for canal in canales_originales:
        if canal not in canales_baja:
            print(f"Advertencia: Canal {canal} no tiene canal secundario configurado")
    
    print(f"Configuración de {len(canales_originales)} cámaras validada")

# Canales activos, inicialmente igual a originales
canales_activos = {canal: canal for canal in canales_originales}

# Formato base RTSP (usa {} para insertar canal)
rtsp_base = "rtsp://admin:nunoa2018@192.168.67.63:554/Streaming/Channels/{}?tcp/"

# Frames en memoria para cada cámara (inicializados vacíos)
frames = {canal: np.zeros((480, 640, 3), dtype=np.uint8) for canal in canales_originales}

# Flags para controlar qué analíticas están activas por cámara
analitica_activa = {canal: False for canal in canales_originales}     # Detección personas (YOLO)
recording_flags = {canal: False for canal in canales_originales}      # Grabación ON/OFF
manos_arriba_activa = {canal: False for canal in canales_originales}  # Detección manos arriba
snapshot_flags = {canal: False for canal in canales_originales}       # Snapshot pedido
zona_interes_activa = {
    "602": False  # Zona de interés en canal secundario 602 (ejemplo)
}

rostros_activa = {canal: False for canal in canales_originales}       # Detección rostros ON/OFF

# Manejadores para video grabado
video_writers = {canal: None for canal in canales_originales}

# Variable global para detener hilos
detener = False

# Carpeta donde se guardan videos, snapshots y rostros detectados
output_folder = Path(r"C:\Users\MXL2442MK2\Desktop\vms\output")
output_folder.mkdir(parents=True, exist_ok=True)

# Crear subcarpetas para mejor organización
(output_folder / "captures").mkdir(exist_ok=True)
(output_folder / "rostros").mkdir(exist_ok=True)
(output_folder / "videos").mkdir(exist_ok=True)
(output_folder / "eventos").mkdir(exist_ok=True)

print(f"Carpeta de salida creada: {output_folder}")
print(f"Subcarpetas: captures, rostros, videos, eventos")

# Validar configuración al importar
validate_camera_config()
