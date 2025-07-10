# config/config_manager.py
import threading
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta

class ConfigManager:
    """
    Clase centralizada para gestionar la configuración y el estado de la aplicación.
    Utiliza un Lock para garantizar la seguridad en el acceso concurrente desde múltiples hilos.
    """
    def __init__(self):
        self._lock = threading.Lock()

        # --- Configuración Estática ---
        self.PERFORMANCE_CONFIG = {
            'max_fps': 30,  # Aumentado a 30 para mejor fluidez
            'frame_width': 1920,
            'frame_height': 1080,
            'buffer_size': 15,  # Reducido para menor latencia
            'reconnect_attempts': 5,
            'reconnect_delay': 2,
            'yolo_frame_skip': 3,  # Incrementado ligeramente para balance
            'hands_frame_skip': 5,  # Incrementado para reducir carga
            'face_frame_skip': 8,  # Incrementado para reducir carga
            'max_queue_size': 6,  # Reducido para menor latencia
            'io_queue_size': 15,  # Reducido para menor latencia
            'gpu_memory_fraction': 0.8,  # Aumentado para mejor rendimiento
            'enable_gpu_preprocessing': True,  # Habilitar preprocesamiento en GPU
            'enable_frame_interpolation': False,  # Interpolación de frames
            'compression_quality': 85,  # Calidad de compresión para grabación
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
        # Usar Path(__file__).parent.parent para obtener la ruta del directorio raíz del proyecto (vms)
        self.output_folder = Path(__file__).parent.parent / "output"
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
        self._event_video_writers = {canal: None for canal in self.canales_originales} # Nuevo para grabaciones de eventos
        self._event_recording_states = {canal: {'is_recording': False, 'frames_left': 0, 'requested_duration_seconds': 0} for canal in self.canales_originales} # Nuevo estado de grabación por evento
        self._event_recording_details = {canal: None for canal in self.canales_originales} # Para almacenar detalles del evento y filepath
        self._last_event_timestamp = {canal: None for canal in self.canales_originales} # Para controlar la extensión de la grabación por evento
        self._last_event_trigger_time = {canal: datetime.min for canal in self.canales_originales} # Para controlar el cooldown de eventos
        self._event_recording_start_time = {canal: None for canal in self.canales_originales} # Para el inicio real de la grabación de evento
        self._detener_hilos = False

        # Constantes para el control de grabación de eventos
        self.COOLDOWN_SECONDS = 5
        self.MAX_EVENT_RECORD_SECONDS = 10
        self.EVENT_FPS = 25 # FPS para la grabación de eventos (igual que la visualización y grabación normal)
        self.POST_EVENT_RECORD_SECONDS = 10 # Cuántos segundos después del evento se graban

    def _setup_output_directories(self):
        """Crea las carpetas de salida si no existen."""
        self.output_folder.mkdir(parents=True, exist_ok=True)
        (self.output_folder / "captures").mkdir(exist_ok=True)
        (self.output_folder / "captures" / "manos_arriba").mkdir(exist_ok=True)  # Carpeta específica para manos arriba
        (self.output_folder / "captures" / "linecrossing").mkdir(exist_ok=True)  # Mantener las existentes
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
            # Al activar la analítica, ya no se cambia al flujo de baja resolución.
            # El sistema continuará usando el canal principal definido en _canales_activos.
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

    def get_event_video_writer(self, canal_id):
        with self._lock:
            return self._event_video_writers.get(canal_id)

    def set_event_video_writer(self, canal_id, writer):
        with self._lock:
            self._event_video_writers[canal_id] = writer

    def get_event_recording_state(self, canal_id):
        with self._lock:
            return self._event_recording_states.get(canal_id)

    def set_event_recording_state(self, canal_id, is_recording, frames_left, requested_duration_seconds):
        with self._lock:
            self._event_recording_states[canal_id] = {'is_recording': is_recording, 'frames_left': frames_left, 'requested_duration_seconds': requested_duration_seconds}

    def set_event_recording_details(self, canal_id, details):
        with self._lock:
            self._event_recording_details[canal_id] = details

    def get_event_recording_details(self, canal_id):
        with self._lock:
            return self._event_recording_details.get(canal_id)

    def clear_event_recording_details(self, canal_id):
        with self._lock:
            if canal_id in self._event_recording_details:
                self._event_recording_details[canal_id] = None

    def start_event_recording(self, canal_id, event_type, event_description, timestamp, duration_seconds):
        """Inicia una grabación de evento para la cámara especificada."""
        now = datetime.now()

        with self._lock:
            # 1. Lógica de Cooldown
            if (now - self._last_event_trigger_time[canal_id]).total_seconds() < self.COOLDOWN_SECONDS:
                # print(f"DEBUG: Cooldown activo para cámara {canal_id}. Ignorando trigger.")
                return
            
            self._last_event_trigger_time[canal_id] = now

            # 2. Lógica de Extensión Controlada / Inicio de Nueva Grabación
            if self._event_recording_states[canal_id]['is_recording']:
                # Si ya hay una grabación en curso, extender su duración hasta el máximo
                if self._event_recording_start_time[canal_id] is not None:
                    elapsed_time = (now - self._event_recording_start_time[canal_id]).total_seconds()
                    remaining_time_from_start = self.MAX_EVENT_RECORD_SECONDS - elapsed_time

                    if remaining_time_from_start > 0:
                        # Extender la duración restante hasta el máximo permitido
                        frames_to_add = int(remaining_time_from_start * self.EVENT_FPS)
                        self._event_recording_states[canal_id]['frames_left'] = frames_to_add
                        self._event_recording_states[canal_id]['requested_duration_seconds'] = self.MAX_EVENT_RECORD_SECONDS
                        
                        # Actualizar los detalles del evento con la información del último evento que extendió la grabación
                        if self._event_recording_details[canal_id] is not None:
                            self._event_recording_details[canal_id].update({
                                'event_type': event_type,
                                'event_description': event_description,
                            })
                        else:
                            # Si los detalles son None, crear un nuevo diccionario
                            self._event_recording_details[canal_id] = {
                                'event_type': event_type,
                                'event_description': event_description,
                                'timestamp': timestamp,
                                'file_path': str(self.output_folder / "eventos" / now.strftime('%Y-%m-%d') / f"{now.strftime('%Y%m%d_%H%M%S')}_EVENT_{canal_id}.mp4")
                            }
                        print(f"Grabación de evento para cámara {canal_id} extendida. Duración restante: {remaining_time_from_start:.2f}s (max {self.MAX_EVENT_RECORD_SECONDS}s).")
                    else:
                        # La grabación ya excedió la duración máxima, dejar que termine
                        # print(f"DEBUG: Grabación de cámara {canal_id} ya excedió el máximo. No se extiende.")
                        pass
                return

            # Si no hay grabación en curso, iniciar una nueva
            self._event_recording_start_time[canal_id] = now
            
            # Generar la ruta del archivo de video aquí
            event_date_folder = now.strftime('%Y-%m-%d')
            filename = f"{now.strftime('%Y%m%d_%H%M%S')}_EVENT_{canal_id}.mp4"
            file_path = self.output_folder / "eventos" / event_date_folder / filename

            self._event_recording_states[canal_id] = {
                'is_recording': True, 
                'frames_left': self.MAX_EVENT_RECORD_SECONDS * self.EVENT_FPS, 
                'requested_duration_seconds': self.MAX_EVENT_RECORD_SECONDS
            }
            self._event_recording_details[canal_id] = {
                'event_type': event_type,
                'event_description': event_description,
                'timestamp': timestamp,
                'file_path': str(file_path) # Asignar la ruta completa como string
            }
            print(f"Solicitada grabación de evento para cámara {canal_id} en '{file_path}' por {self.MAX_EVENT_RECORD_SECONDS}s ({self.MAX_EVENT_RECORD_SECONDS * self.EVENT_FPS} frames).")

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

    def get_adaptive_frame_skip(self, model_type, canal_id):
        """
        Calcula frame skip dinámico basado en la carga del sistema.
        SIMPLIFICADO para mejor fluidez visual.
        """
        with self._lock:
            # Contar analíticas activas para este canal
            active_analytics = 0
            if self._analitica_activa.get(canal_id, False):
                active_analytics += 1
            if self._manos_arriba_activa.get(canal_id, False):
                active_analytics += 1
            if self._rostros_activa.get(canal_id, False):
                active_analytics += 1
            
            # Frame skips base (SIMPLIFICADOS)
            base_skips = {
                'yolo': self.PERFORMANCE_CONFIG['yolo_frame_skip'],
                'hands': self.PERFORMANCE_CONFIG['hands_frame_skip'],
                'face': self.PERFORMANCE_CONFIG['face_frame_skip']
            }
            
            # Multiplicador MUY CONSERVADOR
            if active_analytics >= 3:
                multiplier = 1.1  # Solo 10% de incremento
            elif active_analytics >= 2:
                multiplier = 1.05  # Solo 5% de incremento
            else:
                multiplier = 1.0  # Sin cambios
                
            # Calcular frame skip adaptativo
            adaptive_skip = int(base_skips.get(model_type, 3) * multiplier)
            
            # Límites muy conservadores para mantener fluidez
            min_skip = 1
            max_skip = 10  # Máximo muy bajo
            
            return max(min_skip, min(max_skip, adaptive_skip))

# Crear una única instancia global que será usada por toda la aplicación
config_manager = ConfigManager()
