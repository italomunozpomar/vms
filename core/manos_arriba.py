import cv2
import mediapipe as mp
import time
from datetime import datetime

pose = None
mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils

manos_arriba_start = None
captura_realizada = False

def inicializar_pose():
    global pose
    if pose is None:
        pose = mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5)

def detectar_manos_arriba(frame, guardar_captura=True, output_path="./"):
    global manos_arriba_start, captura_realizada

    inicializar_pose()

    h, w = frame.shape[:2]
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = pose.process(frame_rgb)

    manos_arriba_detectado = False

    if results.pose_landmarks:
        lm = results.pose_landmarks.landmark

        hombro_izq = lm[mp_pose.PoseLandmark.LEFT_SHOULDER]
        hombro_der = lm[mp_pose.PoseLandmark.RIGHT_SHOULDER]
        muneca_izq = lm[mp_pose.PoseLandmark.LEFT_WRIST]
        muneca_der = lm[mp_pose.PoseLandmark.RIGHT_WRIST]

        px = lambda l: (int(l.x * w), int(l.y * h))
        hombros_y = (hombro_izq.y + hombro_der.y) / 2

        manos_arriba = (
            muneca_izq.y < hombros_y and
            muneca_der.y < hombros_y
        )

        if manos_arriba:
            if manos_arriba_start is None:
                manos_arriba_start = time.time()
            elif time.time() - manos_arriba_start >= 2 and not captura_realizada:
                if guardar_captura:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    ruta = f"{output_path}/captura_manos_arriba_{timestamp}.jpg"
                    cv2.imwrite(ruta, frame)
                    print(f" Captura tomada: {ruta}")
                captura_realizada = True
                manos_arriba_detectado = True
        else:
            manos_arriba_start = None
            captura_realizada = False

    return frame, manos_arriba_detectado
