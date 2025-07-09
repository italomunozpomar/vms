import socket
import threading
import cv2
import pickle
import struct
import numpy as np

# Configuración
SERVER_IP = '0.0.0.0'  # Escucha en todas las interfaces
SERVER_PORT = 9000
CAMERA_ID = '101'
RTSP_URL = "rtsp://admin:nunoa2018@192.168.67.63:554/Streaming/Channels/101?tcp/"

# Servidor TCP que envía frames JPEG continuamente
def client_handler(conn, addr):
    print(f"[INFO] Cliente conectado: {addr}")
    cap = cv2.VideoCapture(RTSP_URL)
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                frame = np.zeros((480, 640, 3), dtype=np.uint8)
                cv2.putText(frame, 'Sin señal', (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
            # Codifica el frame como JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            data = pickle.dumps(buffer)
            # Envia tamaño y datos
            conn.sendall(struct.pack('>I', len(data)) + data)
    except Exception as e:
        print(f"[ERROR] Cliente desconectado: {addr} - {e}")
    finally:
        cap.release()
        conn.close()

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((SERVER_IP, SERVER_PORT))
    s.listen(5)
    print(f"[INFO] Servidor VMS TCP escuchando en {SERVER_IP}:{SERVER_PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=client_handler, args=(conn, addr), daemon=True).start()

if __name__ == '__main__':
    main()
