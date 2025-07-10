import socket
import pickle

class VMSCommandClient:
    def __init__(self, server_ip, port=9100):
        self.server_ip = server_ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.server_ip, self.port))

    def send_command(self, action, canal):
        cmd = {'action': action, 'canal': canal}
        data = pickle.dumps(cmd) + b'\n'
        self.sock.sendall(data)

    def close(self):
        self.sock.close()
