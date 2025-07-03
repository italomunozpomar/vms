import sys
import logging
import mediapipe as mp
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vms.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ✅ Inicialización temprana de MediaPipe (para evitar error DLL con PyQt + threads)
try:
    mp_pose = mp.solutions.pose
    _ = mp_pose.Pose()
    logger.info("MediaPipe preinicializado desde main.py")
except Exception as e:
    logger.error(f"Error al inicializar MediaPipe: {e}")

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from core.camera_thread import CamaraThread
from config import config_manager  # Importar la instancia del ConfigManager
from ui.window_grid import VMSGridWindow
from core.hikvision_events import iniciar_eventos, detener_eventos

# Importar QDarkStyle
import qdarkstyle

def setup_application():
    """Configura la aplicación PyQt con optimizaciones"""
    app = QApplication(sys.argv)

    # Configuraciones de rendimiento para PyQt
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Configurar información de la aplicación
    app.setApplicationName("VMS - Sistema de Monitoreo de Video")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("VMS System")

    # Aplicar tema oscuro QDarkStyle
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    
    return app

def start_camera_threads():
    """Inicia los hilos de cámara con manejo de errores"""
    camera_threads = {}
    
    # Usar la configuración desde el ConfigManager
    for canal in config_manager.canales_originales:
        try:
            thread = CamaraThread(canal)
            thread.start()
            camera_threads[canal] = thread
            logger.info(f"Hilo iniciado para cámara {canal}")
        except Exception as e:
            logger.error(f"Error al iniciar hilo para cámara {canal}: {e}")
    
    return camera_threads

def main():
    """Función principal con manejo de errores"""
    try:
        logger.info("Iniciando VMS - Sistema de Monitoreo de Video")
        
        # Configurar aplicación
        app = setup_application()

        
        
        # Iniciar hilos por cámara
        camera_threads = start_camera_threads()
        
        if not camera_threads:
            logger.error("No se pudieron iniciar hilos de cámara")
            return 1
        
        # Crear y mostrar ventana principal
        try:
            ventana = VMSGridWindow(camera_threads)
            ventana.showMaximized()
            logger.info("Ventana principal mostrada")
        except Exception as e:
            logger.error(f"Error al crear ventana principal: {e}")
            return 1
        
        # Ejecutar aplicación
        logger.info("Ejecutando aplicación...")
        exit_code = app.exec_()
        
        # Señalizar a los hilos que deben detenerse
        config_manager.set_stop_flag()
        detener_eventos()
        logger.info("Aplicación finalizada.")
        return exit_code
        
    except KeyboardInterrupt:
        logger.info("Aplicación interrumpida por el usuario")
        config_manager.set_stop_flag()
        detener_eventos()
        return 0
    except Exception as e:
        logger.error(f"Error crítico en la aplicación: {e}")
        config_manager.set_stop_flag()
        detener_eventos()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
