"""
위치 판단 값 실시간 출력 (임시 확인용, 확인 후 삭제)
실행: 프로젝트 폴더에서  PYTHONPATH=. python tools/position_debug.py [카메라번호]
q 로 종료
"""
import sys
import time

import cv2
import numpy as np

from inference import mediapipe_extractor, position_check as pc

index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
cap = cv2.VideoCapture(index)
hand, pose = mediapipe_extractor.create_landmarkers()
start = time.time()
last_print = 0.0

while True:
    ok, frame = cap.read()
    if not ok:
        break
    h, w = frame.shape[:2]
    ts = int((time.time() - start) * 1000)
    *_, body = mediapipe_extractor.extract_keypoints_with_body(hand, pose, frame, ts)
    result = pc.check_position(body, w, h)

    if body is not None:
        sw = float(np.linalg.norm(body[pc.RIGHT_SHOULDER, :2] - body[pc.LEFT_SHOULDER, :2]))
        rw, lw = body[pc.RIGHT_WRIST], body[pc.LEFT_WRIST]
        line = (f"{w}x{h} | {result:22s} | 손목y R {rw[1]/h:.2f} L {lw[1]/h:.2f} (기준 ≤0.98)"
                f" | 손목vis R {rw[2]:.2f} L {lw[2]:.2f} (기준 ≥0.50)"
                f" | 머리여유 {(body[pc.NOSE,1]-pc.HEAD_ROOM*sw)/h:.2f} (기준 ≥0.02)"
                f" | 어깨폭 {sw/w:.2f} (기준 ≥0.15)")
        for p in body.astype(int):
            cv2.circle(frame, (p[0], p[1]), 6, (0, 255, 0), -1)
    else:
        line = f"{w}x{h} | {result}"

    if time.time() - last_print > 0.5:
        print(line)
        last_print = time.time()
    cv2.putText(frame, result, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
    cv2.imshow("position debug", frame)
    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
