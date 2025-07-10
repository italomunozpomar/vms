import cv2
import mediapipe as mp
import time
import os
from datetime import datetime

# Importar administrador de GPUs
from core.gpu_manager import gpu_manager, get_pose_device

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

class ManosArribaDetector:
    def __init__(self):
        # Configurar MediaPipe para usar la GPU asignada si está disponible
        pose_device = get_pose_device()
        
        # MediaPipe no usa PyTorch directamente, pero podemos configurar
        # el procesamiento para que use la GPU asignada cuando sea posible
        if pose_device.type == 'cuda':
            gpu_id = int(pose_device.index) if pose_device.index is not None else 0
            print(f"MediaPipe Pose configurado para GPU {gpu_id}")
            # Configurar variables de entorno para MediaPipe
            os.environ['MEDIAPIPE_DISABLE_GPU'] = '0'
        else:
            print("MediaPipe Pose usando CPU")
            
        self.pose = mp_pose.Pose(
            min_detection_confidence=0.5, 
            min_tracking_confidence=0.5,
            model_complexity=1  # 0=lite, 1=full, 2=heavy
        )
        self.manos_arriba_start = None
        self.captura_realizada = False
        self.pose_device = pose_device

    def detectar(self, frame, guardar_captura=True, output_path="./", canal_id="unknown"):
        h, w = frame.shape[:2]
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.pose.process(frame_rgb)

        manos_arriba_detectado = False

        if results.pose_landmarks:
            lm = results.pose_landmarks.landmark

            hombro_izq = lm[mp_pose.PoseLandmark.LEFT_SHOULDER]
            hombro_der = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER]
            muneca_izq = lm[mp_pose.PoseLandmark.LEFT_WRIST]
            muneca_der = lm[mp_pose.PoseLandmark.RIGHT_WRIST]

            hombros_y = (hombro_izq.y + hombro_der.y) / 2

            manos_arriba = (
                muneca_izq.y < hombros_y and
                muneca_der.y < hombros_y
            )

            if manos_arriba:
                if self.manos_arriba_start is None:
                    self.manos_arriba_start = time.time()
                elif time.time() - self.manos_arriba_start >= 2 and not self.captura_realizada:
                    if guardar_captura:
                        # Crear carpeta específica para manos arriba
                        manos_arriba_folder = os.path.join(output_path, "captures", "manos_arriba")
                        os.makedirs(manos_arriba_folder, exist_ok=True)
                        
                        # Crear nombre de archivo más descriptivo
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        fecha = datetime.now().strftime("%Y-%m-%d")
                        ruta = os.path.join(manos_arriba_folder, f"cam_{canal_id}_manos_arriba_{fecha}_{timestamp}.jpg")
                        
                        cv2.imwrite(ruta, frame)
                        print(f"🙌 Captura manos arriba tomada: {ruta}")
                    self.captura_realizada = True
                    manos_arriba_detectado = True
            else:
                self.manos_arriba_start = None
                self.captura_realizada = False

            # Dibuja los landmarks en el frame (opcional, útil para debug/visualización)
            mp_drawing.draw_landmarks(frame, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

        return frame, manos_arriba_detectado
