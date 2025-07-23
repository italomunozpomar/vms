# core/constants.py
"""
Constantes del sistema VMS
Valores que no cambian durante la ejecución
"""

# ============================================================================
# VERSIÓN Y METADATA
# ============================================================================
VERSION = "1.2.0"
BUILD_DATE = "2025-07-23"
BUILD_NUMBER = "240723.1"

# ============================================================================
# CÓDIGOS DE ESTADO
# ============================================================================
class StatusCodes:
    """Códigos de estado del sistema"""
    SUCCESS = 0
    ERROR = 1
    WARNING = 2
    INFO = 3
    
    # Estados de cámara
    CAMERA_CONNECTED = 100
    CAMERA_DISCONNECTED = 101
    CAMERA_RECONNECTING = 102
    CAMERA_ERROR = 103
    
    # Estados de analíticas
    ANALYTICS_ACTIVE = 200
    ANALYTICS_INACTIVE = 201
    ANALYTICS_ERROR = 202
    
    # Estados de grabación
    RECORDING_STARTED = 300
    RECORDING_STOPPED = 301
    RECORDING_ERROR = 302

# ============================================================================
# TIPOS DE EVENTOS
# ============================================================================
class EventTypes:
    """Tipos de eventos del sistema"""
    # Eventos de movimiento
    MOTION = "motion"
    VMD = "VMD"
    
    # Eventos de seguridad
    LINE_CROSSING = "linecrossing"
    LINE_DETECTION = "linedetection"
    INTRUSION = "intrusion"
    LOITERING = "loitering"
    
    # Eventos de analíticas
    PERSON_DETECTED = "person_detection"
    FACE_DETECTED = "face_detection"
    HANDS_UP = "hands_up"
    
    # Eventos del sistema
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CAMERA_ONLINE = "camera_online"
    CAMERA_OFFLINE = "camera_offline"

# ============================================================================
# CONFIGURACIÓN DE CÁMARAS
# ============================================================================
class CameraConstants:
    """Constantes relacionadas con cámaras"""
    # Resoluciones estándar
    RESOLUTION_4K = (3840, 2160)
    RESOLUTION_FHD = (1920, 1080)
    RESOLUTION_HD = (1280, 720)
    RESOLUTION_SD = (640, 480)
    
    # FPS estándar
    FPS_30 = 30
    FPS_25 = 25
    FPS_15 = 15
    FPS_10 = 10
    
    # Timeouts
    CONNECTION_TIMEOUT = 10  # segundos
    READ_TIMEOUT = 5        # segundos
    RECONNECT_INTERVAL = 30 # segundos

# ============================================================================
# CONFIGURACIÓN DE IA
# ============================================================================
class AIConstants:
    """Constantes para modelos de IA"""
    # YOLO
    YOLO_CONFIDENCE_THRESHOLD = 0.5
    YOLO_NMS_THRESHOLD = 0.4
    YOLO_PERSON_CLASS = 0
    
    # Face Detection
    FACE_CONFIDENCE_THRESHOLD = 0.5
    FACE_MIN_SIZE = (30, 30)
    
    # MediaPipe
    MEDIAPIPE_CONFIDENCE = 0.5
    MEDIAPIPE_TRACKING = 0.5

# ============================================================================
# CONFIGURACIÓN DE UI
# ============================================================================
class UIConstants:
    """Constantes de interfaz de usuario"""
    # Tamaños de ventana
    MIN_WINDOW_WIDTH = 1280
    MIN_WINDOW_HEIGHT = 720
    
    # Colores en hexadecimal
    COLOR_PRIMARY = "#007bff"
    COLOR_SUCCESS = "#28a745"
    COLOR_WARNING = "#ffc107"
    COLOR_DANGER = "#dc3545"
    COLOR_DARK = "#121212"
    COLOR_ACCENT = "#00bfff"
    
    # Tamaños de elementos
    BUTTON_HEIGHT = 40
    BUTTON_MIN_WIDTH = 150
    GRID_SPACING = 4
    
    # Tiempos de animación (ms)
    FLASH_DURATION = 400
    FADE_DURATION = 300

# ============================================================================
# CONFIGURACIÓN DE ARCHIVOS
# ============================================================================
class FileConstants:
    """Constantes de archivos y formatos"""
    # Formatos de video
    VIDEO_CODEC = "mp4v"
    VIDEO_EXTENSION = ".mp4"
    
    # Formatos de imagen
    IMAGE_FORMAT = "jpg"
    IMAGE_QUALITY = 95
    
    # Nombres de archivos de modelos
    YOLO_MODEL = "yolov8n.pt"
    FACE_PROTOTXT = "deploy.prototxt"
    FACE_MODEL = "res10_300x300_ssd_iter_140000.caffemodel"

# ============================================================================
# MENSAJES DEL SISTEMA
# ============================================================================
class Messages:
    """Mensajes estándar del sistema"""
    # Inicio y cierre
    SYSTEM_STARTING = "🚀 Iniciando VMS - Video Management System"
    SYSTEM_READY = "✅ Sistema VMS listo y operativo"
    SYSTEM_SHUTTING_DOWN = "🔄 Cerrando sistema VMS..."
    SYSTEM_CLOSED = "✅ Sistema VMS cerrado correctamente"
    
    # Cámaras
    CAMERA_CONNECTING = "🔌 Conectando cámara {}"
    CAMERA_CONNECTED = "✅ Cámara {} conectada"
    CAMERA_DISCONNECTED = "❌ Cámara {} desconectada"
    CAMERA_RECONNECTING = "🔄 Reconectando cámara {}..."
    
    # Analíticas
    ANALYTICS_STARTED = "🤖 Analíticas iniciadas para cámara {}"
    ANALYTICS_STOPPED = "⏹️ Analíticas detenidas para cámara {}"
    
    # Eventos
    MOTION_DETECTED = "👁️ Movimiento detectado en cámara {}"
    PERSON_DETECTED = "👤 Persona detectada en cámara {}"
    FACE_DETECTED = "😊 Rostro detectado en cámara {}"
    
    # Errores comunes
    ERROR_CAMERA_CONNECTION = "❌ Error conectando cámara {}: {}"
    ERROR_MODEL_LOAD = "❌ Error cargando modelo {}: {}"
    ERROR_FILE_NOT_FOUND = "❌ Archivo no encontrado: {}"
    ERROR_PERMISSION_DENIED = "❌ Sin permisos para acceder: {}"

# ============================================================================
# CONFIGURACIÓN DE PERFORMANCE
# ============================================================================
class PerformanceConstants:
    """Constantes de rendimiento"""
    # Límites de memoria
    MAX_MEMORY_USAGE = 0.8  # 80% de la RAM
    MAX_GPU_MEMORY = 0.8    # 80% de la VRAM
    
    # Tamaños de buffer
    VIDEO_BUFFER_SIZE = 15
    AUDIO_BUFFER_SIZE = 10
    EVENT_BUFFER_SIZE = 100
    
    # Intervalos de limpieza (segundos)
    CLEANUP_INTERVAL = 300      # 5 minutos
    LOG_ROTATION_INTERVAL = 86400  # 24 horas
    
    # Límites de FPS por modo
    FPS_SURVEILLANCE_MODE = 30
    FPS_ANALYTICS_MODE = 15
    FPS_POWER_SAVE_MODE = 10

# ============================================================================
# CONFIGURACIÓN DE RED
# ============================================================================
class NetworkConstants:
    """Constantes de red"""
    # Puertos estándar
    RTSP_PORT = 554
    HTTP_PORT = 80
    HTTPS_PORT = 443
    
    # Timeouts de red
    CONNECTION_TIMEOUT = 10
    READ_TIMEOUT = 30
    SOCKET_TIMEOUT = 5
    
    # Reintentos
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # segundos
