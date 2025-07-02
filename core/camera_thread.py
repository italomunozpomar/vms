import cv2
import time
import threading
import os
from datetime import datetime
import numpy as np
import queue
import atexit

from config import config_manager
from core.yolo_model import modelo_yolo
from core.manos_arriba import detectar_manos_arriba
from core.zona_interes import procesar_zona_interes
from core.deteccion_rostro import detectar_rostros

# Cola para procesamiento asíncrono de rostros
rostros_queue = queue.Queue(maxsize=5)
rostros_thread = None
rostros_running = False

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
                if frame_processed is not None:
                    config_manager.set_frame(canal_id, frame_processed)
            except Exception as e:
                print(f"Error en worker de rostros para cámara {canal_id}: {e}")
                
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error en worker de rostros: {e}")

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

iniciar_rostros_worker()

class CamaraThread(threading.Thread):
    def __init__(self, canal_id):
        super().__init__()
        self.canal_id = canal_id
        self.frame_count = 0
        self.class_id = 0  # clase persona
        self.last_detections = []
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = config_manager.PERFORMANCE_CONFIG['reconnect_attempts']
        self.reconnect_delay = config_manager.PERFORMANCE_CONFIG['reconnect_delay']

    def run(self):
        while not config_manager.should_stop():
            url = config_manager.get_active_channel_url(self.canal_id)
            canal_actual = config_manager.get_current_active_channel(self.canal_id)

            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, config_manager.PERFORMANCE_CONFIG['buffer_size'])
            cap.set(cv2.CAP_PROP_FPS, config_manager.PERFORMANCE_CONFIG['max_fps'])
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config_manager.PERFORMANCE_CONFIG['frame_width'])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config_manager.PERFORMANCE_CONFIG['frame_height'])
            cap.open(url, cv2.CAP_FFMPEG)

            if not cap.isOpened():
                print(f"No se pudo abrir la cámara {canal_actual}")
                self.reconnect_attempts += 1
                if self.reconnect_attempts >= self.max_reconnect_attempts:
                    print(f"Máximo de intentos de reconexión alcanzado para cámara {canal_actual}")
                    time.sleep(5)
                    self.reconnect_attempts = 0
                time.sleep(self.reconnect_delay)
                continue

            print(f"Cámara {canal_actual} conectada")
            self.reconnect_attempts = 0

            while not config_manager.should_stop():
                if canal_actual != config_manager.get_current_active_channel(self.canal_id):
                    cap.release()
                    break

                ret, frame = cap.read()
                if not ret:
                    print(f"No se pudo leer frame de {canal_actual}, intentando reconectar...")
                    cap.release()
                    time.sleep(self.reconnect_delay)
                    break

                self.frame_count += 1

                # --- Analíticas ---
                if config_manager.is_analytics_active(self.canal_id) and (self.frame_count % config_manager.PERFORMANCE_CONFIG['yolo_frame_skip'] == 0):
                    try:
                        # Usar la GPU (device=0) para la inferencia de YOLO
                        results = modelo_yolo(frame, device=0, verbose=False)
                        detections = []
                        for result in results:
                            boxes = result.boxes
                            for box in boxes:
                                if int(box.cls[0]) == self.class_id:
                                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                                    conf = box.conf[0].cpu().numpy()
                                    detections.append([x1, y1, x2, y2, conf])
                        self.last_detections = detections
                    except Exception as e:
                        print(f"Error en detección YOLO para cámara {self.canal_id}: {e}")
                
                for box in self.last_detections:
                    x1, y1, x2, y2, conf = map(int, box)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, "Persona Detectada", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                if config_manager.is_hands_up_active(self.canal_id) and (self.frame_count % config_manager.PERFORMANCE_CONFIG['hands_frame_skip'] == 0):
                    try:
                        frame, detectado = detectar_manos_arriba(frame, guardar_captura=True, output_path=str(config_manager.output_folder))
                        if detectado:
                            print(f"Canal {self.canal_id}: ¡Manos arriba detectadas!")
                    except Exception as e:
                        print(f"Error en detección manos arriba para cámara {self.canal_id}: {e}")

                if config_manager.is_face_detection_active(self.canal_id) and (self.frame_count % config_manager.PERFORMANCE_CONFIG['face_frame_skip'] == 0):
                    try:
                        if not rostros_queue.full():
                            frame_copy = frame.copy()
                            rostros_queue.put((self.canal_id, frame_copy), block=False)
                    except Exception as e:
                        print(f"Error al enviar frame para detección de rostros en cámara {self.canal_id}: {e}")

                config_manager.set_frame(self.canal_id, frame)

                # --- Grabación y Snapshot ---
                if config_manager.is_recording(self.canal_id):
                    video_writer = config_manager.get_video_writer(self.canal_id)
                    if video_writer is None:
                        try:
                            filename = datetime.now().strftime(f"{self.canal_id}_%Y%m%d_%H%M%S.avi")
                            filepath = os.path.join(config_manager.output_folder, "videos", filename)
                            fourcc = cv2.VideoWriter_fourcc(*'XVID')
                            h, w = frame.shape[:2]
                            new_writer = cv2.VideoWriter(filepath, fourcc, 30.0, (w, h))
                            config_manager.set_video_writer(self.canal_id, new_writer)
                            print(f"🎥 Comenzó grabación para cámara {self.canal_id}")
                        except Exception as e:
                            print(f"Error al iniciar grabación para cámara {self.canal_id}: {e}")
                    
                    if config_manager.get_video_writer(self.canal_id) is not None:
                        try:
                            config_manager.get_video_writer(self.canal_id).write(frame)
                        except Exception as e:
                            print(f"Error al escribir frame en grabación para cámara {self.canal_id}: {e}")
                else:
                    video_writer = config_manager.get_video_writer(self.canal_id)
                    if video_writer is not None:
                        try:
                            video_writer.release()
                            config_manager.set_video_writer(self.canal_id, None)
                            print(f"Grabación detenida para cámara {self.canal_id}")
                        except Exception as e:
                            print(f"Error al detener grabación para cámara {self.canal_id}: {e}")

                if config_manager.is_snapshot_requested(self.canal_id):
                    try:
                        filename = datetime.now().strftime(f"{self.canal_id}_snapshot_%Y%m%d_%H%M%S.jpg")
                        filepath = os.path.join(config_manager.output_folder, "captures", filename)
                        cv2.imwrite(filepath, frame)
                        print(f"📸 Snapshot guardado: {filepath}")
                        config_manager.clear_snapshot_request(self.canal_id)
                    except Exception as e:
                        print(f"Error al guardar snapshot para cámara {self.canal_id}: {e}")
                        config_manager.clear_snapshot_request(self.canal_id)

            cap.release()
            video_writer = config_manager.get_video_writer(self.canal_id)
            if video_writer is not None:
                try:
                    video_writer.release()
                    config_manager.set_video_writer(self.canal_id, None)
                except Exception as e:
                    print(f"Error al liberar video writer para cámara {self.canal_id}: {e}")

atexit.register(detener_rostros_worker)
