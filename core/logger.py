# core/logger.py
"""
Sistema de logging profesional para VMS
Configuración centralizada con rotación automática y niveles
"""
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import sys

from config.settings import LOGGING, LOGS_DIR, APP_NAME

class VMSLogger:
    """Configurador de logging profesional para VMS"""
    
    def __init__(self):
        self.setup_logging()
    
    def setup_logging(self):
        """Configura el sistema de logging"""
        # Crear directorio de logs
        LOGS_DIR.mkdir(exist_ok=True)
        
        # Configurar logger raíz
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, LOGGING["level"]))
        
        # Limpiar handlers existentes
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Formatter personalizado
        formatter = logging.Formatter(
            fmt='%(asctime)s | %(name)-15s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para archivo con rotación
        log_file = LOGS_DIR / f"vms_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=LOGGING["max_size"],
            backupCount=LOGGING["backup_count"],
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)
        
        # Handler para consola
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)
        
        # Agregar handlers
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)
        
        # Logger específico para VMS
        self.logger = logging.getLogger("VMS")
        self.logger.info(f"🚀 {APP_NAME} - Sistema de logging inicializado")
        
    def get_logger(self, name: str = "VMS") -> logging.Logger:
        """Obtiene un logger con nombre específico"""
        return logging.getLogger(name)

# Instancia global
vms_logger = VMSLogger()

def get_logger(name: str = "VMS") -> logging.Logger:
    """Función conveniente para obtener logger"""
    return vms_logger.get_logger(name)

# Logger por defecto para el módulo
logger = get_logger(__name__)
