# Archivo: ui/window_grid.py

import os
import cv2
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QSizePolicy, QFrame, QTextEdit, QSplitter
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QPixmap, QImage, QColor, QIcon

from config.settings import (
    canales_originales, frames, analitica_activa,
    canales_activos, canales_baja, recording_flags,
    output_folder, manos_arriba_activa, rostros_activa
)
from core.hikvision_events import register_event_callback, iniciar_eventos, detener_eventos


class EventSignals(QObject):
    """Clase para manejar señales de eventos entre threads"""
    event_detected = pyqtSignal(str, str, str, str, str)  # cam_ip, channel, event_type, event_desc, ruta_imagen


class VMSGridWindow(QWidget):
    def __init__(self, camera_threads):
        super().__init__()
        self.setWindowTitle("VMS - Cámaras IP")
        self.camera_threads = camera_threads

        # Crear objeto de señales
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
        self.event_flash_timers = {}  # Timers para efectos de parpadeo
        self.event_log = []  # Lista de eventos recientes

        # Layout principal con splitter
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # Panel izquierdo con controles
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        left_panel.setFixedWidth(200)

        # Panel de botones
        control_layout = QVBoxLayout()
        control_layout.setAlignment(Qt.AlignTop)

        self.btn_record = QPushButton("  Grabar")
        self.btn_record.setIcon(QIcon.fromTheme("media-record"))
        self.btn_record.setToolTip("Iniciar/Detener grabación de la cámara seleccionada")

        self.btn_snapshot = QPushButton("  Snapshot")
        self.btn_snapshot.setIcon(QIcon.fromTheme("camera-photo"))
        self.btn_snapshot.setToolTip("Tomar una captura de la cámara seleccionada")

        self.btn_analitica = QPushButton("  Detección Personas")
        self.btn_analitica.setIcon(QIcon.fromTheme("user-identity"))
        self.btn_analitica.setToolTip("Activar/Desactivar detección de personas (YOLO)")

        self.btn_manos_arriba = QPushButton("  Manos Arriba")
        self.btn_manos_arriba.setIcon(QIcon.fromTheme("edit-undo"))
        self.btn_manos_arriba.setToolTip("Activar/Desactivar detección de manos arriba")

        self.btn_rostros = QPushButton("  Detección Rostros")
        self.btn_rostros.setIcon(QIcon.fromTheme("face-smile"))
        self.btn_rostros.setToolTip("Activar/Desactivar detección de rostros")

        for btn in [self.btn_record, self.btn_snapshot, self.btn_analitica,
                    self.btn_manos_arriba, self.btn_rostros]:
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

        # Panel de eventos
        events_label = QLabel("Eventos Recientes:")
        events_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        left_layout.addWidget(events_label)

        self.events_text = QTextEdit()
        self.events_text.setMaximumHeight(200)
        self.events_text.setReadOnly(True)
        self.events_text.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.events_text.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        left_layout.addWidget(self.events_text)

        left_layout.addStretch()
        main_layout.addWidget(left_panel)

        # Panel central con grid de cámaras
        self.grid = QGridLayout()
        self.grid.setSpacing(4)  # Espaciado sutil
        grid_container = QWidget()
        grid_container.setLayout(self.grid)
        grid_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        grid_container.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(grid_container)

        # Conexión de botones
        self.btn_record.clicked.connect(self.toggle_grabacion)
        self.btn_snapshot.clicked.connect(self.tomar_snapshot)
        self.btn_analitica.clicked.connect(self.toggle_analitica)
        self.btn_manos_arriba.clicked.connect(self.toggle_manos_arriba)
        self.btn_rostros.clicked.connect(self.toggle_rostros)

        # Crear labels para cada cámara
        for i, canal in enumerate(canales_originales):
            label = QLabel()
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet('''
                background-color: #232323;
                border: 1px solid #222;
                border-radius: 8px;
            ''')
            label.setFrameShape(QFrame.NoFrame)
            label.setLineWidth(0)
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            label.setMinimumSize(320, 180)
            label.mousePressEvent = lambda event, c=canal: self.seleccionar_camara(c)
            self.labels[canal] = label
            self.grid.addWidget(label, i // 2, i % 2)

        # Uniformar el tamaño de las celdas del grid
        num_filas = 2
        num_columnas = 2
        for i in range(num_filas):
            self.grid.setRowStretch(i, 1)
        for j in range(num_columnas):
            self.grid.setColumnStretch(j, 1)

        # Timer para actualizar frames
        self.timer = QTimer()
        self.timer.timeout.connect(self.actualizar_frames)
        self.timer.start(40)  # 25 FPS

        # Registrar callback para eventos usando la señal
        register_event_callback(self.event_callback_wrapper)

        # Iniciar sistema de eventos
        iniciar_eventos()

    def event_callback_wrapper(self, cam_ip, channel, event_type, event_desc, ruta_imagen):
        """Wrapper para enviar eventos a través de señales"""
        self.event_signals.event_detected.emit(cam_ip, channel, event_type, event_desc, ruta_imagen)

    def on_event_detected(self, cam_ip, channel, event_type, event_desc, ruta_imagen):
        """Callback para eventos detectados (ejecutado en thread principal)"""
        # El canal ya viene mapeado correctamente desde el sistema de eventos
        canal = channel
        
        # Agregar evento al log (al final para que aparezca primero)
        timestamp = datetime.now().strftime("%H:%M:%S")
        event_text = f"[{timestamp}] {event_type.upper()}: {event_desc} (Cámara {canal})"
        self.event_log.append(event_text)
        
        # Mantener solo los últimos 50 eventos
        if len(self.event_log) > 50:
            self.event_log.pop(0)
        
        # Verificar si el usuario está al final del scroll antes de actualizar
        scrollbar = self.events_text.verticalScrollBar()
        was_at_bottom = False
        if scrollbar:
            was_at_bottom = (scrollbar.value() >= scrollbar.maximum() - 10)  # 10 píxeles de tolerancia
        
        # Actualizar texto de eventos (mostrar los más recientes primero)
        eventos_ordenados = list(reversed(self.event_log))
        self.events_text.setText("\n".join(eventos_ordenados))
        
        # Solo hacer auto-scroll si el usuario estaba al final
        if was_at_bottom and scrollbar:
            scrollbar.setValue(scrollbar.maximum())
        
        # Efecto visual para la cámara específica
        if canal in self.labels:
            self.flash_camera_border(canal, event_type)
        else:
            print(f"Advertencia: Canal {canal} no encontrado en labels disponibles: {list(self.labels.keys())}")

    def flash_camera_border(self, canal, event_type):
        """Efecto de parpadeo en el borde de la cámara"""
        if canal not in self.labels:
            return
        # Detener timer existente si hay uno
        if canal in self.event_flash_timers:
            self.event_flash_timers[canal].stop()
        # Color según tipo de evento
        colors = {
            "motion": "#ff6600",
            "VMD": "#ff6600",
            "linecrossing": "#ff0000",
            "linedetection": "#ff0000",
            "intrusion": "#00bfff",
            "loitering": "#00bfff",
            "face": "#00ff00",
            "facedetection": "#00ff00",
            "other": "#ffffff"
        }
        color = colors.get(event_type.lower(), "#ffffff")
        label = self.labels[canal]
        # Solo cambiar el color del borde, no el grosor
        normal_style = '''
            background-color: #232323;
            border: 1px solid #222;
            border-radius: 8px;
        '''
        flash_style = f'''
            background-color: #232323;
            border: 1px solid {color};
            border-radius: 8px;
        '''
        def flash():
            label.setStyleSheet(flash_style)
            QTimer.singleShot(400, lambda: label.setStyleSheet(normal_style))
        flash()

    def seleccionar_camara(self, canal):
        if canal in self.selected_cameras:
            self.selected_cameras.remove(canal)
            self.labels[canal].setStyleSheet("background-color: black; border: 2px solid gray;")
        else:
            self.selected_cameras.add(canal)
            self.labels[canal].setStyleSheet("background-color: black; border: 2px solid blue;")

    def actualizar_frames(self):
        for canal in canales_originales:
            frame = frames.get(canal)
            if frame is None or frame.size == 0:
                continue

            # Crear una copia del frame para no modificar el original
            frame_display = frame.copy()
            
            texto = f"Cámara {canal}"
            estados = []
            if recording_flags[canal]:
                estados.append("Grabando: ON")
            if analitica_activa[canal]:
                estados.append("Personas: ON")
            if manos_arriba_activa[canal]:
                estados.append("Manos: ON")
            if rostros_activa[canal]:
                estados.append("Rostros: ON")

            if estados:
                texto += " | " + " | ".join(estados)

            cv2.putText(frame_display, texto, (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)

            # Optimización: Convertir a RGB solo una vez y cachear
            rgb = cv2.cvtColor(frame_display, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qt_image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            pix = QPixmap.fromImage(qt_image)

            label = self.labels[canal]
            # Optimización: Usar KeepAspectRatio en lugar de KeepAspectRatioByExpanding para mejor rendimiento
            pix_resized = pix.scaled(label.width(), label.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            label.setPixmap(pix_resized)

    def toggle_grabacion(self):
        for canal in self.selected_cameras:
            recording_flags[canal] = not recording_flags[canal]
            estado = "Grabando" if recording_flags[canal] else "Detenido"
            print(f"Grabación {estado} en cámara {canal}")

    def tomar_snapshot(self):
        for canal in self.selected_cameras:
            frame = frames[canal].copy()
            filename = datetime.now().strftime(f"{canal}_snapshot_%Y%m%d_%H%M%S.jpg")
            filepath = os.path.join(output_folder, filename)
            cv2.imwrite(filepath, frame)
            print(f"Snapshot guardado: {filepath}")

    def toggle_analitica(self):
        for canal in self.selected_cameras:
            analitica_activa[canal] = not analitica_activa[canal]
            canales_activos[canal] = canales_baja[canal] if analitica_activa[canal] else canal
            estado = "Detección Personas ON" if analitica_activa[canal] else "OFF"
            print(f"Analítica {estado} en cámara {canal}")

    def toggle_manos_arriba(self):
        for canal in self.selected_cameras:
            manos_arriba_activa[canal] = not manos_arriba_activa[canal]
            estado = "ON" if manos_arriba_activa[canal] else "OFF"
            print(f"Manos Arriba {estado} en cámara {canal}")

    def toggle_rostros(self):
        for canal in self.selected_cameras:
            rostros_activa[canal] = not rostros_activa[canal]
            estado = "ON" if rostros_activa[canal] else "OFF"
            print(f"Detección de rostros {estado} en cámara {canal}")

    def closeEvent(self, event):
        self.timer.stop()
        # Detener todos los timers de parpadeo
        for timer in self.event_flash_timers.values():
            timer.stop()
        # Detener sistema de eventos
        detener_eventos()
        event.accept()

    def mostrar_grid(self):
        self.show()
