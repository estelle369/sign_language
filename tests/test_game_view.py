import unittest
from unittest.mock import Mock, patch

import cv2
import numpy as np
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from inference.camera import CameraStream
from views.real_game.game_view import GameView


class FakeRecognitionThread(QObject):
    word_recognized = pyqtSignal(str, float)
    error_occurred = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.stopped = False

    def start(self):
        pass

    def stop(self):
        self.stopped = True

    def request_calibration(self):
        pass

    def read_preview(self, last_id):
        if last_id >= 0:
            return None, last_id, 0
        return np.full((120, 160, 3), (0, 0, 255), dtype=np.uint8), 0, 1


class GameViewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)

    def setUp(self):
        self.recognition_patch = patch(
            "views.real_game.game_view.RecognitionThread", FakeRecognitionThread)
        self.recognition_patch.start()
        self.addCleanup(self.recognition_patch.stop)
        self.view = GameView()
        self.view.show()
        self.app.processEvents()

    def tearDown(self):
        self.view.close()
        self.view.deleteLater()
        self.app.processEvents()

    def test_split_and_grid_at_exhibition_resolutions(self):
        for width, height in ((1000, 700), (1280, 800), (1920, 1080)):
            with self.subTest(resolution=(width, height)):
                self.view.resize(width, height)
                self.app.processEvents()
                left = self.view.camera_panel.geometry()
                right = self.view.game_panel.geometry()
                self.assertAlmostEqual(left.width() / (left.width() + right.width()), 0.4, delta=0.002)
                self.assertEqual(left.right() + 1, right.left())
                self.assertEqual(left.top(), right.top())
                self.assertEqual(left.height(), right.height())
                self.assertEqual(len(self.view.word_widgets), 24)
                for index in range(24):
                    item = self.view.board_grid.itemAtPosition(index // 4, index % 4)
                    self.assertIsNotNone(item)
                    chip = item.widget()
                    self.assertTrue(self.view.game_board_frame.rect().contains(chip.geometry()))
                    self.assertGreaterEqual(chip.width(), chip.minimumSizeHint().width())
                    self.assertGreaterEqual(chip.height(), chip.minimumSizeHint().height())

    def test_preview_converts_bgr_and_fits_label(self):
        self.view._update_camera_preview()
        preview = self.view.camera_preview
        self.assertEqual(preview._image.pixelColor(0, 0).getRgb(), (255, 0, 0, 255))
        self.assertLessEqual(preview.pixmap().width(), preview.width())
        self.assertLessEqual(preview.pixmap().height(), preview.height())
        self.assertEqual(self.view._preview_frame_id, 0)

    def test_camera_error_keeps_window_open_and_allows_retry(self):
        old_thread = self.view.recognition_thread
        old_thread.error_occurred.emit("카메라 연결 실패")
        self.assertTrue(self.view.isVisible())
        self.assertTrue(old_thread.stopped)
        self.assertIsNone(self.view.recognition_thread)
        self.assertFalse(self.view.game_timer.isActive())
        self.assertFalse(self.view.countdown_timer.isActive())
        self.assertFalse(self.view.preview_timer.isActive())
        self.assertFalse(self.view.result_container.isHidden())
        self.assertEqual(self.view.recognition_status.text(), "카메라 연결 실패")
        self.view._reset_game_state()
        self.assertIsNotNone(self.view.recognition_thread)
        self.assertTrue(self.view.result_container.isHidden())
        self.assertTrue(self.view.preview_timer.isActive())

    def test_correct_word_disappears_without_reflow_and_retry_is_safe(self):
        self.view.is_playing = True
        word = self.view.all_words[0]
        chip = self.view.word_widgets[word]
        neighbor = self.view.word_widgets[self.view.all_words[1]]
        old_geometry = neighbor.geometry()
        self.view._on_word_recognized(word, 0.9)
        QTest.qWait(350)
        self.assertTrue(chip.isHidden())
        self.assertEqual(neighbor.geometry(), old_geometry)
        self.assertEqual(self.view.score, 100)
        self.assertEqual(len(self.view.remaining_words), 23)
        self.view.is_playing = True
        self.view._on_word_recognized(self.view.all_words[1], 0.9)
        self.view._reset_game_state()
        QTest.qWait(350)
        self.assertEqual(self.view.score, 0)
        self.assertTrue(all(not chip.isHidden() for chip in self.view.word_widgets.values()))

    def test_hiding_view_stops_capture_and_timers(self):
        thread = self.view.recognition_thread
        self.view.hide()
        self.assertTrue(thread.stopped)
        self.assertFalse(self.view.preview_timer.isActive())
        self.assertFalse(self.view.countdown_timer.isActive())


class CameraFailureTests(unittest.TestCase):
    def test_failed_open_releases_device(self):
        capture = Mock()
        capture.isOpened.return_value = False
        camera = CameraStream()
        with patch("inference.camera.cv2.VideoCapture", return_value=capture):
            with self.assertRaisesRegex(RuntimeError, "카메라 연결 실패"):
                camera.start()
        capture.release.assert_called_once()
        self.assertIsNone(camera.capture)

    def test_opencv_open_exception_becomes_reportable_error(self):
        with patch("inference.camera.cv2.VideoCapture", side_effect=cv2.error("disconnected")):
            with self.assertRaisesRegex(RuntimeError, "카메라 연결 실패"):
                CameraStream().start()

    def test_read_exception_stops_capture_and_wakes_consumers(self):
        camera = CameraStream()
        camera.capture = Mock()
        camera.capture.read.side_effect = cv2.error("disconnected")
        camera.running = True
        camera._run()
        self.assertFalse(camera.running)
        self.assertIn("disconnected", camera.error_message)
        self.assertEqual(camera.read(-1, timeout_seconds=0), (None, -1, 0))
        camera.stop()


if __name__ == "__main__":
    unittest.main()
