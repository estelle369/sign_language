"""
게임용 수어 인식 스레드

    캡처 스레드(CameraStream) → MediaPipe → 손목 트리거 → 전처리 → 추론 모델 → 판정

사용법 (게임 화면에서)
    thread = RecognitionThread()
    thread.word_recognized.connect(...)
    thread.error_occurred.connect(...)     # 카메라·모델을 열지 못했을 때
    thread.frame_ready.connect(...)        # 실시간 웹캠 화면을 메인으로 전달
    thread.body_status_checked.connect(...) # 어깨/손이 실제로 인식되었는지 전달 (True/False)
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
    
    # 🌟 [신규 추가 1] 실시간 웹캠 프레임을 메인 화면에 띄우기 위한 시그널
    frame_ready = pyqtSignal(np.ndarray)
    
    # 🌟 [신규 추가 2] 관람객의 어깨와 손이 실제로 인식되었는지(True/False) 메인으로 보내는 시그널
    body_status_checked = pyqtSignal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._calibration_requested = False

    def start(self):
        """스레드를 시작한다."""
        self._running = True
        super().start()

    def stop(self):
        """반복을 멈추고 스레드가 끝날 때까지 기다린다 (카메라가 꺼진다)."""
        self._running = False
        self.wait()

    def request_calibration(self):
        """다음 프레임부터 쉬는 높이를 새로 잰다."""
        self._calibration_requested = True

    def run(self):
        """스레드 본체: start() 를 부르면 Qt가 새 스레드에서 이 함수를 실행한다."""
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

                # 🌟 [프레임 전달] 카메라 영상을 메인 화면의 실시간 미리보기로 발사!
                self.frame_ready.emit(frame)

                # MediaPipe 키포인트 추출 (어깨, 손 등)
                xy, right_missing, left_missing, pose_missing, wrist_xy = mediapipe_extractor.extract_keypoints(
                    hand_landmarker, pose_landmarker, frame, timestamp_ms)

                # 🌟 [인식 판정] pose_missing이 False이면 관람객의 신체가 정상적으로 감지된 것으로 판정
                is_detected = (not pose_missing) if isinstance(pose_missing, (bool, np.bool_)) else (pose_missing is not None and not np.any(pose_missing))
                
                # 메인 화면으로 "지금 사람이 잘 서 있는지" 상태를 실시간 보고!
                self.body_status_checked.emit(is_detected)

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
        """잘라낸 구간 하나를 전처리하고 단어를 예측한다."""
        seg_xy, seg_right_missing, seg_left_missing, seg_pose_missing = segment
        frame_numbers = np.arange(len(seg_xy), dtype=np.float64)   
        sequence = preprocessor.preprocess_segment(
            frame_numbers, seg_xy, seg_right_missing, seg_left_missing, seg_pose_missing)
        if sequence is None:
            return None, 0.0

        probabilities = predictor.predict_probabilities(model, sequence)
        word, prob = predictor.pick_word(label_names, probabilities)
        return word, prob