import queue
import threading
import time
import os
from datetime import datetime
import atexit
import av
import cv2  # Solo para VideoWriter, imwrite y utilidades de imagen
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import pyqtSignal, QThread, Qt
import collections # Importar collections para deque

from config.database_manager import db_manager # Importar el gestor de la base de datos

from config import config_manager
from core.yolo_model import modelo_yolo
from core.manos_arriba import ManosArribaDetector
from core.deteccion_rostro import detectar_rostros

# Cola para procesamiento asíncrono de rostros
rostros_queue = queue.Queue(maxsize=config_manager.PERFORMANCE_CONFIG['max_queue_size'])
rostros_thread = None
rostros_running = False

# Cola para procesamiento asíncrono de manos arriba
manos_arriba_queue = queue.Queue(maxsize=config_manager.PERFORMANCE_CONFIG['max_queue_size'])
manos_arriba_thread = None
manos_arriba_running = False

# Cola para procesamiento asíncrono de grabación y snapshots
io_queue = queue.Queue(maxsize=config_manager.PERFORMANCE_CONFIG['io_queue_size'])
io_thread = None
io_running = False

def rostros_worker():
    """Worker thread para procesar detección de rostros de forma asíncrona"""
    global rostros_running
    while rostros_running:
        try:
            data = rostros_queue.get(timeout=1)
            if data is None:  # Señal de parada
                break
            
            canal_id, frame_copy = data
            
            try:
                frame_processed = detectar_rostros(frame_copy)
                # Ya no se guarda en config_manager, se procesa y se emite
                # config_manager.set_frame(canal_id, frame_processed)
            except Exception as e:
                print(f"Error en worker de rostros para cámara {canal_id}: {e}")
                
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error en worker de rostros: {e}")

def manos_arriba_worker():
    """Worker thread para procesar detección de manos arriba de forma asíncrona"""
    global manos_arriba_running
    # Instancia única por worker (puedes cambiar a un dict por canal si es necesario)
    detector = ManosArribaDetector()
    while manos_arriba_running:
        try:
            data = manos_arriba_queue.get(timeout=1)
            if data is None:  # Señal de parada
                break
            
            canal_id, frame_copy = data
            
            try:
                frame_processed, detectado = detector.detectar(frame_copy, guardar_captura=True, output_path=str(config_manager.output_folder), canal_id=canal_id)
                if detectado:
                    print(f"Canal {canal_id}: ¡Manos arriba detectadas!")
            except Exception as e:
                print(f"Error en worker de manos arriba para cámara {canal_id}: {e}")
                
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error en worker de manos arriba: {e}")

def io_worker():
    """Worker thread para procesar operaciones de E/S (grabación y snapshots) de forma asíncrona"""
    global io_running
    while io_running:
        try:
            task = io_queue.get(timeout=1)
            if task is None:  # Señal de parada
                break
            
            task_type = task['type']
            canal_id = task['canal_id']
            frame = task['frame']

            if task_type == 'record':
                import av
                video_writer = config_manager.get_video_writer(canal_id)
                if video_writer is None:
                    try:
                        filename = datetime.now().strftime(f"{canal_id}_%Y%m%d_%H%M%S.mp4")
                        filepath = os.path.join(config_manager.output_folder, "videos", filename)
                        h, w = frame.shape[:2]
                        container = av.open(filepath, mode='w')
                        stream = container.add_stream('libx264', rate=25)
                        stream.width = w
                        stream.height = h
                        stream.pix_fmt = 'yuv420p'
                        config_manager.set_video_writer(canal_id, (container, stream))
                        print(f"🎥 Comenzó grabación para cámara {canal_id} (PyAV MP4)")
                    except Exception as e:
                        print(f"Error al iniciar grabación para cámara {canal_id} (PyAV): {e}")
                
                writer_tuple = config_manager.get_video_writer(canal_id)
                if writer_tuple is not None:
                    try:
                        container, stream = writer_tuple
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        video_frame = av.VideoFrame.from_ndarray(frame_rgb, format='rgb24')
                        for packet in stream.encode(video_frame):
                            container.mux(packet)
                    except Exception as e:
                        print(f"Error al escribir frame en grabación para cámara {canal_id} (PyAV): {e}")
            
            elif task_type == 'stop_record':
                writer_tuple = config_manager.get_video_writer(canal_id)
                if writer_tuple is not None:
                    try:
                        container, stream = writer_tuple
                        # Flush stream
                        for packet in stream.encode():
                            container.mux(packet)
                        container.close()
                        config_manager.set_video_writer(canal_id, None)
                        print(f"Grabación detenida para cámara {canal_id} (PyAV MP4)")
                    except Exception as e:
                        print(f"Error al detener grabación para cámara {canal_id} (PyAV): {e}")

            elif task_type == 'event_record':
                import av
                event_video_writer = config_manager.get_event_video_writer(canal_id)
                if event_video_writer is None:
                    event_details = config_manager.get_event_recording_details(canal_id)
                    if not event_details or not event_details.get('file_path'):
                        print(f"ERROR: io_worker - No se encontraron detalles de grabación o file_path para el evento en cámara {canal_id}")
                        continue

                    filepath = event_details['file_path']
                    print(f"DEBUG: io_worker - Intentando iniciar VideoWriter (PyAV) para evento en '{filepath}'")
                    try:
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        h, w = frame.shape[:2]
                        container = av.open(filepath, mode='w')
                        stream = container.add_stream('libx264', rate=config_manager.EVENT_FPS)
                        stream.width = w
                        stream.height = h
                        stream.pix_fmt = 'yuv420p'
                        config_manager.set_event_video_writer(canal_id, (container, stream))
                        print(f"🎥 DEBUG: io_worker - VideoWriter de evento iniciado para cámara {canal_id} (PyAV MP4)")
                    except Exception as e:
                        print(f"ERROR: io_worker - Error al iniciar grabación de evento para cámara {canal_id} (PyAV): {e}")
                writer_tuple = config_manager.get_event_video_writer(canal_id)
                if writer_tuple is not None:
                    try:
                        container, stream = writer_tuple
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        video_frame = av.VideoFrame.from_ndarray(frame_rgb, format='rgb24')
                        for packet in stream.encode(video_frame):
                            container.mux(packet)
                    except Exception as e:
                        print(f"ERROR: io_worker - Error al escribir frame en grabación de evento para cámara {canal_id} (PyAV): {e}")

            elif task_type == 'stop_event_record':
                print(f"DEBUG: io_worker - Solicitud de detener grabación de evento para cámara {canal_id}")
                writer_tuple = config_manager.get_event_video_writer(canal_id)
                if writer_tuple is not None:
                    try:
                        container, stream = writer_tuple
                        # Flush stream
                        for packet in stream.encode():
                            container.mux(packet)
                        container.close()
                        config_manager.set_event_video_writer(canal_id, None)
                        print(f"DEBUG: io_worker - VideoWriter de evento liberado para cámara {canal_id} (PyAV MP4)")

                        # Registrar en la base de datos
                        event_details = config_manager.get_event_recording_details(canal_id)
                        if event_details and 'file_path' in event_details:
                            file_path = event_details['file_path']
                            # Calcular la duración real del video grabado
                            actual_duration = 0.0
                            if os.path.exists(file_path):
                                try:
                                    import av as av2
                                    container2 = av2.open(file_path)
                                    total_frames = container2.streams.video[0].frames
                                    fps = float(container2.streams.video[0].average_rate)
                                    if fps > 0:
                                        actual_duration = total_frames / fps
                                    container2.close()
                                except Exception as e:
                                    print(f"ADVERTENCIA: No se pudo abrir el archivo de video {file_path} para calcular la duración con PyAV: {e}")

                            print(f"DEBUG: io_worker - Intentando registrar evento en DB para cámara {canal_id} con detalles: {event_details}, duración real: {actual_duration:.2f}s")
                            db_manager.insert_event_recording(
                                camera_id=canal_id,
                                event_type=event_details['event_type'],
                                event_description=event_details['event_description'],
                                timestamp=event_details['timestamp'],
                                file_path=file_path,
                                duration_seconds=actual_duration
                            )
                            config_manager.clear_event_recording_details(canal_id)
                            print(f"DEBUG: io_worker - Evento de grabación registrado en DB para cámara {canal_id}")
                        else:
                            print(f"ADVERTENCIA: io_worker - No se encontraron detalles de grabación o file_path para el evento en cámara {canal_id}")

                    except Exception as e:
                        print(f"ERROR: io_worker - Error al detener grabación de evento o registrar en DB para cámara {canal_id} (PyAV): {e}")

            elif task_type == 'snapshot':
                try:
                    filename = datetime.now().strftime(f"{canal_id}_snapshot_%Y%m%d_%H%M%S.jpg")
                    filepath = os.path.join(config_manager.output_folder, "captures", filename)
                    cv2.imwrite(filepath, frame)
                    print(f"📸 Snapshot guardado: {filepath}")
                    config_manager.clear_snapshot_request(canal_id)
                except Exception as e:
                    print(f"Error al guardar snapshot para cámara {canal_id}: {e}")
                    config_manager.clear_snapshot_request(canal_id)
                
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error en worker de E/S: {e}")

def iniciar_rostros_worker():
    """Inicia el worker thread para rostros"""
    global rostros_thread, rostros_running
    if rostros_thread is None or not rostros_thread.is_alive():
        rostros_running = True
        rostros_thread = threading.Thread(target=rostros_worker, daemon=True)
        rostros_thread.start()
        print("Worker de rostros iniciado")

def detener_rostros_worker():
    """Detiene el worker thread de rostros"""
    global rostros_running
    rostros_running = False
    if rostros_thread and rostros_thread.is_alive():
        rostros_queue.put(None)
        rostros_thread.join(timeout=2)
        print("Worker de rostros detenido")

def iniciar_manos_arriba_worker():
    """Inicia el worker thread para manos arriba"""
    global manos_arriba_thread, manos_arriba_running
    if manos_arriba_thread is None or not manos_arriba_thread.is_alive():
        manos_arriba_running = True
        manos_arriba_thread = threading.Thread(target=manos_arriba_worker, daemon=True)
        manos_arriba_thread.start()
        print("Worker de manos arriba iniciado")

def detener_manos_arriba_worker():
    """Detiene el worker thread de manos arriba"""
    global manos_arriba_running
    manos_arriba_running = False
    if manos_arriba_thread and manos_arriba_thread.is_alive():
        manos_arriba_queue.put(None)
        manos_arriba_thread.join(timeout=2)
        print("Worker de manos arriba detenido")

def iniciar_io_worker():
    """Inicia el worker thread para operaciones de E/S"""
    global io_thread, io_running
    if io_thread is None or not io_thread.is_alive():
        io_running = True
        io_thread = threading.Thread(target=io_worker, daemon=True)
        io_thread.start()
        print("Worker de E/S iniciado")

def detener_io_worker():
    """Detiene el worker thread de E/S"""
    global io_running
    io_running = False
    if io_thread and io_thread.is_alive():
        io_queue.put(None)
        io_thread.join(timeout=2)
        print("Worker de E/S detenido")

iniciar_rostros_worker()
iniciar_manos_arriba_worker()
iniciar_io_worker()

class CamaraThread(QThread): # Heredar de QThread
    frame_ready = pyqtSignal(str, object) # Señal para enviar el frame procesado a la UI (np.ndarray RGB)

    def __init__(self, canal_id):
        super().__init__()
        self.canal_id = canal_id
        self.frame_count = 0
        self.class_id = 0  # clase persona
        self.last_detections = []
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = config_manager.PERFORMANCE_CONFIG['reconnect_attempts']
        self.reconnect_delay = config_manager.PERFORMANCE_CONFIG['reconnect_delay']
        self.frame_buffer = collections.deque(maxlen=config_manager.PERFORMANCE_CONFIG['buffer_size'] * config_manager.EVENT_FPS) # Búfer para frames previos al evento
        self.is_event_recording = False
        self.event_recording_frames_left = 0
        self.event_recording_writer = None # Para el VideoWriter específico de grabación por evento
        self.last_event_record_time = 0
        
        # Control de FPS para suavizar la visualización
        self.target_fps = config_manager.PERFORMANCE_CONFIG['max_fps']
        self.frame_interval = 1.0 / self.target_fps
        self.last_frame_time = 0

    def run(self):
        import av
        while not config_manager.should_stop():
            url = config_manager.get_active_channel_url(self.canal_id)
            canal_actual = config_manager.get_current_active_channel(self.canal_id)

            try:
                container = av.open(url)
            except av.AVError as e:
                print(f"No se pudo abrir la cámara {canal_actual} con PyAV: {e}")
                self.reconnect_attempts += 1
                if self.reconnect_attempts >= self.max_reconnect_attempts:
                    print(f"Máximo de intentos de reconexión alcanzado para cámara {canal_actual}")
                    time.sleep(5)
                    self.reconnect_attempts = 0
                time.sleep(self.reconnect_delay)
                continue

            print(f"Cámara {canal_actual} conectada (PyAV)")
            self.reconnect_attempts = 0

            start_time = time.time()
            fps_frame_count = 0

            for frame in container.decode(video=0):
                if config_manager.should_stop():
                    break

                # Control de FPS RELAJADO para mejor fluidez visual
                current_time = time.time()
                time_since_last_frame = current_time - self.last_frame_time
                
                # Solo limitar si es excesivamente rápido (más de 60 FPS)
                if time_since_last_frame < 0.016:  # 1/60 = 0.016 segundos
                    continue  # Saltar solo si es muy rápido
                
                self.last_frame_time = current_time

                img_bgr = frame.to_ndarray(format="bgr24")
                self.frame_count += 1
                fps_frame_count += 1

                if time.time() - start_time >= 1.0:
                    fps_frame_count = 0
                    start_time = time.time()

                self.frame_buffer.append(img_bgr.copy())

                # --- Lógica de Grabación por Evento ---
                if self.is_event_recording:
                    if self.event_recording_frames_left > 0:
                        try:
                            if not io_queue.full():
                                io_queue.put({'type': 'event_record', 'canal_id': self.canal_id, 'frame': img_bgr.copy()}, block=False)
                                self.event_recording_frames_left -= 1
                        except Exception as e:
                            print(f"Error al enviar frame para grabación de evento en cámara {self.canal_id}: {e}")
                    else:
                        self.is_event_recording = False
                        try:
                            if not io_queue.full():
                                io_queue.put({'type': 'stop_event_record', 'canal_id': self.canal_id, 'frame': None}, block=False)
                        except Exception as e:
                            print(f"Error al enviar señal de detener grabación de evento para cámara {self.canal_id}: {e}")

                # --- Analíticas con frame skip adaptativo ---
                yolo_skip = config_manager.get_adaptive_frame_skip('yolo', self.canal_id)
                if config_manager.is_analytics_active(self.canal_id) and (self.frame_count % yolo_skip == 0):
                    try:
                        # Usar el mismo device que el modelo YOLO
                        from core.yolo_model import device as yolo_device
                        
                        # Optimización: Redimensionar frame para YOLO si es necesario
                        h, w = img_bgr.shape[:2]
                        if h > 640 or w > 640:
                            # Redimensionar manteniendo aspect ratio
                            scale = min(640/w, 640/h)
                            new_w, new_h = int(w * scale), int(h * scale)
                            img_resized = cv2.resize(img_bgr, (new_w, new_h))
                        else:
                            img_resized = img_bgr
                        
                        # Ejecutar inferencia YOLO
                        results = modelo_yolo(img_resized, device=yolo_device, verbose=False)
                        detections = []
                        
                        for result in results:
                            boxes = result.boxes
                            if boxes is not None:
                                for box in boxes:
                                    if int(box.cls[0]) == self.class_id:
                                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                        conf = box.conf[0].cpu().numpy()
                                        
                                        # Escalar coordenadas de vuelta al frame original
                                        if h > 640 or w > 640:
                                            x1, y1, x2, y2 = x1/scale, y1/scale, x2/scale, y2/scale
                                        
                                        detections.append([x1, y1, x2, y2, conf])
                        
                        self.last_detections = detections
                    except Exception as e:
                        print(f"Error en detección YOLO para cámara {self.canal_id}: {e}")
                        self.last_detections = []

                if config_manager.is_analytics_active(self.canal_id):
                    for box in self.last_detections:
                        x1, y1, x2, y2, conf = map(int, box)
                        cv2.rectangle(img_bgr, (x1, y1), (x2, y2), (0, 255, 0), 2)
                        cv2.putText(img_bgr, "Persona Detectada", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                hands_skip = config_manager.get_adaptive_frame_skip('hands', self.canal_id)
                if config_manager.is_hands_up_active(self.canal_id) and (self.frame_count % hands_skip == 0):
                    try:
                        if not manos_arriba_queue.full():
                            frame_copy = img_bgr.copy()
                            manos_arriba_queue.put((self.canal_id, frame_copy), block=False)
                        else:
                            print(f"⚠️ Cola de manos arriba llena para cámara {self.canal_id}, descartando frame")
                    except Exception as e:
                        print(f"Error al enviar frame para detección de manos arriba en cámara {self.canal_id}: {e}")

                face_skip = config_manager.get_adaptive_frame_skip('face', self.canal_id)
                if config_manager.is_face_detection_active(self.canal_id) and (self.frame_count % face_skip == 0):
                    try:
                        if not rostros_queue.full():
                            frame_copy = img_bgr.copy()
                            rostros_queue.put((self.canal_id, frame_copy), block=False)
                        else:
                            print(f"⚠️ Cola de rostros llena para cámara {self.canal_id}, descartando frame")
                    except Exception as e:
                        print(f"Error al enviar frame para detección de rostros en cámara {self.canal_id}: {e}")

                texto = f"Cámara {self.canal_id}"
                estados = []
                if config_manager.is_recording(self.canal_id): estados.append("Grabando: ON")
                if config_manager.is_analytics_active(self.canal_id): estados.append("Personas: ON")
                if config_manager.is_hands_up_active(self.canal_id): estados.append("Manos: ON")
                if config_manager.is_face_detection_active(self.canal_id): estados.append("Rostros: ON")

                if estados:
                    texto += " | " + " | ".join(estados)

                rgb_frame = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
                self.frame_ready.emit(self.canal_id, rgb_frame)

                if config_manager.is_recording(self.canal_id):
                    try:
                        if not io_queue.full():
                            io_queue.put({'type': 'record', 'canal_id': self.canal_id, 'frame': img_bgr.copy()}, block=False)
                    except Exception as e:
                        print(f"Error al enviar frame para grabación en cámara {self.canal_id}: {e}")
                else:
                    # Si la grabación se detuvo, enviar una señal al worker de E/S para liberar el VideoWriter
                    if config_manager.get_video_writer(self.canal_id) is not None:
                        try:
                            if not io_queue.full():
                                io_queue.put({'type': 'stop_record', 'canal_id': self.canal_id, 'frame': None}, block=False)
                        except Exception as e:
                            print(f"Error al enviar señal de detener grabación para cámara {self.canal_id}: {e}")

                # Lógica para la grabación por evento

                event_state = config_manager.get_event_recording_state(self.canal_id)
                if event_state and event_state['is_recording']:
                    # No necesitamos last_event_record_time aquí, config_manager maneja la duración
                    if event_state['frames_left'] > 0:
                        try:
                            if not io_queue.full():
                                io_queue.put({'type': 'event_record', 'canal_id': self.canal_id, 'frame': img_bgr.copy()}, block=False)
                                config_manager.set_event_recording_state(self.canal_id, True, event_state['frames_left'] - 1, event_state['requested_duration_seconds'])
                        except Exception as e:
                            print(f"Error al enviar frame para grabación de evento en cámara {self.canal_id}: {e}")
                    else:
                        # Finalizar grabación por evento
                        config_manager.set_event_recording_state(self.canal_id, False, 0, 0)
                        try:
                            if not io_queue.full():
                                io_queue.put({'type': 'stop_event_record', 'canal_id': self.canal_id, 'frame': None}, block=False)
                        except Exception as e:
                            print(f"Error al enviar señal de detener grabación de evento para cámara {self.canal_id}: {e}")

                if config_manager.is_snapshot_requested(self.canal_id):
                    try:
                        if not io_queue.full():
                            io_queue.put({'type': 'snapshot', 'canal_id': self.canal_id, 'frame': img_bgr.copy()}, block=False)
                    except Exception as e:
                        print(f"Error al enviar solicitud de snapshot para cámara {self.canal_id}: {e}")
                
                # Remover el sleep para máxima fluidez visual

            # cap.release() eliminado: ya no se usa OpenCV VideoCapture
            # Asegurarse de liberar cualquier VideoWriter activo al detener el hilo
            if self.event_recording_writer is not None:
                self.event_recording_writer.release()
                self.event_recording_writer = None
            video_writer = config_manager.get_video_writer(self.canal_id)
            if video_writer is not None:
                try:
                    video_writer.release()
                    config_manager.set_video_writer(self.canal_id, None)
                except Exception as e:
                    print(f"Error al liberar video writer para cámara {self.canal_id}: {e}")

atexit.register(detener_rostros_worker)
atexit.register(detener_manos_arriba_worker)
atexit.register(detener_io_worker)
