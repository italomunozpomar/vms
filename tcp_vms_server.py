import socket
import threading
import cv2
import pickle
import struct
import numpy as np
# from config.config_manager import ConfigManager

# Configuración
SERVER_IP = '0.0.0.0'  # Escucha en todas las interfaces
CAMERA_PORTS = {
    '101': 9001,
    '501': 9002,
    '601': 9003,
    '901': 9004,
}
RTSP_BASE = "rtsp://admin:nunoa2018@192.168.67.63:554/Streaming/Channels/{}?tcp/"

def client_handler(conn, addr, camera_id):
    print(f"[INFO] Cliente conectado: {addr} para cámara {camera_id}")
    cap = cv2.VideoCapture(RTSP_BASE.format(camera_id))
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, f'Sin señal {camera_id}', (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
            _, buffer = cv2.imencode('.jpg', frame)
            data = pickle.dumps(buffer)
            conn.sendall(struct.pack('>I', len(data)) + data)
    except Exception as e:
        print(f"[ERROR] Cliente desconectado: {addr} - {e}")
    finally:
        cap.release()
        conn.close()

def start_camera_server(camera_id, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((SERVER_IP, port))
    s.listen(5)
    print(f"[INFO] Servidor TCP para cámara {camera_id} escuchando en puerto {port}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=client_handler, args=(conn, addr, camera_id), daemon=True).start()

def main():
    threads = []
    for cam, port in CAMERA_PORTS.items():
        t = threading.Thread(target=start_camera_server, args=(cam, port), daemon=True)
        t.start()
        threads.append(t)
    print("[INFO] Servidores TCP de cámaras iniciados.")
    for t in threads:
        t.join()

if __name__ == '__main__':
    main()
