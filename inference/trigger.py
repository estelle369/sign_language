"""
손목 높이 트리거: 웹캠 프레임을 하나씩 받아 수어 구간(손 올림 ~ 손 내림)을 잘라낸다

높이 = (어깨 중심 y − 손목 y) ÷ 이번 프레임 어깨 너비   (위쪽이 +, 어깨 너비 단위)
    Pose가 검출되지 않은 프레임은 높이를 잴 수 없으므로 판정에서 건너뛴다 (연속 카운트는 그대로 둔다).

순서
    1. 캘리브레이션: 카운트다운 직후 Pose가 잡힌 첫 프레임에서 양손의 쉬는 높이를 저장한다
    2. 시작: 한 손이라도 (높이 − 쉬는 높이) ≥ 0.3 인 프레임이 3번 연속되면 시작.
             구간은 그 3프레임 중 첫 번째 프레임
    3. 끝 판단: 양손 모두 (높이 − 쉬는 높이) < 0.15 인 프레임이 3번 연속되면 끝났다고 본다
             (기준을 0으로 두면 쉬는 자세의 흔들림 때문에 끝 판단이 안 걸려 두 동작이 합쳐졌다.
              끝 위치는 4번에서 0.3 기준으로 다시 자르므로 이 값은 잘린 구간에 영향이 없다)
    4. 끝 위치: 모아둔 프레임을 뒤에서부터 훑어, 올라간 프레임이 3번 연속되는 곳까지 잘라낸다

구간이 진행되는 동안에는 결측 프레임도 버퍼에 그대로 넣는다. 결측 보간과 연속 결측 검사는 전처리에서 한다.
"""

import numpy as np


RAISE_THRESHOLD = 0.3   # 쉬는 높이보다 이만큼(어깨 너비 단위) 올라가면 "올라감"
END_THRESHOLD = 0.15    # 양손 모두 쉬는 높이 + 이 값보다 낮으면 "내려감" 
CONSECUTIVE = 3         # 연속 프레임 수

RIGHT_SHOULDER = 44
LEFT_SHOULDER = 45
MIN_SHOULDER_WIDTH = 1e-6

STATE_WAITING = "waiting"         # 구간 시작 대기
STATE_IN_SEGMENT = "in_segment"   # 구간 진행 중


def wrist_heights(xy, wrist_xy):
    """
    양손 손목 높이를 어깨 너비 단위로 구한다.

    xy       : (46, 2) 이번 프레임 좌표 (어깨 44, 45번 슬롯을 쓴다)
    wrist_xy : (2, 2)  Pose 손목 [오른손목, 왼손목]
    반환     : (오른손 높이, 왼손 높이). 어깨 너비가 0에 가까우면 None
    """
    right_shoulder = xy[RIGHT_SHOULDER]
    left_shoulder = xy[LEFT_SHOULDER]
    shoulder_center_y = (right_shoulder[1] + left_shoulder[1]) / 2.0
    shoulder_width = float(np.linalg.norm(right_shoulder - left_shoulder))
    if shoulder_width < MIN_SHOULDER_WIDTH:
        return None

    right_height = (shoulder_center_y - wrist_xy[0, 1]) / shoulder_width
    left_height = (shoulder_center_y - wrist_xy[1, 1]) / shoulder_width
    return right_height, left_height


class SegmentTrigger:
    """
    사용법
        trigger = SegmentTrigger()
        # 카운트다운 직후: True가 나올 때까지 매 프레임 호출
        trigger.calibrate(xy, pose_missing, wrist_xy)
        # 그 다음부터 매 프레임 호출. 구간이 끝난 프레임에서만 결과를 돌려준다
        segment = trigger.update(xy, right_missing, left_missing, pose_missing, wrist_xy)
        if segment is not None:
            seg_xy, seg_right_missing, seg_left_missing, seg_pose_missing = segment
            # 프레임 번호는 구간 안 순번이므로 np.arange(len(seg_xy)) 를 전처리에 넘긴다
    """

    def __init__(self):
        self.rest_heights = None   # (오른손 쉬는 높이, 왼손 쉬는 높이)
        self._reset_segment()

    def _reset_segment(self):
        """구간 상태를 비운다. 쉬는 높이는 그대로 둔다."""
        self.state = STATE_WAITING
        self.up_count = 0          # 시작 판정용 연속 "올라감" 수
        self.down_count = 0        # 끝 판정용 연속 "내려감" 수
        self._clear_buffer()

    def is_calibrated(self):
        return self.rest_heights is not None

    def calibrate(self, xy, pose_missing, wrist_xy):
        """
        쉬는 높이를 저장한다. Pose가 잡히지 않은 프레임이면 저장하지 않고 False.
        다시 캘리브레이션하려면 새 SegmentTrigger 를 만든다.
        """
        if pose_missing:
            return False
        heights = wrist_heights(xy, wrist_xy)
        if heights is None:
            return False
        self.rest_heights = heights
        return True

    def update(self, xy, right_missing, left_missing, pose_missing, wrist_xy):
        """
        프레임 하나를 넣는다.

        반환: 구간이 끝난 프레임이면 (xy (T,46,2), right_missing (T,), left_missing (T,), pose_missing (T,))
              나머지 프레임은 None
        """
        if not self.is_calibrated():
            raise RuntimeError("calibrate() 가 먼저 성공해야 합니다.")

        # 이번 프레임의 판정: True(올라감) / False(올라가지 않음) / None(높이를 못 잼)
        is_up = None
        is_down = None
        heights = None
        if not pose_missing:
            heights = wrist_heights(xy, wrist_xy)
        if heights is not None:
            right_rise = heights[0] - self.rest_heights[0]
            left_rise = heights[1] - self.rest_heights[1]
            is_up = (right_rise >= RAISE_THRESHOLD) or (left_rise >= RAISE_THRESHOLD)  # 한 손이라도
            is_down = (right_rise < END_THRESHOLD) and (left_rise < END_THRESHOLD)      # 양손 모두

        if self.state == STATE_WAITING:
            self._update_waiting(xy, right_missing, left_missing, pose_missing, is_up)
            return None

        # 구간 진행 중: 결측 프레임도 버퍼에 넣는다
        self._append(xy, right_missing, left_missing, pose_missing, is_up)
        if is_down is None:
            return None                     # 높이를 못 잰 프레임은 건너뛴다
        if is_down:
            self.down_count += 1
        else:
            self.down_count = 0

        if self.down_count < CONSECUTIVE:
            return None

        segment = self._cut_segment()
        self._reset_segment()
        return segment

    def _update_waiting(self, xy, right_missing, left_missing, pose_missing, is_up):
        """시작 대기 중: 연속으로 올라간 프레임을 버퍼에 모으다가 3번이 되면 구간을 시작한다."""
        if is_up is None:
            # 높이를 못 잰 프레임은 건너뛴다. 이미 세는 중이면 구간에 들어갈 수 있으니 버퍼에는 넣는다
            if self.up_count > 0:
                self._append(xy, right_missing, left_missing, pose_missing, is_up)
            return

        if not is_up:
            # 연속이 끊기면 모아둔 프레임을 버린다
            self.up_count = 0
            self._clear_buffer()
            return

        self.up_count += 1
        self._append(xy, right_missing, left_missing, pose_missing, is_up)
        if self.up_count >= CONSECUTIVE:
            self.state = STATE_IN_SEGMENT   # 버퍼 첫 프레임 = 연속 3프레임 중 첫 번째
            self.down_count = 0

    def _cut_segment(self):
        """
        끝 위치를 학습과 같은 규칙으로 정한다.
        버퍼를 뒤에서부터 훑어 "올라감" 프레임이 3번 연속되는 곳을 찾고,
        그 3프레임 중 (뒤에서 본) 첫 번째, 즉 가장 늦은 프레임까지 남긴다.
        높이를 못 잰 프레임(None)은 건너뛰고 센다.
        """
        end_index = len(self.buffer_is_up) - 1
        count = 0
        last_up_index = None
        for i in range(len(self.buffer_is_up) - 1, -1, -1):
            is_up = self.buffer_is_up[i]
            if is_up is None:
                continue
            if is_up:
                if count == 0:
                    last_up_index = i
                count += 1
                if count >= CONSECUTIVE:
                    end_index = last_up_index
                    break
            else:
                count = 0

        # 시작할 때 연속 3프레임이 있었으므로 위 반복에서 항상 찾는다
        keep = end_index + 1
        return (
            np.array(self.buffer_xy[:keep]),
            np.array(self.buffer_right_missing[:keep], dtype=bool),
            np.array(self.buffer_left_missing[:keep], dtype=bool),
            np.array(self.buffer_pose_missing[:keep], dtype=bool),
        )

    def _append(self, xy, right_missing, left_missing, pose_missing, is_up):
        self.buffer_xy.append(xy.copy())
        self.buffer_right_missing.append(right_missing)
        self.buffer_left_missing.append(left_missing)
        self.buffer_pose_missing.append(pose_missing)
        self.buffer_is_up.append(is_up)

    def _clear_buffer(self):
        """구간 버퍼 (프레임마다 하나씩 추가)를 비운다."""
        self.buffer_xy = []
        self.buffer_right_missing = []
        self.buffer_left_missing = []
        self.buffer_pose_missing = []
        self.buffer_is_up = []     # 끝 위치 자를 때 쓴다. True / False / None(높이를 못 잰 프레임)
