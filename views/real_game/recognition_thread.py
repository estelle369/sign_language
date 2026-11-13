"""
게임용 수어 인식 스레드

    캡처 스레드(CameraStream) → MediaPipe → 손목 트리거 → 전처리 → 추론 모델 → 판정

사용법 (게임 화면에서)
    thread = RecognitionThread()
    thread.word_recognized.connect(...)
    thread.error_occurred.connect(...)     # 카메라·모델을 열지 못했을 때
    thread.start()                         # 카운트다운 시작과 함께. 모델을 불러오고 카메라를 켠다
    thread.request_calibration()           # 카운트다운 "1"이 끝난 직후. 다음 프레임부터 쉬는 높이를 잰다
    thread.stop()                          # 게임이 끝나거나 화면을 나갈 때. 카메라를 끈다
"""

import cv2
import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

from inference import mediapipe_extractor, predictor, preprocessor
from inference.camera import CameraStream
from inference.trigger import SegmentTrigger

CAMERA_INDEX = 0
CAMERA_READ_TIMEOUT_SECONDS = 3.0   # 카메라를 켠 직후 첫 프레임이 늦게 올 수 있어 넉넉하게 둔다

# 화면에 관절을 그릴 때 쓰는 값 (테스트용 표시)
# 손 21점 연결선 (MediaPipe 손 번호 기준: 0 손목, 1~4 엄지, 5~8 검지, 9~12 중지, 13~16 약지, 17~20 새끼)
HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (0, 17), (17, 18), (18, 19), (19, 20),
]
RIGHT_HAND_COLOR = (0, 165, 255)   # BGR 주황: 오른손 슬롯(0~20)
LEFT_HAND_COLOR = (255, 200, 0)    # BGR 하늘색: 왼손 슬롯(21~41)
POSE_COLOR = (200, 200, 200)       # 회색: 어깨·팔꿈치 (Pose)
WRIST_COLOR = (0, 0, 255)          # 빨강: Pose 손목 (트리거용)


class RecognitionThread(QThread):

    word_recognized = pyqtSignal(str, float)   # (단어, 최대 확률)
    error_occurred = pyqtSignal(str)           # 오류 메시지
    frame_ready = pyqtSignal(np.ndarray)       # 관절을 그린 웹캠 화면 (BGR, 좌우 반전)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._calibration_requested = False

    def start(self):
        """스레드를 시작한다. stop() 이 run() 보다 먼저 불려도 멈추도록 여기서 실행 표시를 한다."""
        self._running = True
        super().start()

    def stop(self):
        """반복을 멈추고 스레드가 끝날 때까지 기다린다 (카메라가 꺼진다)."""
        self._running = False
        self.wait()

    def request_calibration(self):
        """
        다음 프레임부터 쉬는 높이를 새로 잰다.
        게임 화면(메인 스레드)에서 부르고 run()(이 스레드)에서 읽는다. bool 하나라 따로 잠그지 않는다.
        """
        self._calibration_requested = True

    def run(self):
        """스레드 본체: start() 를 부르면 Qt가 새 스레드에서 이 함수를 실행한다."""
        # MediaPipe 객체는 만든 스레드에서 써야 하므로 여기서 만든다
        try:
            model = predictor.load_model()
            label_names = predictor.load_label_names()
            hand_landmarker, pose_landmarker = mediapipe_extractor.create_landmarkers()
        except Exception as e:
            self.error_occurred.emit(f"모델을 불러오지 못했습니다: {e}")
            return

        camera = CameraStream(CAMERA_INDEX)
        try:
            camera.start()
        except RuntimeError as e:
            hand_landmarker.close()
            pose_landmarker.close()
            self.error_occurred.emit(str(e))
            return

        trigger = None      # 캘리브레이션 요청이 오면 만든다
        last_id = -1

        # fps 측정 (약 1초마다 갱신. 시각은 카메라가 프레임을 받은 시각 timestamp_ms 를 쓴다)
        #   카메라 fps : 웹캠이 실제로 보내는 프레임 수 (frame_id 증가량)
        #   처리 fps   : MediaPipe 까지 처리한 프레임 수. 처리가 느리면 카메라 fps 보다 낮고, 그만큼 프레임을 건너뛴다
        fps_start_ms = -1
        fps_start_id = 0
        processed_count = 0
        camera_fps = 0.0
        processed_fps = 0.0
        try:
            while self._running:
                frame, last_id, timestamp_ms = camera.read(last_id, CAMERA_READ_TIMEOUT_SECONDS)
                if frame is None:
                    if self._running:
                        self.error_occurred.emit("카메라에서 프레임을 받지 못했습니다.")
                    break

                # 캘리브레이션 전에도 MediaPipe 에는 계속 넣는다 (VIDEO 모드 추적이 이어지도록)
                xy, right_missing, left_missing, pose_missing, wrist_xy = mediapipe_extractor.extract_keypoints(
                    hand_landmarker, pose_landmarker, frame, timestamp_ms)

                if fps_start_ms < 0:
                    fps_start_ms = timestamp_ms
                    fps_start_id = last_id
                processed_count += 1
                elapsed_ms = timestamp_ms - fps_start_ms
                if elapsed_ms >= 1000:
                    camera_fps = (last_id - fps_start_id) * 1000.0 / elapsed_ms
                    processed_fps = processed_count * 1000.0 / elapsed_ms
                    fps_start_ms = timestamp_ms
                    fps_start_id = last_id
                    processed_count = 0

                image = draw_keypoints(frame, xy, right_missing, left_missing, pose_missing, wrist_xy)
                fps_text = f"camera {camera_fps:.1f} fps / processed {processed_fps:.1f} fps"
                cv2.putText(image, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 4)   # 검은 테두리
                cv2.putText(image, fps_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
                self.frame_ready.emit(image)

                if self._calibration_requested:
                    self._calibration_requested = False
                    trigger = SegmentTrigger()
                if trigger is None:
                    continue

                if not trigger.is_calibrated():
                    trigger.calibrate(xy, pose_missing, wrist_xy)   # Pose가 안 잡히면 다음 프레임에서 다시
                    continue

                segment = trigger.process_frame(xy, right_missing, left_missing, pose_missing, wrist_xy)
                if segment is None:
                    continue

                word, prob = self._recognize(model, label_names, segment)
                if word is not None:
                    self.word_recognized.emit(word, prob)
        finally:
            camera.stop()
            hand_landmarker.close()
            pose_landmarker.close()

    def _recognize(self, model, label_names, segment):
        """
        잘라낸 구간 하나를 전처리하고 단어를 예측한다. 결과는 터미널에 로그로 남긴다.
        반환: (단어, 최대 확률). 결측으로 인식하지 않거나 확률이 기준 미만이면 단어는 None
        """
        seg_xy, seg_right_missing, seg_left_missing, seg_pose_missing = segment
        frame_numbers = np.arange(len(seg_xy), dtype=np.float64)   # 구간 안 순번이 시간축이다
        sequence = preprocessor.preprocess_segment(
            frame_numbers, seg_xy, seg_right_missing, seg_left_missing, seg_pose_missing)
        if sequence is None:
            print(f"[인식] 구간 {len(seg_xy)}프레임 → 인식 안 함 (전처리 제외) | 최장 연속 결측: "
                  f"오른손 {preprocessor.longest_missing_run(seg_right_missing)}, "
                  f"왼손 {preprocessor.longest_missing_run(seg_left_missing)}, "
                  f"Pose {preprocessor.longest_missing_run(seg_pose_missing)} "
                  f"(기준: {preprocessor.MAX_MISSING_RUN} 초과면 제외)", flush=True)
            return None, 0.0

        probabilities = predictor.predict_probabilities(model, sequence)
        word, prob = predictor.pick_word(label_names, probabilities)

        top = predictor.top_words(label_names, probabilities, count=3)
        top_text = " | ".join(f"{rank + 1}위 {name} {p:.2f}" for rank, (name, p) in enumerate(top))
        result_text = "판정" if word is not None else f"기준 미만 ({predictor.PROB_THRESHOLD})"
        print(f"[인식] 구간 {len(seg_xy)}프레임 → {result_text} | {top_text}", flush=True)
        return word, prob


def draw_keypoints(frame, xy, right_missing, left_missing, pose_missing, wrist_xy):
    """
    웹캠 프레임 위에 MediaPipe가 뽑은 관절을 그린다 (모델에 들어가는 46슬롯 + 트리거용 Pose 손목).
    좌표를 그린 뒤 좌우 반전해서 돌려준다 (거울처럼 보이게). MediaPipe 입력 프레임은 반전하지 않는다.
    """
    image = frame.copy()

    hands = [
        (0, right_missing, RIGHT_HAND_COLOR),    # 오른손 슬롯 0~20
        (21, left_missing, LEFT_HAND_COLOR),     # 왼손 슬롯 21~41
    ]
    for slot_start, missing, color in hands:
        if missing:
            continue
        points = xy[slot_start:slot_start + 21].astype(int)
        for a, b in HAND_CONNECTIONS:
            cv2.line(image, tuple(points[a]), tuple(points[b]), color, 2)
        for p in points:
            cv2.circle(image, tuple(p), 4, color, -1)

    if not pose_missing:
        right_elbow, left_elbow, right_shoulder, left_shoulder = xy[42:46].astype(int)
        cv2.line(image, tuple(right_shoulder), tuple(left_shoulder), POSE_COLOR, 2)
        cv2.line(image, tuple(right_shoulder), tuple(right_elbow), POSE_COLOR, 2)
        cv2.line(image, tuple(left_shoulder), tuple(left_elbow), POSE_COLOR, 2)
        for p in (right_elbow, left_elbow, right_shoulder, left_shoulder):
            cv2.circle(image, tuple(p), 6, POSE_COLOR, -1)
        for p in wrist_xy.astype(int):
            cv2.circle(image, tuple(p), 8, WRIST_COLOR, 2)

    return cv2.flip(image, 1)
