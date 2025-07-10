from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QImage
import numpy as np
import OpenGL.GL as gl
import time

# Importar administrador de GPUs para renderizado
from core.gpu_manager import gpu_manager, get_rendering_device

class OpenGLVideoWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.frame = None
        self.texture_id = None
        self.setMinimumSize(320, 240)
        self.last_frame_time = 0
        self.fps_limit = 30  # Limitar FPS para mejor rendimiento
        self.frame_cache = None
        self.cache_valid = False
        
        # Configurar dispositivo de renderizado
        self.rendering_device = get_rendering_device()
        print(f"OpenGL Widget usando dispositivo: {self.rendering_device}")
        
        # Timer para actualización controlada
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update)
        self.update_timer.start(33)  # ~30 FPS

    def set_frame(self, frame: np.ndarray):
        current_time = time.time()
        
        # Limitar FPS para evitar sobrecarga
        if current_time - self.last_frame_time < 1.0 / self.fps_limit:
            return
        
        self.frame = frame
        self.cache_valid = False
        self.last_frame_time = current_time
        # No llamar update() aquí, se hace con el timer

    def initializeGL(self):
        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        gl.glEnable(gl.GL_TEXTURE_2D)
        self.texture_id = gl.glGenTextures(1)
        
        # Configurar parámetros de textura una vez
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_S, gl.GL_CLAMP_TO_EDGE)
        gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_WRAP_T, gl.GL_CLAMP_TO_EDGE)

    def paintGL(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        
        if self.frame is not None:
            # Usar caché si es válido
            if not self.cache_valid:
                self._update_texture()
                self.cache_valid = True
            
            self._render_texture()

    def _update_texture(self):
        """Actualizar la textura OpenGL con el frame actual"""
        if self.frame is None:
            return
            
        h, w, ch = self.frame.shape
        
        # Optimización: Usar formato RGB directamente
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, w, h, 0, 
                       gl.GL_RGB, gl.GL_UNSIGNED_BYTE, self.frame.tobytes())

    def _render_texture(self):
        """Renderizar la textura en el widget"""
        if self.frame is None:
            return
            
        h, w, ch = self.frame.shape
        
        # Calcular aspect ratio y dimensiones de renderizado
        widget_w = self.width()
        widget_h = self.height()
        aspect_img = w / h
        aspect_widget = widget_w / widget_h if widget_h != 0 else 1
        
        if aspect_img > aspect_widget:
            draw_w = 1.0
            draw_h = aspect_widget / aspect_img
        else:
            draw_h = 1.0
            draw_w = aspect_img / aspect_widget

        # Renderizar quad con textura (coordenadas corregidas para evitar volteo)
        gl.glEnable(gl.GL_TEXTURE_2D)
        gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
        
        gl.glBegin(gl.GL_QUADS)
        # Corregir coordenadas de textura para evitar imagen invertida
        gl.glTexCoord2f(0.0, 1.0)  # Esquina inferior izquierda -> superior izquierda de textura
        gl.glVertex2f(-draw_w, -draw_h)
        gl.glTexCoord2f(1.0, 1.0)  # Esquina inferior derecha -> superior derecha de textura
        gl.glVertex2f(draw_w, -draw_h)
        gl.glTexCoord2f(1.0, 0.0)  # Esquina superior derecha -> inferior derecha de textura
        gl.glVertex2f(draw_w, draw_h)
        gl.glTexCoord2f(0.0, 0.0)  # Esquina superior izquierda -> inferior izquierda de textura
        gl.glVertex2f(-draw_w, draw_h)
        gl.glEnd()
        
        gl.glDisable(gl.GL_TEXTURE_2D)

    def resizeGL(self, width, height):
        gl.glViewport(0, 0, width, height)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
