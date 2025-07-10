import os
import cv2
import time
from datetime import datetime
import numpy as np

from PyQt5.QtWidgets import (
    QWidget, QPushButton, QVBoxLayout, QHBoxLayout,
    QGridLayout, QSizePolicy, QFrame, QTextEdit, QSplitter, QTabWidget, QLabel
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QObject, QRect
from PyQt5.QtGui import QPixmap, QImage, QColor, QIcon, QPainter

from ui.opengl_video_widget import OpenGLVideoWidget
from ui.playback_panel import PlaybackPanel
from config import config_manager
from core.command_client import VMSCommandClient
from core.hikvision_events import register_event_callback, iniciar_eventos, detener_eventos
# from core.camera_thread import BUFFER_SIZE_SECONDS, POST_EVENT_RECORD_SECONDS # Ya no se importan de camera_thread, ahora vienen de config_manager


class CameraLabel(QFrame):
    def __init__(self, canal_id, parent=None):
        super().__init__(parent)
        self.canal_id = canal_id
        self.setFrameShape(QFrame.StyledPanel)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)

        self.base_style = """
            background-color: #232323;
            border: 2px solid #222;
            border-radius: 8px;
        """
        self.selected_style = """
            background-color: #232323;
            border: 2px solid #00bfff;
            border-radius: 8px;
        """
        self.hover_style = """
            background-color: #282828;
            border: 2px solid #555;
            border-radius: 8px;
        """
        self.setStyleSheet(self.base_style)
        self.is_selected = False
        self.event_flash_timer = QTimer(self)
        self.event_flash_timer.setSingleShot(True)
        self.event_flash_timer.timeout.connect(self._reset_style_after_flash)

        # Layout para que el OpenGLWidget ocupe todo el espacio
        self.setContentsMargins(0, 0, 0, 0)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.opengl_widget = OpenGLVideoWidget(self)
        self.opengl_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.layout.addWidget(self.opengl_widget, stretch=1)

        # Overlays: solo se crean, no se agregan al layout
        self.camera_id_label = QLabel(f"Cámara {self.canal_id}", self)
        self.camera_id_label.setStyleSheet("color: white; font-weight: bold; background-color: rgba(0,0,0,100); padding: 2px;")
        self.camera_id_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.camera_id_label.setFixedHeight(22)
        self.camera_id_label.raise_()

        self.analytics_status_label = QLabel("", self)
        self.analytics_status_label.setStyleSheet("color: #00ff00; background-color: rgba(0,0,0,100); padding: 2px;")
        self.analytics_status_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.analytics_status_label.setFixedHeight(20)
        self.analytics_status_label.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Posicionar overlays: id arriba izquierda, status abajo izquierda
        margin = 8
        self.camera_id_label.move(margin, margin)
        self.camera_id_label.resize(self.width() // 2, self.camera_id_label.height())
        self.analytics_status_label.move(margin, self.height() - self.analytics_status_label.height() - margin)
        self.analytics_status_label.resize(self.width() // 2, self.analytics_status_label.height())

    def update_analytics_status(self, status_text):
        self.analytics_status_label.setText(status_text)

    def set_selected(self, selected):
        self.is_selected = selected
        self._update_style()

    def flash_border(self, event_type):
        colors = {"motion": "#ff6600", "linecrossing": "#ff0000", "intrusion": "#00bfff"}
        color = colors.get(event_type.lower(), "#ffffff")
        flash_style = f"background-color: #232323; border: 2px solid {color}; border-radius: 8px;"
        self.setStyleSheet(flash_style)
        self.event_flash_timer.start(400)

    def _reset_style_after_flash(self):
        self._update_style()

    def _update_style(self):
        if self.is_selected:
            self.setStyleSheet(self.selected_style)
        else:
            self.setStyleSheet(self.base_style)

    def enterEvent(self, event):
        if not self.is_selected:
            self.setStyleSheet(self.hover_style)
        super().enterEvent(event)

    def leaveEvent(self, event):
        if not self.is_selected:
            self.setStyleSheet(self.base_style)
        super().leaveEvent(event)

    def set_frame(self, frame: np.ndarray):
        self.opengl_widget.set_frame(frame)


class EventSignals(QObject):
    """Clase para manejar señales de eventos entre threads"""
    event_detected = pyqtSignal(str, str, str, str, str)  # cam_ip, channel, event_type, event_desc, ruta_imagen


class VMSGridWindow(QWidget):
    def __init__(self, camera_threads):
        super().__init__()
        self.setWindowTitle("VMS - Cámaras IP")
        self.camera_threads = camera_threads
        self.setMinimumSize(1280, 720) # Set a minimum size for the main window

        # Configura el cliente de comandos TCP (ajusta IP si es necesario)
        self.command_client = VMSCommandClient(server_ip="127.0.0.1", port=9100)

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
            QTabWidget::pane {
                border-top: 2px solid #333;
            }
            QTabBar::tab {
                background: #232323;
                color: white;
                padding: 8px 20px;
                border: 1px solid #333;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected, QTabBar::tab:hover {
                background: #333;
                color: #00bfff;
            }
        """)

        self.labels = {}
        self.selected_cameras = set()
        self.event_flash_timers = {}
        self.event_log = []

        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        # Crear el splitter principal
        self.main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.main_splitter)

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
        self.main_splitter.addWidget(left_panel)

        # Crear el QTabWidget
        self.tab_widget = QTabWidget()
        self.main_splitter.addWidget(self.tab_widget)

        # Pestaña de Cámaras en Vivo
        self.grid = QGridLayout()
        self.grid.setSpacing(4)
        grid_container = QWidget()
        grid_container.setLayout(self.grid)
        self.tab_widget.addTab(grid_container, "Cámaras en Vivo")

        # Pestaña de Reproducción
        self.playback_panel = PlaybackPanel()
        self.tab_widget.addTab(self.playback_panel, "Reproducción")

        # Establecer tamaños iniciales del splitter
        self.main_splitter.setSizes([200, self.width() - 200])

        self.btn_record.clicked.connect(self.toggle_grabacion)
        self.btn_snapshot.clicked.connect(self.tomar_snapshot)
        self.btn_analitica.clicked.connect(self.toggle_analitica)
        self.btn_manos_arriba.clicked.connect(self.toggle_manos_arriba)
        self.btn_rostros.clicked.connect(self.toggle_rostros)
        

        # Inicializar el estilo de los botones
        self._update_button_style(self.btn_record, False)
        self._update_button_style(self.btn_analitica, False)
        self._update_button_style(self.btn_manos_arriba, False)
        self._update_button_style(self.btn_rostros, False)

        num_cameras = len(config_manager.canales_originales)
        num_cols = 2
        num_rows = (num_cameras + num_cols - 1) // num_cols

        for i, canal in enumerate(config_manager.canales_originales):
            label = CameraLabel(canal)
            label.mousePressEvent = lambda event, c=canal: self.seleccionar_camara(c)
            self.labels[canal] = label
            row = i // num_cols
            col = i % num_cols
            self.grid.addWidget(label, row, col)
            # Inicializar el estado de las analíticas para cada cámara
            self._update_camera_analytics_status(canal)

        for i in range(num_cols):
            self.grid.setColumnStretch(i, 1)
        for i in range(num_rows):
            self.grid.setRowStretch(i, 1)

        for canal, thread in self.camera_threads.items():
            thread.frame_ready.connect(self.update_frame)

        register_event_callback(self.event_callback_wrapper)
        iniciar_eventos()

    def _get_analytics_status_text(self, canal_id):
        estados = []
        if config_manager.is_recording(canal_id): estados.append("Grabando: ON")
        if config_manager.is_analytics_active(canal_id): estados.append("Personas: ON")
        if config_manager.is_hands_up_active(canal_id): estados.append("Manos: ON")
        if config_manager.is_face_detection_active(canal_id): estados.append("Rostros: ON")
        return " | ".join(estados) if estados else "Analíticas: OFF"

    def _update_camera_analytics_status(self, canal_id):
        if canal_id in self.labels:
            status_text = self._get_analytics_status_text(canal_id)
            self.labels[canal_id].update_analytics_status(status_text)

    def show_playback_tab(self):
        self.tab_widget.setCurrentWidget(self.playback_panel)

    def event_callback_wrapper(self, cam_ip, channel, event_type, event_desc, ruta_imagen):
        self.event_signals.event_detected.emit(cam_ip, channel, event_type, event_desc, ruta_imagen)

    def on_event_detected(self, cam_ip, channel, event_type, event_desc, ruta_imagen):
        canal = channel
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        event_text = f"[{timestamp}] {event_type.upper()}: {event_desc} (Cámara {canal})"
        self.event_log.append(event_text)
        if len(self.event_log) > 50:
            self.event_log.pop(0)
        
        self.events_text.setText("\n".join(reversed(self.event_log)))
        self.events_text.verticalScrollBar().setValue(self.events_text.verticalScrollBar().maximum())
        
        if canal in self.labels:
            self.flash_camera_border(canal, event_type)
            config_manager.start_event_recording(canal, event_type, event_desc, timestamp, config_manager.POST_EVENT_RECORD_SECONDS)

    def flash_camera_border(self, canal, event_type):
        if canal not in self.labels: return
        label = self.labels[canal]
        label.flash_border(event_type)

    def seleccionar_camara(self, canal):
        if canal in self.selected_cameras:
            self.selected_cameras.remove(canal)
            self.labels[canal].set_selected(False)
        else:
            self.selected_cameras.add(canal)
            self.labels[canal].set_selected(True)

    def update_frame(self, canal_id, frame):
        """
        Recibe un frame en formato np.ndarray (RGB) directamente desde el hilo de la cámara.
        Si tu hilo de cámara aún emite QPixmap, modifícalo para emitir np.ndarray (RGB) para máxima eficiencia.
        """
        if canal_id in self.labels:
            label = self.labels[canal_id]
            label.set_frame(frame)

    def toggle_grabacion(self):
        for canal in self.selected_cameras:
            self.command_client.send_command('toggle_grabacion', canal)
            print(f"Comando de grabación enviado para cámara {canal}")

    def tomar_snapshot(self):
        for canal in self.selected_cameras:
            self.command_client.send_command('snapshot', canal)
            print(f"Comando de snapshot enviado para cámara {canal}")

    def toggle_analitica(self):
        for canal in self.selected_cameras:
            self.command_client.send_command('toggle_analitica', canal)
            print(f"Comando de analítica enviado para cámara {canal}")

    def toggle_manos_arriba(self):
        for canal in self.selected_cameras:
            self.command_client.send_command('toggle_manos_arriba', canal)
            print(f"Comando de manos arriba enviado para cámara {canal}")

    def toggle_rostros(self):
        for canal in self.selected_cameras:
            self.command_client.send_command('toggle_rostros', canal)
            print(f"Comando de rostros enviado para cámara {canal}")
    def closeEvent(self, event):
        # Cierra el cliente de comandos limpio
        if hasattr(self, 'command_client'):
            self.command_client.close()
        super().closeEvent(event)

    def _update_button_style(self, button, is_active):
        if is_active:
            button.setStyleSheet('''
                QPushButton {
                    background-color: #007bff; /* Azul para activo */
                    color: #fff;
                    border-radius: 10px;
                    border: 2px solid #0056b3;
                    font-size: 15px;
                    font-weight: bold;
                    padding: 8px 16px;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                    border: 2px solid #007bff;
                    color: #fff;
                }
            ''')
        else:
            button.setStyleSheet('''
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

    def closeEvent(self, event):
        for timer in self.event_flash_timers.values():
            timer.stop()
        detener_eventos()
        config_manager.set_stop_flag() # Asegurarse de que los hilos se detengan
        event.accept()

    def mostrar_grid(self):
        self.show()

