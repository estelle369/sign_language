"""
게임용 수어 인식 스레드

    캡처 스레드(CameraStream) → MediaPipe → 손목 트리거 → 전처리 → 추론 모델 → 판정

사용법 (게임 화면에서)
    thread = RecognitionThread()
    thread.word_recognized.connect(...)    # 확률 0.5 이상으로 인식한 단어만 온다
    thread.error_occurred.connect(...)     # 카메라·모델을 열지 못했을 때
    thread.start()                         # 카운트다운 시작과 함께. 모델을 불러오고 카메라를 켠다
    thread.request_calibration()           # 카운트다운 "1"이 끝난 직후. 다음 프레임부터 쉬는 높이를 잰다
    thread.stop()                          # 게임이 끝나거나 화면을 나갈 때. 카메라를 끈다
"""

import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal

from inference import mediapipe_extractor, predictor, preprocessor
from inference.camera import CameraStream
from inference.trigger import SegmentTrigger

CAMERA_INDEX = 0
CAMERA_READ_TIMEOUT_SECONDS = 3.0   # 카메라를 켠 직후 첫 프레임이 늦게 올 수 있어 넉넉하게 둔다


class RecognitionThread(QThread):

    word_recognized = pyqtSignal(str, float)   # (단어, 최대 확률)
    error_occurred = pyqtSignal(str)           # 오류 메시지

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
        잘라낸 구간 하나를 전처리하고 단어를 예측한다.
        반환: (단어, 최대 확률). 결측으로 인식하지 않거나 확률이 기준 미만이면 단어는 None
        """
        seg_xy, seg_right_missing, seg_left_missing, seg_pose_missing = segment
        frame_numbers = np.arange(len(seg_xy), dtype=np.float64)   # 구간 안 순번이 시간축이다
        sequence = preprocessor.preprocess_segment(
            frame_numbers, seg_xy, seg_right_missing, seg_left_missing, seg_pose_missing)
        if sequence is None:
            return None, 0.0
        return predictor.predict_word(model, label_names, sequence)
