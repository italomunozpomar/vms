
import socket
import pickle
import struct
import cv2
from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np

class CamaraThreadTCP(QThread):
    frame_ready = pyqtSignal(str, object)  # Señal para enviar el frame procesado a la UI (np.ndarray RGB)

    def __init__(self, canal_id, server_ip, camera_ports):
        super().__init__()
        self.canal_id = canal_id
        self.server_ip = server_ip
        self.camera_ports = camera_ports
        self.running = True

    def run(self):
        try:
            port = self.camera_ports[self.canal_id]
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.server_ip, port))
            while self.running:
                # Recibe el tamaño del frame
                packed_size = b''
                while len(packed_size) < 4:
                    packed_size += s.recv(4 - len(packed_size))
                frame_size = struct.unpack('>I', packed_size)[0]
                # Recibe el frame
                data = b''
                while len(data) < frame_size:
                    packet = s.recv(frame_size - len(data))
                    if not packet:
                        break
                    data += packet
                frame = pickle.loads(data)
                img = cv2.imdecode(frame, 1)
                img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                self.frame_ready.emit(self.canal_id, img)
        except Exception as e:
            print(f"[TCP] Error en CamaraThreadTCP {self.canal_id}: {e}")
        finally:
            s.close()

    def stop(self):
        self.running = False
