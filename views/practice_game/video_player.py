# OpenCV 기반 영상 프레임 재생 컨트롤러
import cv2
from PyQt5.QtCore import QTimer, pyqtSignal, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QLabel

class VideoPlayerWidget(QLabel):
    """
    OpenCV 영상 프레임을 받아 수어 시연 영상을 재생하는 커스텀 QLabel 위젯
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background-color: #1E1E1E; border-radius: 12px;")
        
        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)

    def load_video(self, video_path: str):
        """새로운 영상 파일을 로드합니다."""
        self.stop()
        
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            self.setText("영상을 불러올 수 없습니다.")
            return

        # 30ms 간격으로 프레임 갱신 (약 33fps)
        self.timer.start(30)

    def _update_frame(self):
        """QTimer 마다 호출되어 다음 프레임을 그립니다."""
        if self.cap is None or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret:
            # 영상이 끝나면 루프(무한 반복) 재생
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            return

        # BGR -> RGB 변환
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        
        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # 반응형 크기 조절: QLabel 크기에 맞추되 비율 유지 (KeepAspectRatio)
        pixmap = QPixmap.fromImage(q_img)
        scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(scaled_pixmap)

    def stop(self):
        """영상 재생 중지 및 리소스 해제"""
        if self.timer.isActive():
            self.timer.stop()
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None
        self.clear()

    def resizeEvent(self, event):
        """화면 크기가 변경될 때 비율 유지 반응형 적용"""
        super().resizeEvent(event)
        # 현재 프레임 재출력은 다음 _update_frame 타이머에서 자연스럽게 처리됨