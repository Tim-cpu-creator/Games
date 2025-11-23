import cv2
import mediapipe as mp
import pygame
import numpy as np
import threading
import math
import sys

# ==================== 配置 ====================
WINDOW_WIDTH  = 1920      # 改成你的屏幕宽
WINDOW_HEIGHT = 1080      # 改成你的屏幕高
CAM_SOURCE    = 0
SMOOTHING     = 0.60      # 惯性，越小越跟手
SENSITIVITY   = 3.0       # 核心！！！调高到 3.0 才能抬头低头满屏
GLOW_RADIUS   = 180
# ============================================

stop_event = threading.Event()

# MediaPipe
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1,
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

cap = cv2.VideoCapture(CAM_SOURCE)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

# Pygame 全屏黑窗
pygame.init()
screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.NOFRAME)
pygame.display.set_caption("Head Pose Light - Close cam window to exit")
pygame.mouse.set_visible(False)

cur_x = WINDOW_WIDTH // 2
cur_y = WINDOW_HEIGHT // 2
lock = threading.Lock()

# 关键3D点
NOSE = 1
CHIN = 152
LEFT_EYE = 33
RIGHT_EYE = 263

def get_yaw_pitch(landmarks):
    n = np.array([landmarks[NOSE].x,    landmarks[NOSE].y,    landmarks[NOSE].z])
    c = np.array([landmarks[CHIN].x,    landmarks[CHIN].y,    landmarks[CHIN].z])
    le = np.array([landmarks[LEFT_EYE].x, landmarks[LEFT_EYE].y, landmarks[LEFT_EYE].z])
    re = np.array([landmarks[RIGHT_EYE].x, landmarks[RIGHT_EYE].y, landmarks[RIGHT_EYE].z])
    
    eye_mid = (le + re) / 2
    face_vec = n - eye_mid                      # 脸朝向向量
    
    yaw   = math.atan2(face_vec[0], -face_vec[2])   # 左右
    pitch = math.asin(np.clip(face_vec[1], -0.99, 0.99))  # 上下
    
    return yaw, pitch

def camera_thread():
    global cur_x, cur_y
    prev_x = WINDOW_WIDTH // 2
    prev_y = WINDOW_HEIGHT // 2
    
    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret:
            break
            
        frame = cv2.flip(frame, 1)                     # 镜像
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)
        
        if results.multi_face_landmarks:
            lm = results.multi_face_landmarks[0].landmark
            yaw, pitch = get_yaw_pitch(lm)
            
            # 核心：这里除以 3.14*0.9 ≈ π 让 ±45° 左右就能满屏
            target_x = WINDOW_WIDTH / 2  + yaw   * WINDOW_WIDTH  * SENSITIVITY
            target_y = WINDOW_HEIGHT / 4 + pitch * WINDOW_HEIGHT * SENSITIVITY
            
            target_x = np.clip(target_x, GLOW_RADIUS, WINDOW_WIDTH  - GLOW_RADIUS)
            target_y = np.clip(target_y, GLOW_RADIUS, WINDOW_HEIGHT - GLOW_RADIUS)
            
            sx = prev_x + (target_x - prev_x) * (1 - SMOOTHING)
            sy = prev_y + (target_y - prev_y) * (1 - SMOOTHING)
            
            with lock:
                cur_x, cur_y = int(sx), int(sy)
            prev_x, prev_y = sx, sy
        
        # 纯画面！一个像素都不画
        small = cv2.resize(frame, (400, 300))
        cv2.imshow('Camera - Click × to EXIT', small)
        
        key = cv2.waitKey(1)
        # 点×关闭 或 按q/ESC
        if key == ord('q') or key == 27:
            stop_event.set()
            break
        if cv2.getWindowProperty('Camera - Click × to EXIT', cv2.WND_PROP_VISIBLE) < 1:
            stop_event.set()
            break
    
    cap.release()
    cv2.destroyAllWindows()
    pygame.quit()
    sys.exit(0)        # 强制干净退出

# 启动摄像头线程
threading.Thread(target=camera_thread, daemon=False).start()

# 主光球循环
clock = pygame.time.Clock()
while not stop_event.is_set():
    for event in pygame.event.get():
        if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
            stop_event.set()
    
    screen.fill((0, 0, 0))
    
    with lock:
        x, y = cur_x, cur_y
    
    # 发光球
    for r in range(GLOW_RADIUS, 0, -9):
        intensity = int(255 * (1 - r/GLOW_RADIUS * 0.8))
        color = (intensity//10, intensity//4, intensity)
        pygame.draw.circle(screen, color, (x, y), r)
    pygame.draw.circle(screen, (255, 255, 255), (x, y), 22)
    pygame.draw.circle(screen, (100, 255, 255), (x, y), 10)
    
    pygame.display.flip()
    clock.tick(120)

# 最终保险退出
stop_event.set()
pygame.quit()
sys.exit(0)