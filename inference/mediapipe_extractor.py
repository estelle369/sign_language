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

# MediaPipe 손 라벨 → 손 슬롯 시작 번호 (비반전 입력 기준). Pose가 검출되지 않은 프레임에서만 쓴다
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

# 손목 트리거용 Pose 손목 관절 번호 (모델 입력에는 쓰지 않는다)
# Pose는 사람만 잡히면 손목 좌표를 항상 주므로, 몸에 붙인 손을 HandLandmarker가 못 잡아도 높이를 잴 수 있다
POSE_RIGHT_WRIST = 16
POSE_LEFT_WRIST = 15


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

    반환: (xy, right_missing, left_missing, pose_missing, wrist_xy)
        xy            : (46, 2) 픽셀 좌표. 검출되지 않은 부위의 슬롯은 (0, 0)
        right_missing : 오른손이 검출되지 않았으면 True
        left_missing  : 왼손이 검출되지 않았으면 True
        pose_missing  : Pose(사람)가 검출되지 않았으면 True
        wrist_xy      : (2, 2) Pose 손목 픽셀 좌표 [오른손목, 왼손목]. 손목 트리거용.
                        Pose가 검출되지 않으면 (0, 0)
    """
    height, width = frame_bgr.shape[:2]
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

    hand_result = hand_landmarker.detect_for_video(mp_image, timestamp_ms)
    pose_result = pose_landmarker.detect_for_video(mp_image, timestamp_ms)

    xy = np.zeros((NUM_ALL_POINTS, 2), dtype=np.float64)

    # Pose: 사람이 검출되면 33점이 모두 나온다. 손 슬롯을 정할 때 손목 좌표가 필요하므로 먼저 처리한다
    pose_missing = len(pose_result.pose_landmarks) == 0
    wrist_xy = np.zeros((2, 2), dtype=np.float64)
    if not pose_missing:
        landmarks = pose_result.pose_landmarks[0]
        for k in range(len(POSE_LANDMARK_IDS)):
            landmark = landmarks[POSE_LANDMARK_IDS[k]]
            xy[POSE_SLOT_START + k, 0] = landmark.x * width
            xy[POSE_SLOT_START + k, 1] = landmark.y * height

        wrist_ids = [POSE_RIGHT_WRIST, POSE_LEFT_WRIST]
        for k in range(2):
            landmark = landmarks[wrist_ids[k]]
            wrist_xy[k, 0] = landmark.x * width
            wrist_xy[k, 1] = landmark.y * height

    # 손: 검출된 손마다 21점을 픽셀 좌표로 바꾼다
    # 0 ~ 1 좌표에 화면 폭·높이를 곱해 픽셀로 되돌린다 (화면비 왜곡 방지)
    hands = []
    for i in range(len(hand_result.hand_landmarks)):
        landmarks = hand_result.hand_landmarks[i]
        points = np.zeros((HAND_POINT_COUNT, 2), dtype=np.float64)
        for p in range(HAND_POINT_COUNT):
            points[p, 0] = landmarks[p].x * width
            points[p, 1] = landmarks[p].y * height
        hands.append(points)

    if pose_missing:
        slot_starts = _slots_by_label(hand_result)
    else:
        slot_starts = _slots_by_pose_wrist(hands, wrist_xy)

    right_missing = True
    left_missing = True
    for i in range(len(hands)):
        slot_start = slot_starts[i]
        if slot_start is None:
            continue
        xy[slot_start:slot_start + HAND_POINT_COUNT] = hands[i]
        if slot_start == RIGHT_HAND_START:
            right_missing = False
        else:
            left_missing = False

    return xy, right_missing, left_missing, pose_missing, wrist_xy


def _slots_by_pose_wrist(hands, wrist_xy):
    """
    검출된 손의 0번(손목)이 Pose 오른손목(16)과 왼손목(15) 중 어디에 가까운지로 손 슬롯을 정한다.
    HandLandmarker의 "Left"/"Right" 라벨은 프레임마다 바뀌거나 두 손에 같은 라벨이 붙는 경우가 있어 쓰지 않는다.

    hands    : 손마다 (21, 2) 픽셀 좌표 리스트 (최대 2개)
    wrist_xy : (2, 2) Pose 손목 픽셀 좌표 [오른손목, 왼손목]
    반환     : 손마다 슬롯 시작 번호 리스트 (RIGHT_HAND_START 또는 LEFT_HAND_START)
    """
    right_wrist = wrist_xy[0]
    left_wrist = wrist_xy[1]

    if len(hands) == 1:
        to_right = np.linalg.norm(hands[0][0] - right_wrist)
        to_left = np.linalg.norm(hands[0][0] - left_wrist)
        return [RIGHT_HAND_START] if to_right <= to_left else [LEFT_HAND_START]

    if len(hands) == 2:
        # 두 손이 같은 슬롯에 들어가지 않도록, 두 가지 배정 중 손목 거리 합이 작은 쪽을 고른다
        #   배정 A: 손 0 → 오른손, 손 1 → 왼손
        #   배정 B: 손 0 → 왼손,   손 1 → 오른손
        cost_a = np.linalg.norm(hands[0][0] - right_wrist) + np.linalg.norm(hands[1][0] - left_wrist)
        cost_b = np.linalg.norm(hands[0][0] - left_wrist) + np.linalg.norm(hands[1][0] - right_wrist)
        if cost_a <= cost_b:
            return [RIGHT_HAND_START, LEFT_HAND_START]
        return [LEFT_HAND_START, RIGHT_HAND_START]

    return []


def _slots_by_label(hand_result):
    """
    Pose가 검출되지 않아 손목 좌표가 없을 때만 쓴다. HandLandmarker 라벨로 손 슬롯을 정한다.
    같은 라벨이 두 번 나오면 라벨 점수(handedness score)가 높은 쪽만 쓰고, 나머지는 None(버림)이다.

    반환: 손마다 슬롯 시작 번호 또는 None 리스트
    """
    slot_starts = [None] * len(hand_result.handedness)
    best_index = {"Left": -1, "Right": -1}
    best_score = {"Left": -1.0, "Right": -1.0}
    for i in range(len(hand_result.handedness)):
        label = hand_result.handedness[i][0].category_name   # "Left" 또는 "Right"
        score = hand_result.handedness[i][0].score
        if score > best_score[label]:
            best_score[label] = score
            best_index[label] = i

    for label in ["Left", "Right"]:
        if best_index[label] >= 0:
            slot_starts[best_index[label]] = HAND_LABEL_TO_SLOT[label]
    return slot_starts
