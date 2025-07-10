import socket
import threading
import pickle
import queue
from config.config_manager import config_manager

COMMAND_PORT = 9100
SERVER_IP = '0.0.0.0'

# Cola para comandos recibidos
command_queue = queue.Queue()

def handle_command(conn, addr):
    print(f"[CMD] Cliente de comandos conectado: {addr}")
    try:
        while True:
            data = b''
            while True:
                packet = conn.recv(4096)
                if not packet:
                    break
                data += packet
                if data.endswith(b'\n'):
                    break
            if not data:
                break
            try:
                cmd = pickle.loads(data[:-1])
                print(f"[CMD] Recibido: {cmd}")
                command_queue.put(cmd)
            except Exception as e:
                print(f"[CMD] Error al decodificar comando: {e}")
    except Exception as e:
        print(f"[CMD] Error en conexión de comandos: {e}")
    finally:
        conn.close()

def command_server():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((SERVER_IP, COMMAND_PORT))
    s.listen(5)
    print(f"[CMD] Servidor de comandos escuchando en puerto {COMMAND_PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_command, args=(conn, addr), daemon=True).start()

def process_commands():
    while True:
        cmd = command_queue.get()
        if not isinstance(cmd, dict):
            continue
        action = cmd.get('action')
        canal = cmd.get('canal')
        print(f"[CMD] Ejecutando acción: {action} en cámara {canal}")
        # Aquí se activa/desactiva la analítica, grabación, etc. usando config_manager
        if action == 'toggle_rostros':
            current = config_manager.get_rostros_activa(canal)
            config_manager.set_rostros_activa(canal, not current)
        elif action == 'toggle_analitica':
            current = config_manager.get_analitica_activa(canal)
            config_manager.set_analitica_activa(canal, not current)
        elif action == 'toggle_grabacion':
            current = config_manager.get_recording_flag(canal)
            config_manager.set_recording_flag(canal, not current)
        elif action == 'toggle_manos_arriba':
            current = config_manager.get_manos_arriba_activa(canal)
            config_manager.set_manos_arriba_activa(canal, not current)
        elif action == 'snapshot':
            config_manager.set_snapshot_flag(canal, True)
        # Agrega más acciones según sea necesario

if __name__ == '__main__':
    threading.Thread(target=command_server, daemon=True).start()
    process_commands()
