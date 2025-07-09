from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage
import numpy as np
import OpenGL.GL as gl

class OpenGLVideoWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.frame = None
        self.texture_id = None
        self.setMinimumSize(320, 240)

    def set_frame(self, frame: np.ndarray):
        self.frame = frame
        self.update()

    def initializeGL(self):
        gl.glClearColor(0.0, 0.0, 0.0, 1.0)
        self.texture_id = gl.glGenTextures(1)

    def paintGL(self):
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        if self.frame is not None:
            h, w, ch = self.frame.shape
            img = QImage(self.frame.data, w, h, ch * w, QImage.Format_RGB888)
            img = img.mirrored(False, True)
            img_data = img.bits().asstring(img.byteCount())

            gl.glBindTexture(gl.GL_TEXTURE_2D, self.texture_id)
            gl.glTexImage2D(gl.GL_TEXTURE_2D, 0, gl.GL_RGB, w, h, 0, gl.GL_RGB, gl.GL_UNSIGNED_BYTE, img_data)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MIN_FILTER, gl.GL_LINEAR)
            gl.glTexParameteri(gl.GL_TEXTURE_2D, gl.GL_TEXTURE_MAG_FILTER, gl.GL_LINEAR)

            # Restaurar: mantener aspect ratio y centrar imagen
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

            gl.glEnable(gl.GL_TEXTURE_2D)
            gl.glBegin(gl.GL_QUADS)
            gl.glTexCoord2f(0.0, 0.0)
            gl.glVertex2f(-draw_w, -draw_h)
            gl.glTexCoord2f(1.0, 0.0)
            gl.glVertex2f(draw_w, -draw_h)
            gl.glTexCoord2f(1.0, 1.0)
            gl.glVertex2f(draw_w, draw_h)
            gl.glTexCoord2f(0.0, 1.0)
            gl.glVertex2f(-draw_w, draw_h)
            gl.glEnd()
            gl.glDisable(gl.GL_TEXTURE_2D)

    def resizeGL(self, w, h):
        gl.glViewport(0, 0, w, h)
        gl.glMatrixMode(gl.GL_PROJECTION)
        gl.glLoadIdentity()
        gl.glOrtho(-1, 1, -1, 1, -1, 1)
        gl.glMatrixMode(gl.GL_MODELVIEW)
        gl.glLoadIdentity()
