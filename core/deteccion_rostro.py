import os
import urllib.request
from datetime import datetime, timedelta
import cv2
import pyodbc
import threading
import queue
import time

# URLs para descargar los archivos del modelo
PROTO_TXT_URL = "https://raw.githubusercontent.com/opencv/opencv/master/samples/dnn/face_detector/deploy.prototxt"
MODEL_CAFFE_URL = "https://github.com/opencv/opencv_3rdparty/raw/dnn_samples_face_detector_20170830/res10_300x300_ssd_iter_140000.caffemodel"

PROTO_TXT_LOCAL = "core/deploy.prototxt"
MODEL_CAFFE_LOCAL = "core/res10_300x300_ssd_iter_140000.caffemodel"

# Crear carpeta de capturas si no existe
if not os.path.exists("output/rostros"):
    os.makedirs("output/rostros")

# Descargar los archivos si no existen
def descargar_archivo(url, destino):
    if not os.path.exists(destino):
        print(f"Descargando {url} ...")
        urllib.request.urlretrieve(url, destino)
        print(f"Guardado en {destino}")
    else:
        print(f"Archivo ya existe: {destino}")

descargar_archivo(PROTO_TXT_URL, PROTO_TXT_LOCAL)
descargar_archivo(MODEL_CAFFE_URL, MODEL_CAFFE_LOCAL)

# Cargar el modelo DNN una sola vez (cache)
print("Cargando modelo de detección de rostros...")
net = cv2.dnn.readNetFromCaffe(PROTO_TXT_LOCAL, MODEL_CAFFE_LOCAL)

# Intentar configurar el backend de CUDA para usar la GPU
try:
    print("Intentando configurar backend CUDA para DNN...")
    net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
    net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
    print("Backend CUDA configurado exitosamente. La detección de rostros usará la GPU.")
except Exception as e:
    print(f"No se pudo configurar el backend de CUDA para la GPU: {e}")
    print("La detección de rostros se ejecutará en la CPU.")

print("Modelo de rostros cargado")

# Conexión a SQL Server
conn_str = (
    "DRIVER={ODBC Driver 18 for SQL Server};"
    "SERVER=tcp:datosestructurados.database.windows.net,1433;"
    "DATABASE=DatosEstructurados;"
    "UID=DBuser@DatosEstructurados;"
    "PWD=Contrasena123;"
    "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
)

# Control de tiempo entre capturas
ultimo_registro = datetime.min

# Cola para procesamiento asíncrono de base de datos
db_queue = queue.Queue()
db_thread = None
db_running = False

def db_worker():
    """Worker thread para procesar inserciones de base de datos de forma asíncrona"""
    global db_running
    while db_running:
        try:
            data = db_queue.get(timeout=1)
            if data is None:
                break
            # Desempaquetar datos
            ahora, x, y, ancho, alto, confidence, rostro, filename = data
            try:
                # Guardar imagen
                cv2.imwrite(filename, rostro)
                print(f"Rostro capturado: {filename}")
                conn = pyodbc.connect(conn_str)
                cursor = conn.cursor()
                # Insertar en Detecciones
                cursor.execute("""
                    INSERT INTO Detecciones (fecha, hora, x, y, ancho, alto, score_confianza, en_zona_interes)
                    OUTPUT INSERTED.id_deteccion
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, ahora.date(), ahora.time(), int(x), int(y), int(ancho), int(alto), float(confidence), None)
                result = cursor.fetchone()
                if result is not None:
                    id_deteccion = result[0]
                    conn.commit()
                    # Insertar en Capturas
                    cursor.execute("""
                        INSERT INTO Capturas (id_deteccion_fk, timestamp, path_imagen, tipo_evento, descripcion_evento)
                        VALUES (?, ?, ?, ?, ?)
                    """, id_deteccion, ahora, filename, "Rostro detectado", "Captura automática con modelo DNN")
                    conn.commit()
                    print(f"Datos insertados en SQL Server para rostro: {filename}")
                else:
                    print(f"Error: No se obtuvo id_deteccion al insertar en Detecciones para {filename}")
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"Error en base de datos (async): {e}")
        except queue.Empty:
            continue
        except Exception as e:
            print(f"❌ Error en worker de base de datos: {e}")

def iniciar_db_worker():
    """Inicia el worker thread para base de datos"""
    global db_thread, db_running
    if db_thread is None or not db_thread.is_alive():
        db_running = True
        db_thread = threading.Thread(target=db_worker, daemon=True)
        db_thread.start()
        print("Worker de base de datos iniciado")

def detener_db_worker():
    """Detiene el worker thread de base de datos"""
    global db_running
    db_running = False
    if db_thread and db_thread.is_alive():
        db_queue.put(None)  # Señal de parada
        db_thread.join(timeout=2)
        print("Worker de base de datos detenido")

# Iniciar worker al importar el módulo
iniciar_db_worker()

def detectar_rostros(frame, conf_threshold=0.5):
    global ultimo_registro

    (h, w) = frame.shape[:2]
    blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300), (104.0, 177.0, 123.0))
    net.setInput(blob)
    detections = net.forward()

    ahora = datetime.now()
    rostros_detectados = []

    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]
        if confidence > conf_threshold:
            box = detections[0, 0, i, 3:7] * [w, h, w, h]
            x, y, x2, y2 = box.astype("int")
            ancho = x2 - x
            alto = y2 - y
            if ancho < 40 or alto < 40:
                continue
            cv2.rectangle(frame, (x, y), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{confidence:.2f}", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
            # Solo enviar a la cola si han pasado 5 segundos desde la última captura
            if (ahora - ultimo_registro) > timedelta(seconds=5):
                rostro = frame[y:y+alto, x:x+ancho].copy()
                filename = f"output/rostros/rostro_detectado_{ahora.strftime('%Y%m%d_%H%M%S')}.jpg"
                # Enviar todo a la cola para que el thread asíncrono lo procese
                db_queue.put((ahora, x, y, ancho, alto, confidence, rostro, filename))
                ultimo_registro = ahora
    return frame

# Función de limpieza al cerrar
import atexit
atexit.register(detener_db_worker)
