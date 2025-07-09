import sys
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from core.camera_thread_tcp import CamaraThreadTCP
from config import config_manager
from ui.window_grid import VMSGridWindow
import qdarkstyle

# Configuración
SERVER_IP = '192.168.1.2'  # Cambia a la IP de tu servidor
SERVER_PORT = 9000

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('vms.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def setup_application():
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app.setApplicationName("VMS - Cliente TCP")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("VMS System")
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    return app

def start_camera_threads():
    camera_threads = {}
    for canal in config_manager.canales_originales:
        try:
            thread = CamaraThreadTCP(canal, SERVER_IP, SERVER_PORT)
            thread.start()
            camera_threads[canal] = thread
            logger.info(f"[TCP] Hilo iniciado para cámara {canal}")
        except Exception as e:
            logger.error(f"[TCP] Error al iniciar hilo para cámara {canal}: {e}")
    return camera_threads

def main():
    logger.info("Iniciando VMS Cliente TCP")
    app = setup_application()
    camera_threads = start_camera_threads()
    if not camera_threads:
        logger.error("No se pudieron iniciar hilos de cámara TCP")
        return 1
    ventana = VMSGridWindow(camera_threads)
    ventana.showMaximized()
    logger.info("Ventana principal mostrada (TCP)")
    exit_code = app.exec_()
    logger.info("Aplicación finalizada (TCP)")
    return exit_code

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
