import cv2
import threading
import time
from flask import Flask, Response, jsonify, request
import os
import importlib.util
import numpy as np

from flask import send_file
app = Flask(__name__)
# --- Servir el cliente web en la raíz ---
@app.route('/')
def index():
    # Sirve el archivo webui_client.html desde el mismo directorio del script
    return send_file(os.path.join(os.path.dirname(__file__), 'webui_client.html'))

# --- Configuración de cámaras ---
CAMERA_IDS = ['101', '501', '601', '901']
RTSP_BASE = "rtsp://admin:nunoa2018@192.168.67.63:554/Streaming/Channels/{}?tcp/"
CAMERA_STREAMS = {cam: RTSP_BASE.format(cam) for cam in CAMERA_IDS}

# --- Estado de analíticas, grabación, etc. (simulado) ---
camera_status = {cam: {'grabando': False, 'analitica': False, 'manos_arriba': False, 'rostros': False} for cam in CAMERA_IDS}

# --- Video Streaming MJPEG con overlays (simulado) ---
def gen_frames(camera_id):
    src = CAMERA_STREAMS.get(camera_id)
    cap = cv2.VideoCapture(src)
    while True:
        success, frame = cap.read()
        if not success:
            frame = cv2.putText(
                np.zeros((480, 640, 3), dtype=np.uint8),
                f"Sin señal {camera_id}", (50, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2, cv2.LINE_AA)
        # Overlay de estado
        status = camera_status.get(camera_id, {})
        y = 30
        for key, label, color in [
            ('grabando', 'REC', (0,0,255)),
            ('analitica', 'ANALYTICS', (0,255,255)),
            ('manos_arriba', 'MANOS', (255,255,0)),
            ('rostros', 'ROSTROS', (0,255,0))]:
            if status.get(key):
                cv2.putText(frame, label, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2, cv2.LINE_AA)
                y += 40
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(1/15)
    cap.release()

@app.route('/video_feed/<camera_id>')
def video_feed(camera_id):
    if camera_id not in CAMERA_STREAMS:
        return "Cámara no encontrada", 404
    return Response(gen_frames(camera_id), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/status')
def status():
    return jsonify(camera_status)

@app.route('/action', methods=['POST'])
def action():
    data = request.get_json()
    action = data.get('action')
    cameras = data.get('cameras', [])
    for cam in cameras:
        if cam not in camera_status:
            continue
        if action == 'toggle_grabacion':
            camera_status[cam]['grabando'] = not camera_status[cam]['grabando']
        elif action == 'toggle_analitica':
            camera_status[cam]['analitica'] = not camera_status[cam]['analitica']
        elif action == 'toggle_manos_arriba':
            camera_status[cam]['manos_arriba'] = not camera_status[cam]['manos_arriba']
        elif action == 'toggle_rostros':
            camera_status[cam]['rostros'] = not camera_status[cam]['rostros']
    return jsonify({'status': 'ok', 'status_data': {cam: camera_status[cam] for cam in cameras}})

@app.route('/events')
def get_events():
    # Simulación de eventos
    return jsonify([f"[2025-07-09 15:00:00] MOTION: Movimiento detectado (Cámara {cam})" for cam in CAMERA_IDS])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
