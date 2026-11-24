"""
게임용 수어 인식 스레드

    캡처 스레드(CameraStream) → MediaPipe → 손목 트리거 → 전처리 → 추론 모델 → 판정

사용법 (게임 화면에서)
    thread = RecognitionThread()
    thread.word_recognized.connect(...)    # 인식 안 함·기준 미만이면 단어가 "" 로 온다 (오답 처리)
    thread.error_occurred.connect(...)     # 카메라·모델을 열지 못했을 때
    thread.status_changed.connect(...)     # 상태가 바뀔 때. 캘리브레이션 전에는 position_check.POSITION_*,
                                           # 캘리브레이션 뒤에는 STATUS_* 중 하나
    thread.start()                         # 게임 화면에 들어올 때. 모델을 불러오고 카메라를 켠다
    thread.request_calibration()           # 카운트다운 "1"이 끝난 직후. 서 있는 위치가 통과인 첫 프레임에서
                                           # 쉬는 높이를 잰다
    thread.stop()                          # 게임이 끝나거나 화면을 나갈 때. 카메라를 끈다
"""

import numpy as np
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QImage

from inference import mediapipe_extractor, position_check, predictor, preprocessor
from inference.camera import CameraStream
from inference.trigger import STATE_IN_SEGMENT, SegmentTrigger

CAMERA_INDEX = 0
CAMERA_READ_TIMEOUT_SECONDS = 3.0   # 카메라를 켠 직후 첫 프레임이 늦게 올 수 있어 넉넉하게 둔다

# 화면에 보여 줄 인식 상태 (캘리브레이션이 끝난 뒤부터 보낸다. 그 전에는 position_check.POSITION_* 를 보낸다)
STATUS_NO_PERSON = "no_person"   # Pose(사람)가 안 잡힘
STATUS_WAITING = "waiting"       # 손을 올리기를 기다리는 중
STATUS_RECORDING = "recording"   # 구간 진행 중 (손을 올림 ~ 내림)

MIN_SEGMENT_FRAMES = 40             # 구간이 이 프레임 수 이하면 수어 동작으로 보지 않고 무시한다 (정답도 오답도 아님)


class RecognitionThread(QThread):

    word_recognized = pyqtSignal(str, float)   # (단어, 최대 확률). 인식 안 함·기준 미만이면 단어는 ""
    error_occurred = pyqtSignal(str)           # 오류 메시지
    frame_ready = pyqtSignal(QImage)
    status_changed = pyqtSignal(str)           # POSITION_* 또는 STATUS_*. 바뀔 때만 보낸다

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
        status = None       # 마지막으로 보낸 인식 상태
        try:
            while self._running:
                frame, last_id, timestamp_ms = camera.read(last_id, CAMERA_READ_TIMEOUT_SECONDS)
                if frame is None:
                    if self._running:
                        self.error_occurred.emit("카메라에서 프레임을 받지 못했습니다.")
                    break

                height, width = frame.shape[:2]
                image = QImage(
                    frame.data, width, height, frame.strides[0], QImage.Format_BGR888
                ).copy()
                self.frame_ready.emit(image)

                # 캘리브레이션 전에도 MediaPipe 에는 계속 넣는다 (VIDEO 모드 추적이 이어지도록)
                xy, right_missing, left_missing, pose_missing, wrist_xy, body = \
                    mediapipe_extractor.extract_keypoints_with_body(
                        hand_landmarker, pose_landmarker, frame, timestamp_ms)

                if self._calibration_requested:
                    self._calibration_requested = False
                    trigger = SegmentTrigger()

                # 캘리브레이션 전: 서 있는 위치를 판단해 화면에 알려 준다
                if trigger is None or not trigger.is_calibrated():
                    position = position_check.check_position(body, width, height)
                    status = self._emit_status(status, position)
                    # 위치가 통과일 때만 쉬는 높이를 잰다 (손목이 잘린 채로 재지 않도록)
                    if trigger is not None and position == position_check.POSITION_OK:
                        trigger.calibrate(xy, pose_missing, wrist_xy)
                    continue

                segment = trigger.process_frame(xy, right_missing, left_missing, pose_missing, wrist_xy)

                if trigger.state == STATE_IN_SEGMENT:
                    status = self._emit_status(status, STATUS_RECORDING)
                elif pose_missing:
                    status = self._emit_status(status, STATUS_NO_PERSON)
                else:
                    status = self._emit_status(status, STATUS_WAITING)

                if segment is None:
                    continue

                segment_frames = len(segment[0])
                if segment_frames <= MIN_SEGMENT_FRAMES:
                    print(f"[인식] 구간 {segment_frames}프레임 → 무시 "
                        f"(기준: {MIN_SEGMENT_FRAMES}프레임 이하)", flush=True)
                    continue

                word, prob = self._recognize(model, label_names, segment)
                self.word_recognized.emit(word if word is not None else "", prob)
        finally:
            camera.stop()
            hand_landmarker.close()
            pose_landmarker.close()

    def _emit_status(self, old_status, new_status):
        """상태가 바뀌었을 때만 화면에 보낸다. 반환: 새 상태"""
        if new_status != old_status:
            self.status_changed.emit(new_status)
        return new_status

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
