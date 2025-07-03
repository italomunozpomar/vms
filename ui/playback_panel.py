import os
import cv2
from datetime import datetime
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QDateEdit, QTableWidget, QTableWidgetItem, QSlider, QHeaderView
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage, QPixmap

from config.config_manager import config_manager
from config.database_manager import db_manager

class PlaybackPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_video_path = None
        self.cap = None
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self.play_frame)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # --- Controles de Búsqueda ---
        search_layout = QHBoxLayout()
        main_layout.addLayout(search_layout)

        search_layout.addWidget(QLabel("Cámara:"))
        self.camera_selector = QComboBox()
        self.camera_selector.addItems(config_manager.canales_originales)
        search_layout.addWidget(self.camera_selector)

        search_layout.addWidget(QLabel("Desde:"))
        self.date_start = QDateEdit(calendarPopup=True)
        self.date_start.setDate(datetime.now().date())
        search_layout.addWidget(self.date_start)

        search_layout.addWidget(QLabel("Hasta:"))
        self.date_end = QDateEdit(calendarPopup=True)
        self.date_end.setDate(datetime.now().date())
        search_layout.addWidget(self.date_end)

        self.search_button = QPushButton("Buscar")
        self.search_button.clicked.connect(self.search_recordings)
        search_layout.addWidget(self.search_button)

        search_layout.addStretch()

        # --- Tabla de Resultados ---
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels(["Cámara", "Tipo Evento", "Descripción", "Fecha/Hora", "Duración (s)"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.itemDoubleClicked.connect(self.load_selected_recording)
        main_layout.addWidget(self.results_table)

        # --- Reproductor de Video ---
        self.video_player_label = QLabel("Seleccione una grabación para reproducir")
        self.video_player_label.setAlignment(Qt.AlignCenter)
        self.video_player_label.setStyleSheet("background-color: black; border: 1px solid #555;")
        self.video_player_label.setMinimumSize(640, 360)
        main_layout.addWidget(self.video_player_label)

        # Controles de reproducción
        playback_controls_layout = QHBoxLayout()
        main_layout.addLayout(playback_controls_layout)

        self.play_button = QPushButton("Play")
        self.play_button.clicked.connect(self.toggle_playback)
        self.play_button.setEnabled(False)
        playback_controls_layout.addWidget(self.play_button)

        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_playback)
        self.stop_button.setEnabled(False)
        playback_controls_layout.addWidget(self.stop_button)

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 100)
        self.progress_slider.sliderMoved.connect(self.set_playback_position)
        self.progress_slider.setEnabled(False)
        playback_controls_layout.addWidget(self.progress_slider)

        self.time_label = QLabel("00:00 / 00:00")
        playback_controls_layout.addWidget(self.time_label)

    def search_recordings(self):
        camera_id = self.camera_selector.currentText()
        start_date = self.date_start.date().toString("yyyy-MM-dd 00:00:00")
        end_date = self.date_end.date().toString("yyyy-MM-dd 23:59:59")

        recordings = db_manager.get_event_recordings(camera_id=camera_id, start_date=start_date, end_date=end_date)
        
        self.results_table.setRowCount(len(recordings))
        for row_idx, recording in enumerate(recordings):
            # id, camera_id, event_type, event_description, timestamp, file_path, duration_seconds, thumbnail_path
            self.results_table.setItem(row_idx, 0, QTableWidgetItem(recording[1])) # camera_id
            self.results_table.setItem(row_idx, 1, QTableWidgetItem(recording[2])) # event_type
            self.results_table.setItem(row_idx, 2, QTableWidgetItem(recording[3])) # event_description
            self.results_table.setItem(row_idx, 3, QTableWidgetItem(recording[4])) # timestamp
            self.results_table.setItem(row_idx, 4, QTableWidgetItem(str(recording[6]))) # duration_seconds
            self.results_table.item(row_idx, 0).setData(Qt.UserRole, recording[5]) # Store file_path in UserRole

    def load_selected_recording(self, item):
        self.stop_playback()
        
        # Obtener la ruta del video desde la primera columna de la fila seleccionada
        row = item.row()
        first_column_item = self.results_table.item(row, 0)
        if not first_column_item:
            return # No hacer nada si la primera celda no existe
            
        self.current_video_path = first_column_item.data(Qt.UserRole)
        
        if not self.current_video_path or not os.path.exists(self.current_video_path):
            self.video_player_label.setText(f"Error: Archivo no encontrado.\n{self.current_video_path}")
            self.play_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.progress_slider.setEnabled(False)
            return

        self.cap = cv2.VideoCapture(self.current_video_path)
        if not self.cap.isOpened():
            self.video_player_label.setText("Error: No se pudo abrir el video.")
            self.play_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.progress_slider.setEnabled(False)
            return

        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.duration_ms = int(self.total_frames / self.fps * 1000) if self.fps > 0 else 0

        self.progress_slider.setRange(0, self.total_frames - 1)
        self.progress_slider.setValue(0)
        self.update_time_label()

        self.play_button.setEnabled(True)
        self.stop_button.setEnabled(True)
        self.progress_slider.setEnabled(True)
        self.play_frame() # Mostrar el primer frame

    def toggle_playback(self):
        if self.playback_timer.isActive():
            self.playback_timer.stop()
            self.play_button.setText("Play")
        else:
            if self.cap and self.cap.isOpened():
                self.playback_timer.start(1000 // int(self.fps)) # Reproducir a la velocidad original
                self.play_button.setText("Pause")
            else:
                self.video_player_label.setText("No hay video cargado.")

    def play_frame(self):
        if self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                convert_to_qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                p = convert_to_qt_format.scaled(self.video_player_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.video_player_label.setPixmap(QPixmap.fromImage(p))
                
                current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                self.progress_slider.setValue(current_frame)
                self.update_time_label()
            else:
                self.stop_playback() # Fin del video
        else:
            self.stop_playback()

    def stop_playback(self):
        self.playback_timer.stop()
        self.play_button.setText("Play")
        self.play_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        self.progress_slider.setEnabled(False)
        self.progress_slider.setValue(0)
        self.time_label.setText("00:00 / 00:00")
        if self.cap:
            self.cap.release()
            self.cap = None
        self.video_player_label.setText("Seleccione una grabación para reproducir")
        self.video_player_label.clear()

    def set_playback_position(self, frame_number):
        if self.cap and self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
            self.play_frame() # Mostrar el frame en la nueva posición
            self.update_time_label()

    def update_time_label(self):
        if self.cap and self.cap.isOpened():
            current_frame = self.cap.get(cv2.CAP_PROP_POS_FRAMES)
            total_frames = self.cap.get(cv2.CAP_PROP_FRAME_COUNT)
            fps = self.cap.get(cv2.CAP_PROP_FPS)

            current_time_sec = current_frame / fps if fps > 0 else 0
            total_time_sec = total_frames / fps if fps > 0 else 0

            current_min = int(current_time_sec // 60)
            current_sec = int(current_time_sec % 60)
            total_min = int(total_time_sec // 60)
            total_sec = int(total_time_sec % 60)

            self.time_label.setText(f"{current_min:02d}:{current_sec:02d} / {total_min:02d}:{total_sec:02d}")
        else:
            self.time_label.setText("00:00 / 00:00")

    def closeEvent(self, event):
        self.stop_playback()
        super().closeEvent(event)
