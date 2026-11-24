"""
서 있는 위치 확인: 인식에 필요한 부위가 웹캠 화면 안에 들어왔는지 Pose 좌표로 판단한다

키나 카메라 높이에 상관없이, 아래 조건만 맞으면 통과다
    1. 사람(Pose)이 잡힌다
    2. 양 손목이 화면 안에 보인다  (차렷 자세에서 쉬는 높이를 재야 한다)
    3. 코 위로 손을 올릴 여유가 있다
    4. 양 어깨 바깥으로 팔꿈치가 나갈 여유가 있다
    5. 너무 멀리 서 있지 않다

기준값은 웹캠으로 맞춰 본 값이 아니라 추정값이다. 써 보면서 조정한다.
"""

import numpy as np


# 판단 결과
POSITION_OK = "position_ok"
POSITION_NO_PERSON = "position_no_person"
POSITION_STEP_BACK = "position_step_back"      # 손목이나 머리 위가 잘림 → 뒤로
POSITION_MOVE_CENTER = "position_move_center"  # 한쪽 옆이 잘림 → 가운데로
POSITION_COME_CLOSER = "position_come_closer"  # 너무 멀다 → 앞으로

# body 배열 행 번호 (mediapipe_extractor.BODY_LANDMARK_IDS 순서)
NOSE = 0
RIGHT_SHOULDER = 1
LEFT_SHOULDER = 2
RIGHT_WRIST = 5
LEFT_WRIST = 6

MIN_VISIBILITY = 0.5        # 손목 visibility 가 이보다 낮으면 안 보이는 것으로 본다
EDGE_MARGIN = 0.02          # 화면 가장자리에서 이만큼(화면 크기 비율) 안쪽이어야 "화면 안"
HEAD_ROOM = 0.8             # 코 위로 어깨 너비의 이 배만큼이 화면 안이어야 한다 (손 올릴 여유)
SIDE_ROOM = 0.6             # 각 어깨 바깥으로 어깨 너비의 이 배만큼이 화면 안이어야 한다 (팔꿈치 여유)
MIN_SHOULDER_RATIO = 0.10   # 어깨 너비가 화면 폭의 이 비율보다 작으면 너무 멀다


def check_position(body, frame_width, frame_height):
    """
    body         : mediapipe_extractor 가 돌려준 (7, 3) [x 픽셀, y 픽셀, visibility]. Pose가 없으면 None
    frame_width  : 프레임 폭 (픽셀)
    frame_height : 프레임 높이 (픽셀)
    반환         : POSITION_* 중 하나. 여러 개가 걸리면 위에서부터 먼저 걸린 것
    """
    if body is None:
        return POSITION_NO_PERSON

    left_edge = frame_width * EDGE_MARGIN
    right_edge = frame_width * (1.0 - EDGE_MARGIN)
    top_edge = frame_height * EDGE_MARGIN
    bottom_edge = frame_height * (1.0 - EDGE_MARGIN)

    shoulder_width = float(np.linalg.norm(body[RIGHT_SHOULDER, :2] - body[LEFT_SHOULDER, :2]))

    for wrist in (RIGHT_WRIST, LEFT_WRIST):
        x, y, visibility = body[wrist]
        if visibility < MIN_VISIBILITY or not (left_edge <= x <= right_edge and top_edge <= y <= bottom_edge):
            return POSITION_STEP_BACK

    if body[NOSE, 1] - HEAD_ROOM * shoulder_width < top_edge:
        return POSITION_STEP_BACK

    shoulder_xs = (body[RIGHT_SHOULDER, 0], body[LEFT_SHOULDER, 0])
    left_short = min(shoulder_xs) - SIDE_ROOM * shoulder_width < left_edge
    right_short = max(shoulder_xs) + SIDE_ROOM * shoulder_width > right_edge
    if left_short and right_short:
        return POSITION_STEP_BACK
    if left_short or right_short:
        return POSITION_MOVE_CENTER

    if shoulder_width < frame_width * MIN_SHOULDER_RATIO:
        return POSITION_COME_CLOSER

    return POSITION_OK
