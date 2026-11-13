"""
게임 추론용 구간 전처리

손목 트리거로 잘라낸 구간 하나를 모델 입력 (72, 44, 2)로 만든다.
    
슬롯 순서 (46점)
    0 ~ 20  : 오른손
    21 ~ 41 : 왼손
    42      : 오른팔꿈치
    43      : 왼팔꿈치
    44      : 오른어깨
    45      : 왼어깨

처리 순서 
    연속 결측 검사 → 결측 보간 → 어깨 기준 정규화 → 72프레임 리샘플링
"""

from cv2 import intensity_transform
import numpy as np


SEQ_LEN = 72            # 모델 입력 프레임 수
MAX_MISSING_RUN = 10     # 한 부위가 이보다 길게(6프레임 이상) 연속으로 빠지면 그 구간은 인식하지 않는다

RIGHT_HAND_START, RIGHT_HAND_END = 0, 21
LEFT_HAND_START, LEFT_HAND_END = 21, 42
POSE_START, POSE_END = 42, 46   # 팔꿈치 2 + 어깨 2

RIGHT_SHOULDER = 44
LEFT_SHOULDER = 45
NUM_INPUT_POINTS = 44  # 손 42 + 팔꿈치 2
NUM_ALL_POINTS = 46    # 입력 44 + 어깨 2

MIN_SHOULDER_WIDTH = 1e-6  # 이보다 작으면 어깨 너비가 잘못된 것으로 본다


def longest_missing_run(missing):
    """
    결측이 가장 길게 이어진 프레임 수를 센다.

    missing : (T,) bool   결측 프레임이면 True
    반환    : int
    """
    longest = 0
    current = 0
    for is_missing in missing:
        if is_missing:
            current += 1
            if current > longest:
                longest = current
        else:
            current = 0
    return longest


def interpolate_points(frame_numbers, coords, missing):
    """
    한 부위(한 손 또는 Pose)의 결측 프레임을 직선 보간한다.

    frame_numbers : (T,)        프레임 번호 (시간축)
    coords        : (T, P, C)   한 부위 좌표. 앞의 두 채널(x, y)만 보간한다
    missing       : (T,) bool   결측 프레임이면 True

    반환: 보간된 (T, P, C) 복사본
    """
    valid = ~missing

    result = coords.copy()
    valid_numbers = frame_numbers[valid]
    missing_numbers = frame_numbers[missing]

    for point in range(coords.shape[1]):
        for channel in range(2):  # 0: x, 1: y
            valid_values = coords[valid, point, channel]
            result[missing, point, channel] = np.interp(missing_numbers, valid_numbers, valid_values)

    return result


def normalize_sample(xy):
    """
    샘플 하나(사람 한 명의 수어 구간)를 정규화한다.

    xy     : shape (T, 46, 2), T = 프레임 수, 픽셀 단위 좌표
    반환값 : normalized     shape (T, 44, 2)
    """
    num_frames = xy.shape[0]

    # 6번: 프레임마다 어깨 중심과 어깨 거리를 구한다
    centers = np.zeros((num_frames, 2))
    widths = np.zeros(num_frames)
    for t in range(num_frames):
        right = xy[t, RIGHT_SHOULDER] # (오른어깨 x, 오른어깨 y)
        left = xy[t, LEFT_SHOULDER] # (왼어깨 x, 왼어깨 y)
        centers[t] = (right + left) / 2.0 # (오른어깨 x + 왼어깨 x /2, 오른어깨 y + 왼어깨 y /2)
        widths[t] = np.linalg.norm(right - left) # 오른어깨와 왼어깨 사이의 거리

    # 6번: 어깨 너비는 구간 전체의 중앙값 하나
    shoulder_width = float(np.median(widths))
    if shoulder_width < MIN_SHOULDER_WIDTH:
        raise ValueError("어깨 너비가 0에 가깝습니다.")

    normalized = np.zeros((num_frames, NUM_INPUT_POINTS, 2))
    for t in range(num_frames):
        points = xy[t, :NUM_INPUT_POINTS]        # 어깨 2점 제외
        points = points - centers[t]             # 7번: 어깨 중심을 뺀다
        normalized[t] = points / shoulder_width  # 8번: 어깨 너비로 나눈다

    return normalized


def resample_sequence(frame_numbers, coords, seq_len):
    """
    구간을 seq_len 개 지점으로 균등하게 나눠 직선 보간한다.

    frame_numbers: shape (F,)        프레임 번호 (오름차순)
    coords:        shape (F, 44, 2)  프레임별 좌표
    반환:          shape (seq_len, 44, 2)
    """
    frame_count = coords.shape[0]
    point_count = coords.shape[1]
    channel_count = coords.shape[2]

    # seq_len 개의 목표 지점 (소수 위치 가능). 예: 0, 1.94, 3.87, ..., 60
    target_positions = np.linspace(frame_numbers[0], frame_numbers[-1], seq_len)

    result = np.zeros((seq_len, point_count, channel_count), dtype=np.float64)

    # 좌표 하나(점 하나의 x 또는 y)씩 시간축을 따라 보간한다
    for p in range(point_count):
        for c in range(channel_count):
            values_over_time = coords[:, p, c] # 특정 키포인트 p의 x 또는 y 좌표의 원본 값들
            result[:, p, c] = np.interp(target_positions, frame_numbers, values_over_time)

    return result


def preprocess_segment(frame_numbers, xy, right_missing, left_missing, pose_missing):
    """
    손목 트리거로 잘라낸 구간 하나를 모델 입력으로 만든다.

    frame_numbers : (T,)        프레임 번호 (시간축). 웹캠에서는 구간 안의 순번 0, 1, 2, ...
    xy            : (T, 46, 2)  픽셀 좌표. 결측 프레임의 그 부위 슬롯은 (0, 0)
    right_missing : (T,) bool   오른손이 검출되지 않은 프레임
    left_missing  : (T,) bool   왼손이 검출되지 않은 프레임
    pose_missing  : (T,) bool   Pose(팔꿈치·어깨)가 검출되지 않은 프레임

    반환: (72, 44, 2) 모델 입력. 인식하지 않을 구간이면 None
    """
    parts = [
        (RIGHT_HAND_START, RIGHT_HAND_END, right_missing),
        (LEFT_HAND_START, LEFT_HAND_END, left_missing),
        (POSE_START, POSE_END, pose_missing),
    ]

    # 연속 결측 검사: 한 부위라도 6프레임 이상 연속으로 빠지면 인식하지 않는다
    for start, end, missing in parts:
        if np.all(missing):
            return None
        if longest_missing_run(missing) > MAX_MISSING_RUN:
            return None

    # 결측 보간 (부위별)
    filled = xy.copy()
    for start, end, missing in parts:
        filled[:, start:end] = interpolate_points(frame_numbers, xy[:, start:end], missing)

    # 어깨 기준 정규화 (46점 → 44점)
    try:
        normalized = normalize_sample(filled)
    except ValueError:
        return None

    # 72프레임 리샘플링
    return resample_sequence(frame_numbers, normalized, SEQ_LEN)
