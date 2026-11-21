import os
import unittest
from unittest.mock import patch

from PyQt5.QtGui import QFontDatabase
from PyQt5.QtWidgets import QApplication, QLabel

from views.practice_game.practice_view import PracticeView
from views.real_game.game_view import GameView


class TitleFontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        font_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "MonaS10.ttf")
        font_id = QFontDatabase.addApplicationFont(font_path)
        if font_id == -1:
            raise RuntimeError(f"Could not load font: {font_path}")
        cls.font_family = QFontDatabase.applicationFontFamilies(font_id)[0]

    def test_practice_title_font_and_center(self):
        with patch("views.practice_game.practice_view.VideoPlayerWidget.load_video"):
            view = PracticeView()
            self.addCleanup(view.close)
            title = next(label for label in view.findChildren(QLabel) if label.text() == "수어 연습 모드")
            self.assertEqual(title.font().family(), self.font_family)

            for width in (640, 1000, 1600):
                with self.subTest(width=width):
                    view.resize(width, 800)
                    view.show()
                    self.app.processEvents()
                    self.assertLessEqual(abs(title.x() + title.width() / 2 - view.width() / 2), 1)
                    self.assertLess(view.btn_back.geometry().right(), title.geometry().left())

    def test_game_title_font(self):
        view = GameView()
        self.addCleanup(view.close)
        self.assertEqual(view.title_label.font().family(), self.font_family)
