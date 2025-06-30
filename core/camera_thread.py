import cv2
import time
import threading
import os
from datetime import datetime
import numpy as np
import queue
import atexit

from config.settings import (
    rtsp_base, canales_activos, analitica_activa,
    frames, recording_flags, video_writers, manos_arriba_activa,
    snapshot_flags, output_folder, zona_interes_activa, rostros_activa
)
from core.yolo_model import modelo_yolo  # Tu modelo YOLO (ultralytics)
from core.manos_arriba import detectar_manos_arriba  # Detección manos arriba
from core.zona_interes import procesar_zona_interes  # Zona interés
from core.deteccion_rostro import detectar_rostros

detener = False

# Cola para procesamiento asíncrono de rostros
rostros_queue = queue.Queue(maxsize=5)  # Limitar cola para evitar acumulación
rostros_thread = None
rostros_running = False

def rostros_worker():
    """Worker thread para procesar detección de rostros de forma asíncrona"""
    global rostros_running
    while rostros_running:
        try:
            # Obtener frame de la cola con timeout
            data = rostros_queue.get(timeout=1)
            if data is None:  # Señal de parada
                break
                
            canal_id, frame_copy = data
            
            try:
                # Procesar detección de rostros
                frame_processed = detectar_rostros(frame_copy)
                
                # Actualizar el frame original con los resultados
                if frame_processed is not None:
                    frames[canal_id] = frame_processed
                    
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
        rostros_queue.put(None)  # Señal de parada
        rostros_thread.join(timeout=2)
        print("Worker de rostros detenido")

# Iniciar worker al importar el módulo
iniciar_rostros_worker()

class CamaraThread(threading.Thread):
    def __init__(self, canal_id):
        super().__init__()
        self.canal_id = canal_id
        self.frame_count = 0
        self.class_id = 0  # clase persona
        self.frame_skip = 5  # Optimización: Detectar cada 5 frames en lugar de 3
        self.last_detections = []
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2

    def run(self):
        global detener

        while not detener:
            canal_actual = canales_activos[self.canal_id]
            url = rtsp_base.format(canal_actual)

            # Optimización: Configurar parámetros de captura para mejor rendimiento
            cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FPS, 25)  # Cambiado a 25 FPS para mejor calidad
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)  # Resolución estándar
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
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
            self.reconnect_attempts = 0  # Resetear contador de intentos

            while not detener:
                if canal_actual != canales_activos[self.canal_id]:
                    cap.release()
                    break

                ret, frame = cap.read()
                if not ret:
                    print(f"No se pudo leer frame de {canal_actual}, intentando reconectar...")
                    cap.release()
                    time.sleep(self.reconnect_delay)
                    break

                self.frame_count += 1

                # Control de zona de interés
                zona_interes_id = "602"
                zona_activa = zona_interes_activa.get(zona_interes_id, False)

                # Analítica YOLO (persona) - Optimización: Reducir frecuencia de detección
                if analitica_activa[self.canal_id] and (not zona_activa or self.canal_id == zona_interes_id):
                    if self.frame_count % self.frame_skip == 0:
                        try:
                            results = modelo_yolo(frame, verbose=False)
                            
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

                    # Dibujar detecciones si no es canal 602 con zona activa
                    if not (zona_activa and self.canal_id == zona_interes_id):
                        for box in self.last_detections:
                            x1, y1, x2, y2, conf = map(int, box)
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            cv2.putText(frame, "Persona Detectada", (x1, y1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                # Detección manos arriba solo si zona interés NO activa - Optimización: Reducir frecuencia
                if manos_arriba_activa[self.canal_id] and not zona_activa and (self.frame_count % 3 == 0):
                    try:
                        frame, detectado = detectar_manos_arriba(frame, guardar_captura=True, output_path=str(output_folder))
                        if detectado:
                            print(f"Canal {self.canal_id}: ¡Manos arriba detectadas!")
                    except Exception as e:
                        print(f"Error en detección manos arriba para cámara {self.canal_id}: {e}")

                # Zona de interés SOLO canal 602
                if self.canal_id == zona_interes_id and zona_activa:
                    try:
                        frame = procesar_zona_interes(frame, zona_interes_id, self.last_detections)
                    except Exception as e:
                        print(f"Error en zona de interés para cámara {self.canal_id}: {e}")

                # Detección rostros - Optimización: Procesamiento asíncrono
                if rostros_activa[self.canal_id] and (self.frame_count % 15 == 0):  # Cada 15 frames
                    try:
                        # Enviar frame a worker asíncrono sin bloquear el thread principal
                        if not rostros_queue.full():
                            frame_copy = frame.copy()
                            rostros_queue.put((self.canal_id, frame_copy), block=False)
                    except Exception as e:
                        print(f"Error al enviar frame para detección de rostros en cámara {self.canal_id}: {e}")

                # Actualizar frame en tiempo real
                frames[self.canal_id] = frame

                # Grabación - Optimización: Mejor manejo de errores
                if recording_flags[self.canal_id]:
                    if video_writers[self.canal_id] is None:
                        try:
                            filename = datetime.now().strftime(f"{self.canal_id}_%Y%m%d_%H%M%S.avi")
                            filepath = os.path.join(output_folder, filename)
                            fourcc = cv2.VideoWriter_fourcc(*'XVID')
                            h, w = frame.shape[:2]
                            video_writers[self.canal_id] = cv2.VideoWriter(filepath, fourcc, 30.0, (w, h))
                            print(f"🎥 Comenzó grabación para cámara {self.canal_id}")
                        except Exception as e:
                            print(f"Error al iniciar grabación para cámara {self.canal_id}: {e}")

                    if video_writers[self.canal_id] is not None:
                        try:
                            video_writers[self.canal_id].write(frame)
                        except Exception as e:
                            print(f"Error al escribir frame en grabación para cámara {self.canal_id}: {e}")
                else:
                    if video_writers[self.canal_id] is not None:
                        try:
                            video_writers[self.canal_id].release()
                            video_writers[self.canal_id] = None
                            print(f"Grabación detenida para cámara {self.canal_id}")
                        except Exception as e:
                            print(f"Error al detener grabación para cámara {self.canal_id}: {e}")

                # Snapshot
                if snapshot_flags[self.canal_id]:
                    try:
                        filename = datetime.now().strftime(f"{self.canal_id}_snapshot_%Y%m%d_%H%M%S.jpg")
                        filepath = os.path.join(output_folder, filename)
                        cv2.imwrite(filepath, frame)
                        print(f"📸 Snapshot guardado: {filepath}")
                        snapshot_flags[self.canal_id] = False
                    except Exception as e:
                        print(f"Error al guardar snapshot para cámara {self.canal_id}: {e}")
                        snapshot_flags[self.canal_id] = False

            cap.release()

            if video_writers[self.canal_id] is not None:
                try:
                    video_writers[self.canal_id].release()
                    video_writers[self.canal_id] = None
                except Exception as e:
                    print(f"Error al liberar video writer para cámara {self.canal_id}: {e}")

# Función de limpieza al cerrar
atexit.register(detener_rostros_worker)
