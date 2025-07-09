import sys
import requests
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QListWidget, QMessageBox
from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtCore import QTimer, Qt
import io

# Cambia esta IP a la de tu servidor VMS
SERVER = 'http://192.168.1.2:5000'

class VMSClient(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('VMS Cliente Escritorio')
        self.setGeometry(100, 100, 900, 600)
        self.cameras = []
        self.selected = None
        self.init_ui()
        self.update_cameras()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(80)  # ~12 fps
        self.event_timer = QTimer()
        self.event_timer.timeout.connect(self.update_events)
        self.event_timer.start(2000)

    def init_ui(self):
        layout = QHBoxLayout()
        # Sidebar
        sidebar = QVBoxLayout()
        self.list_cams = QListWidget()
        self.list_cams.clicked.connect(self.select_camera)
        sidebar.addWidget(QLabel('Cámaras disponibles:'))
        sidebar.addWidget(self.list_cams)
        self.btn_record = QPushButton('Grabar')
        self.btn_analitica = QPushButton('Detección Personas')
        self.btn_manos = QPushButton('Manos Arriba')
        self.btn_rostros = QPushButton('Detección Rostros')
        for btn, action in [
            (self.btn_record, 'toggle_grabacion'),
            (self.btn_analitica, 'toggle_analitica'),
            (self.btn_manos, 'toggle_manos_arriba'),
            (self.btn_rostros, 'toggle_rostros')]:
            btn.clicked.connect(lambda _, a=action: self.send_action(a))
            sidebar.addWidget(btn)
        sidebar.addStretch()
        self.events = QListWidget()
        sidebar.addWidget(QLabel('Eventos recientes:'))
        sidebar.addWidget(self.events)
        layout.addLayout(sidebar, 1)
        # Video
        video_layout = QVBoxLayout()
        self.label_cam = QLabel('Selecciona una cámara')
        self.label_cam.setAlignment(Qt.AlignCenter)
        self.video = QLabel()
        self.video.setAlignment(Qt.AlignCenter)
        self.video.setFixedSize(640, 360)
        video_layout.addWidget(self.label_cam)
        video_layout.addWidget(self.video)
        layout.addLayout(video_layout, 3)
        self.setLayout(layout)

    def update_cameras(self):
        try:
            r = requests.get(SERVER + '/status', timeout=3)
            status = r.json()
            self.cameras = list(status.keys())
            self.list_cams.clear()
            for cam in self.cameras:
                st = status[cam]
                txt = f"{cam} - " + ' | '.join([k.upper() for k, v in st.items() if v])
                self.list_cams.addItem(txt)
        except Exception as e:
            self.list_cams.clear()
            self.list_cams.addItem('No se pudo conectar al servidor')

    def select_camera(self):
        idx = self.list_cams.currentRow()
        if idx >= 0 and idx < len(self.cameras):
            self.selected = self.cameras[idx]
            self.label_cam.setText(f'Cámara {self.selected}')
        else:
            self.selected = None
            self.label_cam.setText('Selecciona una cámara')

    def update_frame(self):
        if not self.selected:
            self.video.clear()
            return
        try:
            url = f"{SERVER}/video_feed/{self.selected}"
            r = requests.get(url, stream=True, timeout=2)
            for chunk in r.iter_content(chunk_size=1024):
                if b'Content-Type: image/jpeg' in chunk:
                    img_data = b''
                if chunk.startswith(b'\xff\xd8'):
                    img_data = chunk
                elif chunk.endswith(b'\xff\xd9'):
                    img_data += chunk
                    break
                else:
                    img_data += chunk
            image = QImage.fromData(img_data)
            pixmap = QPixmap.fromImage(image)
            self.video.setPixmap(pixmap.scaled(self.video.size(), Qt.KeepAspectRatio))
        except Exception:
            self.video.clear()

    def send_action(self, action):
        if not self.selected:
            QMessageBox.warning(self, 'Error', 'Selecciona una cámara')
            return
        try:
            r = requests.post(SERVER + '/action', json={'action': action, 'cameras': [self.selected]}, timeout=2)
            if r.status_code == 200:
                self.update_cameras()
            else:
                QMessageBox.warning(self, 'Error', 'No se pudo enviar la acción')
        except Exception:
            QMessageBox.warning(self, 'Error', 'No se pudo conectar al servidor')

    def update_events(self):
        try:
            r = requests.get(SERVER + '/events', timeout=2)
            events = r.json()
            self.events.clear()
            for ev in events[::-1]:
                self.events.addItem(ev)
        except Exception:
            self.events.clear()
            self.events.addItem('No se pudo obtener eventos')

if __name__ == '__main__':
    app = QApplication(sys.argv)
    win = VMSClient()
    win.show()
    sys.exit(app.exec_())
