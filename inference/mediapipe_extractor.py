# inference/keypoints.py
"""
웹캠 프레임 한 장에서 MediaPipe로 46점 좌표를 뽑는다

MediaPipe Tasks API VIDEO 모드
    손 21점          : HandLandmarker
    팔꿈치·어깨 4점  : PoseLandmarker (오른팔꿈치 14, 왼팔꿈치 13, 오른어깨 12, 왼어깨 11)

슬롯 순서 (46점, 학습 데이터와 동일)
    0 ~ 20  : 오른손
    21 ~ 41 : 왼손
    42      : 오른팔꿈치
    43      : 왼팔꿈치
    44      : 오른어깨
    45      : 왼어깨
"""

import os

import cv2
import mediapipe as mp
import numpy as np


MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")
HAND_MODEL_PATH = os.path.join(MODEL_DIR, "hand_landmarker.task")
POSE_MODEL_PATH = os.path.join(MODEL_DIR, "pose_landmarker.task")

NUM_ALL_POINTS = 46
RIGHT_HAND_START = 0
LEFT_HAND_START = 21
HAND_POINT_COUNT = 21
POSE_SLOT_START = 42

# MediaPipe 손 라벨 → 손 슬롯 시작 번호 (비반전 입력 기준)
HAND_LABEL_TO_SLOT = {
    "Left": LEFT_HAND_START,   # 사용자의 왼손
    "Right": RIGHT_HAND_START,   # 사용자의 오른손
}

# 슬롯 42 ~ 45에 넣을 MediaPipe Pose 관절 번호 (순서대로)
POSE_LANDMARK_IDS = [
    14,  # 42: 오른팔꿈치
    13,  # 43: 왼팔꿈치
    12,  # 44: 오른어깨
    11,  # 45: 왼어깨
]


def create_landmarkers():
    """
    HandLandmarker, PoseLandmarker VIDEO Mode Load
    검출 기준값 : MediaPipe 기본값(0.5)

    반환: (hand_landmarker, pose_landmarker)
    """
    if not os.path.exists(HAND_MODEL_PATH):
        raise FileNotFoundError(f"HandLandmarker 모델을 찾을 수 없습니다: {HAND_MODEL_PATH}")
    if not os.path.exists(POSE_MODEL_PATH):
        raise FileNotFoundError(f"PoseLandmarker 모델을 찾을 수 없습니다: {POSE_MODEL_PATH}")

    BaseOptions = mp.tasks.BaseOptions
    RunningMode = mp.tasks.vision.RunningMode

    hand_options = mp.tasks.vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=HAND_MODEL_PATH),
        running_mode=RunningMode.VIDEO,
        num_hands=2,
    )
    pose_options = mp.tasks.vision.PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=POSE_MODEL_PATH),
        running_mode=RunningMode.VIDEO,
        num_poses=1,
    )

    hand_landmarker = mp.tasks.vision.HandLandmarker.create_from_options(hand_options)
    pose_landmarker = mp.tasks.vision.PoseLandmarker.create_from_options(pose_options)
    return hand_landmarker, pose_landmarker


def extract_keypoints(hand_landmarker, pose_landmarker, frame_bgr, timestamp_ms):
    """
    프레임 한 장에서 46점 픽셀 좌표와 부위별 결측 여부를 뽑는다.

    frame_bgr    : OpenCV로 읽은 프레임 (BGR, 좌우 반전하지 않은 것)
    timestamp_ms : 이 프레임의 시각(ms). 이전 호출보다 커야 한다

    반환: (xy, right_missing, left_missing, pose_missing)
        xy            : (46, 2) 픽셀 좌표. 검출되지 않은 부위의 슬롯은 (0, 0)
        right_missing : 오른손이 검출되지 않았으면 True
        left_missing  : 왼손이 검출되지 않았으면 True
        pose_missing  : Pose(사람)가 검출되지 않았으면 True
    """
    height, width = frame_bgr.shape[:2]
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    hand_result = hand_landmarker.detect_for_video(mp_image, timestamp_ms)
    pose_result = pose_landmarker.detect_for_video(mp_image, timestamp_ms)

    xy = np.zeros((NUM_ALL_POINTS, 2), dtype=np.float64)

    # 손: 같은 라벨이 두 번 나오면 손 라벨 점수(handedness score)가 높은 쪽을 쓴다
    best_score = {"Left": -1.0, "Right": -1.0}
    for i in range(len(hand_result.hand_landmarks)):
        label = hand_result.handedness[i][0].category_name   # "Left" 또는 "Right"
        score = hand_result.handedness[i][0].score
        if score <= best_score[label]:
            continue
        best_score[label] = score

        slot_start = HAND_LABEL_TO_SLOT[label]
        landmarks = hand_result.hand_landmarks[i]
        for p in range(HAND_POINT_COUNT):
            # 0 ~ 1 좌표에 화면 폭·높이를 곱해 픽셀로 되돌린다 (화면비 왜곡 방지)
            xy[slot_start + p, 0] = landmarks[p].x * width
            xy[slot_start + p, 1] = landmarks[p].y * height

    right_missing = best_score["Right"] < 0    # "Right" 라벨 = 오른손
    left_missing = best_score["Left"] < 0      # "Left" 라벨 = 왼손

    # Pose: 사람이 검출되면 33점이 모두 나온다
    pose_missing = len(pose_result.pose_landmarks) == 0
    if not pose_missing:
        landmarks = pose_result.pose_landmarks[0]
        for k in range(len(POSE_LANDMARK_IDS)):
            landmark = landmarks[POSE_LANDMARK_IDS[k]]
            xy[POSE_SLOT_START + k, 0] = landmark.x * width
            xy[POSE_SLOT_START + k, 1] = landmark.y * height

    return xy, right_missing, left_missing, pose_missing
