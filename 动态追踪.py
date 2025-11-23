import cv2
import numpy as np

# --------------------- 参数区 / 一起改 -------------
caps = 0                     # 替换为视频文件路径，例如 "video.mp4" 或 0 代表摄像头
frame_res = (640, 480)       # 缩放大小，保证处理速度
history = 500                # 背景建模的帧数
varThreshold = 16            # 变异阈值，越大背景更新越慢
detectShadows = False        # 关闭阴影检测（不需要，阴影会导致误检）
min_area = 500               # 小于此面积的连通块直接丢弃
kernel_size = (5, 5)         # 形态学核
dilation_iter = 2
# ----------------------------------------------------

# 1. 视频读取
cap = cv2.VideoCapture(caps)

# 2. 背景减除器
fgbg = cv2.createBackgroundSubtractorMOG2(history=history,
                                          varThreshold=varThreshold,
                                          detectShadows=detectShadows)

# 形态学核
kernel = cv2.getStructuringElement(cv2.MORPH_RECT, kernel_size)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # 3. 预处理，缩放 + 灰度
    frame_small = cv2.resize(frame, frame_res)
    gray = cv2.cvtColor(frame_small, cv2.COLOR_BGR2GRAY)

    # 4. 背景减除
    fgmask = fgbg.apply(gray)

    # 5. 阈值化
    _, fgmask = cv2.threshold(fgmask, 250, 255, cv2.THRESH_BINARY)

    # 6. 形态学清理
    fgmask = cv2.morphologyEx(fgmask, cv2.MORPH_OPEN, kernel, iterations=2)
    fgmask = cv2.dilate(fgmask, kernel, iterations=dilation_iter)

    # 7. 轮廓检测
    contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # 8. 过滤 & 绘制
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        x, y, w, h = cv2.boundingRect(cnt)
        cv2.rectangle(frame_small, (x, y), (x + w, y + h), (0, 255, 0), 2)

    # 9. 显示
    cv2.imshow('Motion Boxes', frame_small)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
