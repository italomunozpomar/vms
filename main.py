import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

# Configurar logging profesional
from core.logger import get_logger
logger = get_logger("VMS.Main")

# Importar configuración
from config.settings import APP_NAME, APP_VERSION, ensure_directories
from core.constants import VERSION, Messages
from core.system_info import get_system_info

# Inicializar directorios
ensure_directories()

logger.info(Messages.SYSTEM_STARTING)
logger.info(f"🏷️ Versión: {APP_VERSION} (Build: {VERSION})")

# ✅ Inicialización temprana de MediaPipe (para evitar error DLL con PyQt + threads)
try:
    import mediapipe as mp
    mp_pose = mp.solutions.pose
    _ = mp_pose.Pose()
    logger.info("✅ MediaPipe preinicializado correctamente")
except Exception as e:
    logger.error(f"❌ Error al inicializar MediaPipe: {e}")

# ✅ Inicializar monitor de rendimiento
try:
    from core.performance_monitor import start_performance_monitoring, stop_performance_monitoring
    logger.info("✅ Monitor de rendimiento disponible")
except Exception as e:
    logger.warning(f"⚠️ Monitor de rendimiento no disponible: {e}")
    start_performance_monitoring = lambda: None
    stop_performance_monitoring = lambda: None

# Importaciones principales
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from core.camera_thread import CamaraThread
from ui.window_grid import VMSGridWindow
from core.hikvision_events import iniciar_eventos, detener_eventos

# Importar tema oscuro
try:
    import qdarkstyle
except ImportError:
    qdarkstyle = None

def setup_application():
    """Configura la aplicación PyQt con optimizaciones"""
    app = QApplication(sys.argv)

    # Configuraciones de rendimiento para PyQt
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    # Aplicar tema oscuro profesional
    if qdarkstyle:
        try:
            app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
            logger.info("✅ Tema oscuro aplicado correctamente")
        except Exception as e:
            logger.warning(f"⚠️ Error aplicando tema oscuro: {e}")
    else:
        logger.warning("⚠️ QDarkStyle no disponible, usando tema por defecto")

    # Configurar icono y metadata de la aplicación
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("VMS Development")
    
    return app

def initialize_system():
    """Inicializa todos los componentes del sistema"""
    logger.info("🔧 Inicializando componentes del sistema...")
    
    # Mostrar información del sistema
    try:
        system_info = get_system_info()
        system_info.print_summary()
    except Exception as e:
        logger.warning(f"⚠️ No se pudo obtener información del sistema: {e}")
    
    # Inicializar configuración
    from config import config_manager
    logger.info("✅ Configuración del sistema cargada")
    
    # Inicializar monitor de rendimiento
    start_performance_monitoring()
    logger.info("✅ Monitor de rendimiento iniciado")
    
    return config_manager

def create_camera_threads(config_manager):
    """Crea e inicializa los hilos de las cámaras"""
    camera_threads = {}
    logger.info("📹 Iniciando hilos de cámaras...")
    
    for canal in config_manager.canales_originales:
        try:
            thread = CamaraThread(canal)
            camera_threads[canal] = thread
            thread.start()
            logger.info(f"✅ Hilo iniciado para cámara {canal}")
        except Exception as e:
            logger.error(f"❌ Error iniciando cámara {canal}: {e}")
    
    return camera_threads

def main():
    """Función principal del VMS"""
    try:
        # Configurar aplicación
        app = setup_application()
        
        # Inicializar sistema
        config_manager = initialize_system()
        
        # Crear hilos de cámaras
        camera_threads = create_camera_threads(config_manager)
        
        if not camera_threads:
            logger.error("❌ No se pudieron iniciar hilos de cámara")
            return 1
        
        # Crear ventana principal
        logger.info("🖥️ Creando interfaz principal...")
        main_window = VMSGridWindow(camera_threads)
        
        # Configurar cierre limpio
        def cleanup():
            logger.info("🔄 Iniciando cierre del sistema...")
            detener_eventos()
            stop_performance_monitoring()
            config_manager.set_stop_flag()
            logger.info(Messages.SYSTEM_CLOSED)
        
        app.aboutToQuit.connect(cleanup)
        
        # Mostrar ventana
        main_window.showMaximized()
        logger.info("✅ Ventana principal mostrada")
        logger.info(Messages.SYSTEM_READY)
        
        # Ejecutar aplicación
        return app.exec_()
        
    except KeyboardInterrupt:
        logger.info("🔄 Interrupción de usuario detectada")
        return 0
    except Exception as e:
        logger.error(f"❌ Error crítico en main: {e}", exc_info=True)
        return 1
    finally:
        logger.info("🔄 Limpieza final completada")

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
