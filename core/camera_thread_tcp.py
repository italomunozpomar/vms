
import socket
import pickle
import struct
import cv2
from PyQt5.QtCore import QThread, pyqtSignal
import numpy as np

class CamaraThreadTCP(QThread):
    frame_ready = pyqtSignal(str, object)  # Señal para enviar el frame procesado a la UI (np.ndarray RGB)

    def __init__(self, canal_id, server_ip, server_port):
        super().__init__()
        self.canal_id = canal_id
        self.server_ip = server_ip
        self.server_port = server_port
        self.running = True

    def run(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.server_ip, self.server_port))
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
                self.frame_ready.emit(self.canal_id, img)
        except Exception as e:
            print(f"[TCP] Error en CamaraThreadTCP {self.canal_id}: {e}")
        finally:
            s.close()

    def stop(self):
        self.running = False
