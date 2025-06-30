# Archivo: core/zona_interes.py

import cv2
import numpy as np
from datetime import datetime
import pyodbc
import os

# Conexión a SQL Server Azure
def conectar_sql():
    conn_str = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=tcp:datosestructurados.database.windows.net,1433;"
        "DATABASE=DatosEstructurados;"
        "UID=DBuser@DatosEstructurados;"
        "PWD=Contrasena123;"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
    )
    return pyodbc.connect(conn_str)

# Zona rectangular de interés (solo para cámara 602)
zona_interes = (180, 95, 446, 304)
class_id = 0

if not os.path.exists("output/captures"):   
    os.makedirs("output/captures") 

last_detections = []
prev_zona_flags = []
captura_flags = []

def box_center(box):
    x1, y1, x2, y2 = box[:4]
    return ((x1 + x2) / 2, (y1 + y2) / 2)

def distance(p1, p2):
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

def esta_en_zona(cx, cy, zona):
    x1, y1, x2, y2 = zona
    return x1 <= cx <= x2 and y1 <= cy <= y2

def match_and_smooth(old_boxes, new_boxes, alpha=0.5, dist_threshold=50):
    if len(old_boxes) == 0:
        return new_boxes, [False] * len(new_boxes)
    matched_old = set()
    smoothed_boxes = []
    zona_flags = []
    old_centers = [box_center(b) for b in old_boxes]
    new_centers = [box_center(b) for b in new_boxes]

    for new_idx, new_box in enumerate(new_boxes):
        best_match = None
        best_dist = float('inf')
        for old_idx, old_box in enumerate(old_boxes):
            if old_idx in matched_old:
                continue
            dist = distance(new_centers[new_idx], old_centers[old_idx])
            if dist < best_dist and dist < dist_threshold:
                best_dist = dist
                best_match = old_idx
        if best_match is not None:
            old_box = old_boxes[best_match]
            sm_box = [o * (1 - alpha) + n * alpha for o, n in zip(old_box[:4], new_box[:4])]
            sm_box.append(new_box[4])
            smoothed_boxes.append(sm_box)
            matched_old.add(best_match)
        else:
            smoothed_boxes.append(new_box)

    for box in smoothed_boxes:
        cx, cy = box_center(box)
        zona_flags.append(esta_en_zona(cx, cy, zona_interes))

    return smoothed_boxes, zona_flags

def procesar_zona_interes(frame, canal_id, detecciones_yolo):
    global last_detections, prev_zona_flags, captura_flags

    if canal_id != "602":
        return frame

    detections = detecciones_yolo  # ← Reutilizamos las detecciones del hilo

    last_detections, zona_flags = match_and_smooth(last_detections, detections, alpha=0.3, dist_threshold=60)

    now = datetime.now()
    id_detecciones_actuales = []

    if len(prev_zona_flags) != len(zona_flags):
        prev_zona_flags = [False] * len(zona_flags)
        captura_flags = [False] * len(zona_flags)

    try:
        conn = conectar_sql()
        cursor = conn.cursor()

        for i, det in enumerate(last_detections):
            x1, y1, x2, y2, score = det
            w, h = x2 - x1, y2 - y1
            cx, cy = box_center(det)
            zona_flag = esta_en_zona(cx, cy, zona_interes)

            cursor.execute("""
                INSERT INTO Detecciones (fecha, hora, x, y, ancho, alto, score_confianza, en_zona_interes)
                OUTPUT INSERTED.id_deteccion
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, now.date(), now.time(), int(x1), int(y1), int(w), int(h), float(score), int(zona_flag))
            id_insertado = cursor.fetchone()[0]
            id_detecciones_actuales.append(id_insertado)
            conn.commit()

            ahora_en_zona = zona_flags[i]
            antes_en_zona = prev_zona_flags[i] if i < len(prev_zona_flags) else False

            if ahora_en_zona and not antes_en_zona and not captura_flags[i]:
                capture_filename = f"captures/captura_{now.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
                cv2.imwrite(capture_filename, frame)
                print(f"Captura realizada: {capture_filename}")
                captura_flags[i] = True

                if id_insertado is not None:
                    cursor.execute("""
                        INSERT INTO Capturas (id_deteccion_fk, timestamp, path_imagen, tipo_evento, descripcion_evento)
                        VALUES (?, ?, ?, ?, ?)
                    """, id_insertado, now, capture_filename, "Entrada a zona", "Captura por entrada a zona de interés")
                    conn.commit()

        for i in range(len(captura_flags)):
            if prev_zona_flags[i] and not zona_flags[i]:
                captura_flags[i] = False

        prev_zona_flags = zona_flags.copy()

    except Exception as e:
        print("Error en base de datos zona_interes:", e)

    for det in last_detections:
        x1, y1, x2, y2, score = det
        x1, y1, x2, y2 = map(int, [x1, y1, x2, y2])
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, "Persona", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    x1z, y1z, x2z, y2z = zona_interes
    cv2.rectangle(frame, (x1z, y1z), (x2z, y2z), (255, 0, 0), 2)
    cv2.putText(frame, "Zona Interés", (x1z, y1z - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

    return frame
