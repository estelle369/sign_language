import sys

import cv2
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QApplication, QLabel, QScrollArea, QSizePolicy

from views.real_game.game_view import GameView


class CameraWindow(QLabel):
    closed = pyqtSignal()

    def __init__(self):
        super().__init__("카메라 연결 준비 중")
        self.setWindowTitle("수어 게임 - 카메라")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet("background: black; color: white;")
        self.setMinimumSize(160, 120)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self._image = QImage()

    def reset_preview(self):
        self._image = QImage()
        self.clear()
        self.setText("카메라 연결 준비 중")

    def show_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width = rgb.shape[:2]
        self._image = QImage(
            rgb.data, width, height, rgb.strides[0], QImage.Format_RGB888).copy()
        self._render_frame()

    def _render_frame(self):
        if not self._image.isNull():
            self.setPixmap(QPixmap.fromImage(self._image).scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._render_frame()

    def closeEvent(self, event):
        super().closeEvent(event)
        self.closed.emit()


class PreviewGameView(GameView):
    def __init__(self, camera_window):
        self.camera_window = camera_window
        super().__init__()

    def _start_recognition(self):
        super()._start_recognition()
        self.camera_window.reset_preview()
        self.recognition_thread.frame_ready.connect(
            self.camera_window.show_frame, Qt.QueuedConnection)


class GameWindow(QScrollArea):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("수어 게임 - 문제")
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        self.setWidgetResizable(True)
        self.camera_window = CameraWindow()
        self.game_view = PreviewGameView(self.camera_window)
        self.setWidget(self.game_view)
        self.camera_window.closed.connect(self.close)
        self.game_view.request_main_menu.connect(self.close)

    def closeEvent(self, event):
        self.game_view.hide()
        self.camera_window.hide()
        super().closeEvent(event)


def show_exhibition(game_window, screens):
    camera_window = game_window.camera_window
    for window, screen in (
        (camera_window, screens[0]),
        (game_window, screens[1] if len(screens) > 1 else screens[0]),
    ):
        window.winId()
        window.windowHandle().setScreen(screen)
    camera_area = screens[0].availableGeometry()
    if len(screens) > 1:
        game_area = screens[1].availableGeometry()
        camera_window.move(camera_area.topLeft())
        camera_window.resize(camera_area.size())
        game_window.move(game_area.topLeft())
        game_window.resize(game_area.size())
        camera_window.showMaximized()
        game_window.showMaximized()
    else:
        camera_width = camera_area.width() // 3
        camera_window.move(camera_area.topLeft())
        camera_window.resize(camera_width, camera_area.height())
        game_window.move(camera_area.x() + camera_width, camera_area.y())
        game_window.resize(camera_area.width() - camera_width, camera_area.height())
        camera_window.show()
        game_window.show()


def main():
    app = QApplication(sys.argv)
    game_window = GameWindow()
    show_exhibition(game_window, app.screens())
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
