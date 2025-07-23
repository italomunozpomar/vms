# config/settings.py
"""
Configuración centralizada del VMS
Todas las constantes y configuraciones del sistema en un solo lugar
"""
import os
from pathlib import Path

# ============================================================================
# INFORMACIÓN DEL SISTEMA
# ============================================================================
APP_NAME = "VMS - Video Management System"
APP_VERSION = "1.2.0"
APP_AUTHOR = "ITalo Muñoz Pomar"
APP_DESCRIPTION = "Sistema profesional de gestión de video con IA"

# ============================================================================
# CONFIGURACIÓN DE CÁMARAS
# ============================================================================
CAMERA_CONFIG = {
    "ip_address": "192.168.67.63",
    "username": "admin",
    "password": "nunoa2018",
    "channels": {
        "high_res": ['101', '501', '601', '901'],  # Canales alta resolución
        "low_res": ['102', '502', '602', '902'],   # Canales baja resolución
    },
    "rtsp_template": "rtsp://{username}:{password}@{ip}:554/Streaming/Channels/{}?tcp/"
}

# ============================================================================
# RUTAS Y DIRECTORIOS
# ============================================================================
# Rutas del proyecto
PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
LOGS_DIR = PROJECT_ROOT / "logs"
CONFIG_DIR = PROJECT_ROOT / "config"

# Ruta de salida (puede ser externa)
OUTPUT_DIR = Path("D:/output")
RECORDINGS_DIR = OUTPUT_DIR / "recordings"
SNAPSHOTS_DIR = OUTPUT_DIR / "snapshots"
EVENTS_DIR = OUTPUT_DIR / "events"
ANALYTICS_DIR = OUTPUT_DIR / "analytics"

# ============================================================================
# CONFIGURACIÓN DE RENDIMIENTO
# ============================================================================
PERFORMANCE = {
    # Video
    "max_fps": 30,
    "frame_width": 1920,
    "frame_height": 1080,
    "buffer_size": 15,
    "compression_quality": 85,
    
    # GPU
    "gpu_memory_fraction": 0.8,
    "enable_gpu_preprocessing": True,
    
    # Analíticas (frame skip)
    "yolo_frame_skip": 3,
    "hands_frame_skip": 5,
    "face_frame_skip": 8,
    
    # Colas y buffers
    "max_queue_size": 6,
    "io_queue_size": 15,
    
    # Reconexión
    "reconnect_attempts": 5,
    "reconnect_delay": 2,
}

# ============================================================================
# CONFIGURACIÓN DE EVENTOS
# ============================================================================
EVENTS = {
    "cooldown_seconds": 5,
    "max_record_seconds": 10,
    "post_event_record_seconds": 10,
    "event_fps": 25,
    
    # Tipos de eventos
    "motion_events": ["motion", "VMD"],
    "security_events": ["linecrossing", "linedetection", "intrusion", "loitering"],
    "analytics_events": ["face_detection", "hands_up", "person_detection"],
}

# ============================================================================
# CONFIGURACIÓN DE UI
# ============================================================================
UI_CONFIG = {
    "theme": "dark",
    "min_window_size": (1280, 720),
    "grid_spacing": 4,
    "button_height": 40,
    "button_min_width": 150,
    
    # Colores
    "colors": {
        "primary": "#007bff",
        "success": "#28a745", 
        "warning": "#ffc107",
        "danger": "#dc3545",
        "dark": "#121212",
        "light": "#ffffff",
        "accent": "#00bfff",
    },
    
    # Estados de cámara
    "camera_states": {
        "normal": "#232323",
        "selected": "#00bfff", 
        "hover": "#282828",
        "motion": "#ff6600",
        "linecrossing": "#ff0000",
        "intrusion": "#00bfff",
    }
}

# ============================================================================
# CONFIGURACIÓN DE LOGGING
# ============================================================================
LOGGING = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": "vms.log",
    "max_size": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5,
}

# ============================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================================================
DATABASE = {
    "sqlite": {
        "path": CONFIG_DIR / "vms_events.db",
    },
    # Para futuras expansiones
    "azure_sql": {
        "driver": "{ODBC Driver 18 for SQL Server}",
        "server": "datosestructurados.database.windows.net,1433",
        "database": "DatosEstructurados",
        "username": "DBuser@DatosEstructurados",
        "password": "Contrasena123",
    }
}

# ============================================================================
# MODELOS DE IA
# ============================================================================
AI_MODELS = {
    "yolo": {
        "model_path": PROJECT_ROOT / "yolov8n.pt",
        "confidence": 0.5,
        "device": "cuda:0",
        "classes": [0],  # Solo personas
    },
    
    "face_detection": {
        "prototxt": PROJECT_ROOT / "core" / "deploy.prototxt",
        "model": PROJECT_ROOT / "core" / "res10_300x300_ssd_iter_140000.caffemodel",
        "confidence": 0.5,
        "device": "cpu",  # OpenCV DNN
    },
    
    "mediapipe": {
        "model_complexity": 1,
        "min_detection_confidence": 0.5,
        "min_tracking_confidence": 0.5,
    }
}

# ============================================================================
# FUNCIONES UTILITARIAS
# ============================================================================
def ensure_directories():
    """Crea todos los directorios necesarios"""
    directories = [
        OUTPUT_DIR, RECORDINGS_DIR, SNAPSHOTS_DIR, 
        EVENTS_DIR, ANALYTICS_DIR, LOGS_DIR, MODELS_DIR
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        
def get_camera_url(channel: str) -> str:
    """Genera URL RTSP para un canal específico"""
    return CAMERA_CONFIG["rtsp_template"].format(
        username=CAMERA_CONFIG["username"],
        password=CAMERA_CONFIG["password"],
        ip=CAMERA_CONFIG["ip_address"]
    ).format(channel)

def get_version_string() -> str:
    """Retorna string de versión completo"""
    return f"{APP_NAME} v{APP_VERSION}"

if __name__ == "__main__":
    # Crear directorios al importar
    ensure_directories()
    print(f"✅ Configuración cargada: {get_version_string()}")
