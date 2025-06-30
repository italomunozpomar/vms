import requests
from requests.auth import HTTPDigestAuth
import xml.etree.ElementTree as ET
import os
from datetime import datetime
import threading
import pyodbc
from pathlib import Path
import time
import sys
sys.path.append(str(Path(__file__).parent.parent))
from config.settings import canales_originales

# Configuración de cámaras Hikvision - Todas las cámaras del sistema
HIKVISION_CAMERAS = [
    {"ip": "192.168.67.63", "username": "admin", "password": "nunoa2018", "canal": "101"},
    {"ip": "192.168.67.63", "username": "admin", "password": "nunoa2018", "canal": "501"},
    {"ip": "192.168.67.63", "username": "admin", "password": "nunoa2018", "canal": "601"},
    {"ip": "192.168.67.63", "username": "admin", "password": "nunoa2018", "canal": "901"},
]

# Parámetros de conexión a Azure SQL
DB_CONFIG = {
    "driver": "{ODBC Driver 18 for SQL Server}",
    "server": "datosestructurados.database.windows.net,1433",
    "database": "DatosEstructurados",
    "uid": "DBuser@DatosEstructurados",
    "pwd": "Contrasena123",
}

# Variables globales para comunicación con la UI
event_callbacks = []
event_threads = {}
event_running = False

# --- Mapeo manual directo de canal real a carpeta ---
def obtener_carpeta_canal(channel_real):
    """Asigna manualmente cada canal real a su carpeta específica"""
    canal_str = str(channel_real)
    
    # Mapeo manual directo
    if canal_str == "1":
        return "101"
    elif canal_str == "5":
        return "501"
    elif canal_str == "6":
        return "601"
    elif canal_str == "9":
        return "901"
    elif canal_str == "11":
        return "1101"
    else:
        # Si no está en el mapeo, usar el canal original
        return canal_str

# Reemplazar la función mapear_canal_logico
def mapear_canal_logico(channel_real):
    """Mapea el canal real al canal lógico usando asignación manual"""
    return obtener_carpeta_canal(channel_real)

def register_event_callback(callback):
    """Registra un callback para notificar eventos a la UI"""
    event_callbacks.append(callback)

def notify_event_to_ui(cam_ip, channel, event_type, event_desc, ruta_imagen):
    """Notifica un evento a todos los callbacks registrados"""
    if not event_callbacks:
        return
        
    for callback in event_callbacks:
        try:
            callback(cam_ip, channel, event_type, event_desc, ruta_imagen)
        except Exception as e:
            print(f"Error en callback de evento: {e}")
            # No remover el callback para evitar problemas de concurrencia

def descargar_snapshot_manual(cam_ip, username, password, timestamp, channel_id, folder):
    """Descarga snapshot manual de la cámara"""
    # 1. Intentar snapshot de alta calidad (System/picture)
    url_system_picture = f"http://{cam_ip}/ISAPI/System/picture/channels/{int(channel_id)}"
    nombre_archivo_system = os.path.join(
        folder,
        f"cam_{cam_ip.replace('.', '_')}_canal_{channel_id}_{timestamp.replace(':', '-')}_system.jpg"
    )
    exito_system = False
    try:
        response = requests.get(url_system_picture, auth=HTTPDigestAuth(username, password), stream=True, timeout=10)
        if response.status_code == 200 and response.headers.get('Content-Type', '').startswith('image'):
            with open(nombre_archivo_system, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Imagen alta calidad (system) descargada: {nombre_archivo_system}")
            exito_system = True
        else:
            print(f"No se pudo descargar snapshot system. Código HTTP: {response.status_code}")
    except Exception as e:
        print(f"Error al descargar snapshot system: {e}")

    # 2. Intentar snapshot estándar (Streaming/channels)
    canal_stream_principal = f"{int(channel_id)}01"
    snapshot_url = f"http://{cam_ip}/ISAPI/Streaming/channels/{canal_stream_principal}/picture"
    nombre_archivo_stream = os.path.join(
        folder,
        f"cam_{cam_ip.replace('.', '_')}_canal_{channel_id}_{timestamp.replace(':', '-')}_manual.jpg"
    )
    exito_stream = False
    try:
        response = requests.get(snapshot_url, auth=HTTPDigestAuth(username, password), stream=True, timeout=10)
        if response.status_code == 200 and response.headers.get('Content-Type', '').startswith('image'):
            with open(nombre_archivo_stream, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Imagen estándar descargada: {nombre_archivo_stream}")
            exito_stream = True
        else:
            print(f"No se pudo descargar snapshot manual. Código HTTP: {response.status_code}")
    except Exception as e:
        print(f"Error al descargar snapshot manual: {e}")

    if not exito_system and not exito_stream:
        print("No se pudo obtener ninguna imagen de snapshot.")
        return ""
    
    return nombre_archivo_system if exito_system else nombre_archivo_stream

def descargar_imagen_bkgurl(url, username, password, timestamp, channel_id, cam_ip, folder):
    """Descarga imagen desde bkgUrl"""
    nombre_archivo = os.path.join(
        folder,
        f"cam_{cam_ip.replace('.', '_')}_canal_{channel_id}_{timestamp.replace(':', '-')}_bkgurl.jpg"
    )
    try:
        response = requests.get(url, auth=HTTPDigestAuth(username, password), stream=True, timeout=10)
        if response.status_code == 200 and response.headers.get('Content-Type', '').startswith('image'):
            with open(nombre_archivo, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Imagen descargada desde bkgUrl: {nombre_archivo}")
            return nombre_archivo
        else:
            print(f"No se pudo descargar imagen desde bkgUrl. Código HTTP: {response.status_code}")
    except Exception as e:
        print(f"Error al descargar imagen desde bkgUrl: {e}")
    return ""

def insertar_evento_hikvision(event_time, cam_ip, channel, event_type, event_desc, ruta_imagen):
    """Inserta evento en la base de datos"""
    try:
        conn = pyodbc.connect(
            f"DRIVER={DB_CONFIG['driver']};SERVER={DB_CONFIG['server']};DATABASE={DB_CONFIG['database']};UID={DB_CONFIG['uid']};PWD={DB_CONFIG['pwd']}"
        )
        cursor = conn.cursor()
        query = '''
        INSERT INTO cam_hikvision (event_time, cam_ip, channel, event_type, event_desc, ruta_imagen)
        VALUES (?, ?, ?, ?, ?, ?)
        '''
        cursor.execute(query, (event_time, cam_ip, channel, event_type, event_desc, ruta_imagen))
        conn.commit()
        cursor.close()
        conn.close()
        print("Evento insertado en la base de datos")
    except Exception as e:
        print(f"Error al insertar en base de datos: {e}")

def escuchar_eventos_camara(cam):
    """Escucha eventos de una cámara específica"""
    global event_running
    
    EVENT_STREAM_URL = f"http://{cam['ip']}/ISAPI/Event/notification/alertStream"
    canal_especifico = cam.get('canal', 'N/A')
    print(f"Escuchando eventos desde {cam['ip']} canal {canal_especifico}...")
    
    # Crear estructura de carpetas organizada
    base_folder = Path("output")
    eventos_folder = base_folder / "eventos"
    eventos_folder.mkdir(parents=True, exist_ok=True)
    
    # Carpetas específicas por tipo de evento
    capturas_folder = eventos_folder / "capturas"
    capturas_folder.mkdir(exist_ok=True)
    
    log_file = eventos_folder / f"log_eventos_{cam['ip'].replace('.', '_')}_canal_{canal_especifico}.txt"
    NS = {'hk': 'http://www.hikvision.com/ver20/XMLSchema'}
    
    while event_running:
        try:
            response = requests.get(
                EVENT_STREAM_URL,
                auth=HTTPDigestAuth(cam["username"], cam["password"]),
                stream=True,
                timeout=60
            )
            if response.status_code != 200:
                print(f"ERROR: No se pudo conectar a {cam['ip']}: HTTP {response.status_code}")
                time.sleep(5)  # Esperar antes de reintentar
                continue

            buffer = ""
            for line in response.iter_lines():
                if not event_running:
                    break
                    
                if not line:
                    continue
                try:
                    decoded_line = line.decode("utf-8").strip()
                except Exception:
                    continue
                if decoded_line.startswith("<?xml") or "<EventNotificationAlert" in decoded_line:
                    buffer = decoded_line
                elif buffer:
                    buffer += decoded_line
                if decoded_line.endswith("</EventNotificationAlert>"):
                    try:
                        root = ET.fromstring(buffer)
                        event_type = root.findtext("hk:eventType", default="N/A", namespaces=NS)
                        channel = root.findtext("hk:dynChannelID", default=None, namespaces=NS)
                        if channel is None:
                            channel = root.findtext("hk:channelID", default="N/A", namespaces=NS)
                        event_time = root.findtext("hk:dateTime", default="N/A", namespaces=NS)
                        event_desc = root.findtext("hk:eventDescription", default="", namespaces=NS)
                        bkg_url = root.findtext("hk:bkgUrl", default=None, namespaces=NS)
                        
                        # Filtrar motion alert (solo mostrar mensaje, no guardar en BD)
                        if event_type == "videoloss":
                            continue
                        elif event_type == "motion" or event_type == "VMD":  # Agregar VMD también
                            print(f"MOVIMIENTO DETECTADO en cam {cam['ip']} canal {channel}")
                            # Usar canal_logico calculado desde el channel del evento
                            canal_logico = mapear_canal_logico(channel)
                            # Notificar a la UI para parpadear la cámara usando el canal lógico
                            try:
                                notify_event_to_ui(cam['ip'], canal_logico, "motion", "Movimiento detectado", "")
                            except Exception as e:
                                print(f"Error al notificar evento motion: {e}")
                            continue
                        
                        # Para otros eventos, procesar normalmente
                        print(f"Evento [{event_type}] en cam {cam['ip']} canal {channel} - Fecha: {event_time} - Desc: {event_desc}")
                        
                        # Guardar en log
                        try:
                            with open(log_file, "a", encoding="utf-8") as logf:
                                logf.write(f"{event_time} | cam: {cam['ip']} | canal: {channel} | tipo: {event_type} | desc: {event_desc} | bkgUrl: {bkg_url}\n")
                        except Exception as e:
                            print(f"Error al escribir en log: {e}")
                        
                        # 1. Mapear canal real a lógico
                        canal_logico = mapear_canal_logico(channel)
                        canal_real = str(channel)

                        # 2. Determinar carpeta por tipo de evento (estructura simplificada)
                        event_type_folder = "other"
                        if event_type.lower() in ["linecrossing", "linedetection"]:
                            event_type_folder = "linecrossing"
                        elif event_type.lower() in ["intrusion", "loitering"]:
                            event_type_folder = "intrusion"
                        elif event_type.lower() in ["face", "facedetection"]:
                            event_type_folder = "face"
                        elif event_type.lower() in ["motion", "vmd"]:
                            event_type_folder = "motion"

                        # 3. Carpeta destino
                        simple_folder = capturas_folder / event_type_folder
                        simple_folder.mkdir(parents=True, exist_ok=True)

                        # 4. Nombre de archivo robusto
                        # Ejemplo: cam_192_168_67_63_canalreal_1_canallogico_101_2025-06-30_14-42-27_linecrossing.jpg
                        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                        nombre_archivo = f"cam_{cam['ip'].replace('.', '_')}_canalreal_{canal_real}_canallogico_{canal_logico}_{timestamp}_{event_type_folder}.jpg"
                        ruta_imagen = str(simple_folder / nombre_archivo)

                        # 5. Descargar imagen y guardar en ruta_imagen
                        try:
                            if bkg_url:
                                response = requests.get(bkg_url, auth=HTTPDigestAuth(cam['username'], cam['password']), stream=True, timeout=10)
                                if response.status_code == 200 and response.headers.get('Content-Type', '').startswith('image'):
                                    with open(ruta_imagen, "wb") as f:
                                        for chunk in response.iter_content(chunk_size=8192):
                                            f.write(chunk)
                                    print(f"Imagen descargada desde bkgUrl: {ruta_imagen}")
                                else:
                                    print(f"No se pudo descargar imagen desde bkgUrl. Código HTTP: {response.status_code}")
                                    ruta_imagen = ""
                            else:
                                ruta_imagen = descargar_snapshot_manual(cam['ip'], cam['username'], cam['password'], timestamp, channel, simple_folder)
                        except Exception as e:
                            print(f"Error al descargar imagen: {e}")
                            ruta_imagen = ""

                        # 6. Insertar en BD y notificar a la UI como antes
                        try:
                            insertar_evento_hikvision(event_time, cam['ip'], channel, event_type, event_desc, ruta_imagen)
                        except Exception as e:
                            print(f"Error al insertar en BD: {e}")

                        try:
                            notify_event_to_ui(cam['ip'], canal_logico, event_type, event_desc, ruta_imagen)
                        except Exception as e:
                            print(f"Error al notificar evento a UI: {e}")
                        
                        buffer = ""
                    except ET.ParseError as e:
                        print(f"Error al parsear XML: {e}")
                        buffer = ""
                    except Exception as e:
                        print(f"Error general procesando evento: {e}")
                        buffer = ""
                        
        except requests.exceptions.RequestException as e:
            print(f"ERROR: Fallo al conectar a {cam['ip']}: {e}")
            time.sleep(5)  # Esperar antes de reintentar
        except Exception as e:
            print(f"ERROR general en thread de eventos para {cam['ip']}: {e}")
            time.sleep(5)  # Esperar antes de reintentar

def iniciar_eventos():
    """Inicia el sistema de eventos"""
    global event_running, event_threads
    
    event_running = True
    event_threads = {}
    
    for cam in HIKVISION_CAMERAS:
        # Crear un thread por cada cámara
        thread = threading.Thread(target=escuchar_eventos_camara, args=(cam,), daemon=True)
        thread.start()
        thread_key = f"{cam['ip']}_{cam.get('canal', 'N/A')}"
        event_threads[thread_key] = thread
        print(f"Sistema de eventos iniciado para cámara {cam['ip']} canal {cam.get('canal', 'N/A')}")

def detener_eventos():
    """Detiene el sistema de eventos"""
    global event_running
    event_running = False
    print("Sistema de eventos detenido")

# Función de limpieza al cerrar
import atexit
atexit.register(detener_eventos) 