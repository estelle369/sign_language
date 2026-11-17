import unittest
from unittest.mock import Mock, patch

import numpy as np
from PyQt5.QtCore import QObject, QRect, Qt, pyqtSignal
from PyQt5.QtWidgets import QApplication

from dual_monitor import GameWindow, show_exhibition


class FakeRecognitionThread(QObject):
    word_recognized = pyqtSignal(str, float)
    error_occurred = pyqtSignal(str)
    frame_ready = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.stopped = False

    def start(self):
        pass

    def stop(self):
        self.stopped = True


class DualMonitorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        recognition_patch = patch(
            "views.real_game.game_view.RecognitionThread", FakeRecognitionThread)
        recognition_patch.start()
        self.addCleanup(recognition_patch.stop)
        self.window = GameWindow()

    def tearDown(self):
        self.window.close()
        self.window.camera_window.deleteLater()
        self.window.deleteLater()
        self.app.processEvents()

    def show_windows(self):
        show_exhibition(self.window, [self.app.primaryScreen()])
        self.app.processEvents()

    def test_independent_always_on_top_windows(self):
        self.show_windows()
        for window in (self.window, self.window.camera_window):
            self.assertTrue(window.isWindow())
            self.assertTrue(window.isVisible())
            self.assertTrue(window.windowFlags() & Qt.WindowStaysOnTopHint)
        self.assertIsNot(self.window.windowHandle(), self.window.camera_window.windowHandle())
        self.assertEqual(len(self.window.game_view.word_widgets), 24)

    def test_shared_frame_displays_without_second_capture(self):
        with patch("inference.camera.cv2.VideoCapture") as capture:
            self.show_windows()
            frame = np.full((120, 160, 3), (0, 0, 255), dtype=np.uint8)
            self.window.game_view.recognition_thread.frame_ready.emit(frame)
            self.app.processEvents()
            image = self.window.camera_window._image
            self.assertEqual(image.pixelColor(0, 0).getRgb(), (255, 0, 0, 255))
            capture.assert_not_called()

    def assert_windows_closed(self, thread):
        self.app.processEvents()
        self.assertFalse(self.window.isVisible())
        self.assertFalse(self.window.camera_window.isVisible())
        self.assertTrue(thread.stopped)

    def test_closing_game_window_stops_both(self):
        self.show_windows()
        thread = self.window.game_view.recognition_thread
        self.window.close()
        self.assert_windows_closed(thread)

    def test_closing_camera_window_stops_both(self):
        self.show_windows()
        thread = self.window.game_view.recognition_thread
        self.window.camera_window.close()
        self.assert_windows_closed(thread)

    def test_main_menu_button_closes_both(self):
        self.show_windows()
        self.window.game_view.btn_top_main.click()
        self.assertFalse(self.window.isVisible())
        self.assertFalse(self.window.camera_window.isVisible())

    def test_screen_selection_supports_negative_monitor_coordinates(self):
        camera_screen, game_screen = Mock(), Mock()
        camera_screen.availableGeometry.return_value = QRect(-1920, 0, 1920, 1040)
        game_screen.availableGeometry.return_value = QRect(0, 100, 2560, 1340)
        window = Mock()
        show_exhibition(window, [camera_screen, game_screen])
        camera = window.camera_window
        camera.windowHandle().setScreen.assert_called_once_with(camera_screen)
        window.windowHandle().setScreen.assert_called_once_with(game_screen)
        self.assertEqual(camera.move.call_args.args[0], camera_screen.availableGeometry().topLeft())
        self.assertEqual(window.move.call_args.args[0], game_screen.availableGeometry().topLeft())
        camera.showMaximized.assert_called_once()
        window.showMaximized.assert_called_once()

    def test_single_monitor_uses_non_overlapping_coordinates(self):
        screen = Mock()
        screen.availableGeometry.return_value = QRect(100, 50, 1800, 1000)
        window = Mock()
        show_exhibition(window, [screen])
        window.camera_window.resize.assert_called_once_with(600, 1000)
        window.move.assert_called_once_with(700, 50)
        window.resize.assert_called_once_with(1200, 1000)
        window.camera_window.show.assert_called_once()
        window.show.assert_called_once()


if __name__ == "__main__":
    unittest.main()
