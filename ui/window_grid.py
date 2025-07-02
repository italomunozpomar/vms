import os
import cv2
from datetime import datetime
from PyQt5.QtWidgets import(
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QSizePolicy, QFrame, QTextEdit, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QImage, QColor, QIcon
import time # Importar el módulo time

from config import config_manager
from core.hikvision_events import register_event_callback, iniciar_eventos, detener_eventos


class EventSignals(QObject):
    """Clase para manejar señales de eventos entre threads"""
    event_detected = pyqtSignal(str, str, str, str, str)  # cam_ip, channel, event_type, event_desc, ruta_imagen


class VMSGridWindow(QWidget):
    def __init__(self, camera_threads):
        super().__init__()
        self.setWindowTitle("VMS - Cámaras IP")
        self.camera_threads = camera_threads

        self.event_signals = EventSignals()
        self.event_signals.event_detected.connect(self.on_event_detected)

        self.setStyleSheet("""
            QWidget {
                background-color: #121212;
                color: white;
            }
            QPushButton {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #444;
            }
            QTextEdit {
                background-color: #1a1a1a;
                color: #00ff00;
                border: 1px solid #555;
                font-family: 'Consolas', monospace;
                font-size: 10px;
            }
        """)

        self.labels = {}
        self.selected_cameras = set()
        self.event_flash_timers = {}
        self.event_log = []

        # Variables para cálculo de FPS de visualización
        self.display_fps_start_time = time.time()
        self.display_fps_frame_count = 0

        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        left_panel.setFixedWidth(200)

        control_layout = QVBoxLayout()
        control_layout.setAlignment(Qt.AlignTop)

        self.btn_record = QPushButton("  Grabar")
        self.btn_snapshot = QPushButton("  Snapshot")
        self.btn_analitica = QPushButton("  Detección Personas")
        self.btn_manos_arriba = QPushButton("  Manos Arriba")
        self.btn_rostros = QPushButton("  Detección Rostros")

        buttons = {
            self.btn_record: ("media-record", "Iniciar/Detener grabación de la cámara seleccionada"),
            self.btn_snapshot: ("camera-photo", "Tomar una captura de la cámara seleccionada"),
            self.btn_analitica: ("user-identity", "Activar/Desactivar detección de personas (YOLO)"),
            self.btn_manos_arriba: ("edit-undo", "Activar/Desactivar detección de manos arriba"),
            self.btn_rostros: ("face-smile", "Activar/Desactivar detección de rostros")
        }

        for btn, (icon, tooltip) in buttons.items():
            btn.setIcon(QIcon.fromTheme(icon))
            btn.setToolTip(tooltip)
            btn.setFixedHeight(40)
            btn.setMinimumWidth(150)
            btn.setStyleSheet('''
                QPushButton {
                    background-color: #222;
                    color: #fff;
                    border-radius: 10px;
                    border: 2px solid #444;
                    font-size: 15px;
                    font-weight: bold;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #444;
                    border: 2px solid #00bfff;
                    color: #00bfff;
                }
            ''')
            control_layout.addWidget(btn)

        left_layout.addLayout(control_layout)

        events_label = QLabel("Eventos Recientes:")
        events_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        left_layout.addWidget(events_label)

        self.events_text = QTextEdit()
        self.events_text.setMaximumHeight(200)
        self.events_text.setReadOnly(True)
        left_layout.addWidget(self.events_text)

        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        self.grid = QGridLayout()
        self.grid.setSpacing(4)
        grid_container = QWidget()
        grid_container.setLayout(self.grid)
        main_layout.addWidget(grid_container)

        self.btn_record.clicked.connect(self.toggle_grabacion)
        self.btn_snapshot.clicked.connect(self.tomar_snapshot)
        self.btn_analitica.clicked.connect(self.toggle_analitica)
        self.btn_manos_arriba.clicked.connect(self.toggle_manos_arriba)
        self.btn_rostros.clicked.connect(self.toggle_rostros)

        for i, canal in enumerate(config_manager.canales_originales):
            label = QLabel()
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet('''
                background-color: #232323;
                border: 2px solid #222; /* Borde inicial de 2px */
                border-radius: 8px;
            ''')
            label.setFrameShape(QFrame.NoFrame)
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            label.setMinimumSize(320, 180)
            label.mousePressEvent = lambda event, c=canal: self.seleccionar_camara(c)
            self.labels[canal] = label
            self.grid.addWidget(label, i // 2, i % 2)

        for canal, thread in self.camera_threads.items():
            thread.frame_ready.connect(self.update_frame)

        register_event_callback(self.event_callback_wrapper)
        iniciar_eventos()

    def event_callback_wrapper(self, cam_ip, channel, event_type, event_desc, ruta_imagen):
        self.event_signals.event_detected.emit(cam_ip, channel, event_type, event_desc, ruta_imagen)

    def on_event_detected(self, cam_ip, channel, event_type, event_desc, ruta_imagen):
        canal = channel
        timestamp = datetime.now().strftime("%H:%M:%S")
        event_text = f"[{timestamp}] {event_type.upper()}: {event_desc} (Cámara {canal})"
        self.event_log.append(event_text)
        if len(self.event_log) > 50:
            self.event_log.pop(0)
        
        self.events_text.setText("\n".join(reversed(self.event_log)))
        self.events_text.verticalScrollBar().setValue(self.events_text.verticalScrollBar().maximum())
        
        if canal in self.labels:
            self.flash_camera_border(canal, event_type)

    def flash_camera_border(self, canal, event_type):
        if canal not in self.labels: return
        if canal in self.event_flash_timers: self.event_flash_timers[canal].stop()
        
        colors = {"motion": "#ff6600", "linecrossing": "#ff0000", "intrusion": "#00bfff"}
        color = colors.get(event_type.lower(), "#ffffff")
        label = self.labels[canal]
        
        normal_style = "background-color: #232323; border: 2px solid #222; border-radius: 8px;"
        flash_style = f"background-color: #232323; border: 2px solid {color}; border-radius: 8px;"
        
        label.setStyleSheet(flash_style)
        QTimer.singleShot(400, lambda: label.setStyleSheet(normal_style))

    def seleccionar_camara(self, canal):
        if canal in self.selected_cameras:
            self.selected_cameras.remove(canal)
            self.labels[canal].setStyleSheet("""
                background-color: #232323;
                border: 2px solid #222;
                border-radius: 8px;
            """)
        else:
            self.selected_cameras.add(canal)
            self.labels[canal].setStyleSheet("""
                background-color: #232323;
                border: 2px solid #00bfff; /* Azul brillante para selección */
                border-radius: 8px;
            """)

    def update_frame(self, canal_id, pixmap):
        if canal_id in self.labels:
            label = self.labels[canal_id]
            pixmap_resized = pixmap.scaled(label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pixmap_resized)

    def toggle_grabacion(self):
        for canal in self.selected_cameras:
            is_recording = config_manager.toggle_recording(canal)
            print(f"Grabación {'ON' if is_recording else 'OFF'} en cámara {canal}")

    def tomar_snapshot(self):
        for canal in self.selected_cameras:
            config_manager.take_snapshot(canal)
            print(f"Snapshot solicitado para cámara {canal}")

    def toggle_analitica(self):
        for canal in self.selected_cameras:
            is_active = config_manager.toggle_analytics(canal)
            print(f"Detección de Personas {'ON' if is_active else 'OFF'} en cámara {canal}")

    def toggle_manos_arriba(self):
        for canal in self.selected_cameras:
            is_active = config_manager.toggle_hands_up(canal)
            print(f"Detección Manos Arriba {'ON' if is_active else 'OFF'} en cámara {canal}")

    def toggle_rostros(self):
        for canal in self.selected_cameras:
            is_active = config_manager.toggle_face_detection(canal)
            print(f"Detección de Rostros {'ON' if is_active else 'OFF'} en cámara {canal}")

    def closeEvent(self, event):
        self.timer.stop()
        for timer in self.event_flash_timers.values():
            timer.stop()
        detener_eventos()
        config_manager.set_stop_flag() # Asegurarse de que los hilos se detengan
        event.accept()

    def mostrar_grid(self):
        self.show()

