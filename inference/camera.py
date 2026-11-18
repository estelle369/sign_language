"""
웹캠 캡처 스레드
"""

import threading
import time

import cv2


class CameraStream:
    """
    사용법
        camera = CameraStream(0)
        camera.start()
        last_id = -1
        while ...:
            frame, last_id, timestamp_ms = camera.read(last_id)   # 새 프레임이 올 때까지 기다린다
            if frame is None:
                break                                              # 카메라가 멈춤
        camera.stop()
    """

    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.capture = None
        self.thread = None
        self.running = False

        # 아래 값들은 캡처 스레드와 처리 쪽이 같이 쓰므로 condition(잠금)으로 보호한다
        self.condition = threading.Condition()
        self.frame = None
        self.frame_id = -1          # 프레임을 받을 때마다 1씩 늘어난다. 건너뛴 프레임 수를 셀 때도 쓴다
        self.timestamp_ms = 0       # 프레임을 받은 시각 (start() 기준, ms). MediaPipe VIDEO 모드에 넘긴다
        self.start_time = 0.0

    def start(self):
        """카메라를 열고 캡처 스레드를 시작한다. 카메라를 열 수 없으면 RuntimeError."""
        self.capture = cv2.VideoCapture(self.camera_index)
        if not self.capture.isOpened():
            raise RuntimeError(f"카메라를 열 수 없습니다 (번호 {self.camera_index})")

        self.start_time = time.time()
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)  # daemon: 프로그램이 끝나면 같이 끝난다
        self.thread.start()

    def _run(self):
        """캡처 스레드: 카메라에서 계속 읽어 가장 최근 프레임으로 덮어쓴다."""
        while self.running:
            ok, frame = self.capture.read()
            if not ok:
                break
            timestamp_ms = int((time.time() - self.start_time) * 1000)
            with self.condition:
                self.frame = frame
                self.frame_id += 1
                self.timestamp_ms = timestamp_ms
                self.condition.notify_all()     # read() 에서 기다리는 쪽을 깨운다

        # 카메라가 멈췄거나 stop() 이 불렸다: 기다리는 쪽이 계속 기다리지 않도록 깨운다
        with self.condition:
            self.running = False
            self.condition.notify_all()

    def read(self, last_id, timeout_seconds=1.0):
        """
        last_id 보다 새로운 프레임을 돌려준다. 아직 없으면 올 때까지 기다린다.
        같은 프레임을 두 번 처리하지 않기 위해 마지막으로 받은 frame_id 를 넘긴다.

        반환: (frame, frame_id, timestamp_ms). 카메라가 멈췄거나 timeout 이면 (None, last_id, 0)
        """
        with self.condition:
            got_new = self.condition.wait_for(
                lambda: self.frame_id > last_id or not self.running,
                timeout=timeout_seconds,
            )
            if not got_new or not self.running or self.frame_id <= last_id:
                return None, last_id, 0
            return self.frame, self.frame_id, self.timestamp_ms

    def stop(self):
        """캡처 스레드를 멈추고 카메라를 닫는다."""
        self.running = False
        if self.thread is not None:
            self.thread.join(timeout=2.0)
            self.thread = None
        if self.capture is not None:
            self.capture.release()
            self.capture = None
