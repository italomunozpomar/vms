import socket
import cv2
import pickle
import struct

# Cambia la IP al servidor VMS
SERVER_IP = '192.168.1.2'
SERVER_PORT = 9000

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((SERVER_IP, SERVER_PORT))

while True:
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
    cv2.imshow('VMS TCP Cliente', img)
    if cv2.waitKey(1) == 27:
        break
s.close()
cv2.destroyAllWindows()
