# config/config_manager.py
import threading
import numpy as np
from pathlib import Path

class ConfigManager:
    """
    Clase centralizada para gestionar la configuración y el estado de la aplicación.
    Utiliza un Lock para garantizar la seguridad en el acceso concurrente desde múltiples hilos.
    """
    def __init__(self):
        self._lock = threading.Lock()

        # --- Configuración Estática ---
        self.PERFORMANCE_CONFIG = {
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
        self.canales_originales = ['101', '501', '601', '901']
        self.canales_baja = {
            '101': '102',
            '501': '502',
            '601': '602',
            '901': '902'
        }
        self.rtsp_base = "rtsp://admin:nunoa2018@192.168.67.63:554/Streaming/Channels/{}?tcp/"
        
        # --- Rutas y Carpetas ---
        self.output_folder = Path(r"C:\Users\MXL2442MK2\Desktop\vms\output")
        self._setup_output_directories()

        # --- Estado Dinámico (protegido por el lock) ---
        self._frames = {canal: np.zeros((480, 640, 3), dtype=np.uint8) for canal in self.canales_originales}
        self._canales_activos = {canal: canal for canal in self.canales_originales}
        self._analitica_activa = {canal: False for canal in self.canales_originales}
        self._recording_flags = {canal: False for canal in self.canales_originales}
        self._manos_arriba_activa = {canal: False for canal in self.canales_originales}
        self._rostros_activa = {canal: False for canal in self.canales_originales}
        self._snapshot_flags = {canal: False for canal in self.canales_originales}
        self._video_writers = {canal: None for canal in self.canales_originales}
        self._detener_hilos = False

    def _setup_output_directories(self):
        """Crea las carpetas de salida si no existen."""
        self.output_folder.mkdir(parents=True, exist_ok=True)
        (self.output_folder / "captures").mkdir(exist_ok=True)
        (self.output_folder / "rostros").mkdir(exist_ok=True)
        (self.output_folder / "videos").mkdir(exist_ok=True)
        (self.output_folder / "eventos").mkdir(exist_ok=True)

    # --- Métodos para acceder y modificar el estado de forma segura ---

    def get_frame(self, canal_id):
        with self._lock:
            return self._frames.get(canal_id)

    def set_frame(self, canal_id, frame):
        with self._lock:
            self._frames[canal_id] = frame

    def is_analytics_active(self, canal_id):
        with self._lock:
            return self._analitica_activa.get(canal_id, False)

    def toggle_analytics(self, canal_id):
        with self._lock:
            is_active = not self._analitica_activa.get(canal_id, False)
            self._analitica_activa[canal_id] = is_active
            # Cambiar a flujo de baja resolución si la analítica se activa
            if is_active:
                self._canales_activos[canal_id] = self.canales_baja.get(canal_id, canal_id)
            else:
                self._canales_activos[canal_id] = canal_id
            return is_active

    def get_active_channel_url(self, canal_id):
        with self._lock:
            canal_a_usar = self._canales_activos.get(canal_id, canal_id)
            return self.rtsp_base.format(canal_a_usar)
            
    def get_current_active_channel(self, canal_id):
        with self._lock:
            return self._canales_activos.get(canal_id, canal_id)

    def is_recording(self, canal_id):
        with self._lock:
            return self._recording_flags.get(canal_id, False)

    def toggle_recording(self, canal_id):
        with self._lock:
            self._recording_flags[canal_id] = not self._recording_flags.get(canal_id, False)
            return self._recording_flags[canal_id]

    def get_video_writer(self, canal_id):
        with self._lock:
            return self._video_writers.get(canal_id)

    def set_video_writer(self, canal_id, writer):
        with self._lock:
            self._video_writers[canal_id] = writer

    def is_hands_up_active(self, canal_id):
        with self._lock:
            return self._manos_arriba_activa.get(canal_id, False)

    def toggle_hands_up(self, canal_id):
        with self._lock:
            self._manos_arriba_activa[canal_id] = not self._manos_arriba_activa.get(canal_id, False)
            return self._manos_arriba_activa[canal_id]

    def is_face_detection_active(self, canal_id):
        with self._lock:
            return self._rostros_activa.get(canal_id, False)

    def toggle_face_detection(self, canal_id):
        with self._lock:
            self._rostros_activa[canal_id] = not self._rostros_activa.get(canal_id, False)
            return self._rostros_activa[canal_id]
            
    def take_snapshot(self, canal_id):
        """Activa el flag para tomar un snapshot."""
        with self._lock:
            self._snapshot_flags[canal_id] = True

    def is_snapshot_requested(self, canal_id):
        """Consulta si se pidió un snapshot."""
        with self._lock:
            return self._snapshot_flags.get(canal_id, False)

    def clear_snapshot_request(self, canal_id):
        """Limpia el flag de snapshot una vez tomado."""
        with self._lock:
            if canal_id in self._snapshot_flags:
                self._snapshot_flags[canal_id] = False

    def should_stop(self):
        with self._lock:
            return self._detener_hilos

    def set_stop_flag(self):
        with self._lock:
            self._detener_hilos = True

# Crear una única instancia global que será usada por toda la aplicación
config_manager = ConfigManager()
