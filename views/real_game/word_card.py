import sys
import logging
from PyQt5.QtWidgets import QFrame, QLabel, QHBoxLayout, QApplication, QGraphicsOpacityEffect, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, pyqtSignal, QPropertyAnimation, QParallelAnimationGroup
from PyQt5.QtGui import QFont, QColor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class WordCard(QFrame):

    popped_finished = pyqtSignal(str)

    def __init__(self, word: str, parent=None):
        super().__init__(parent)
        self.word = word
        self._is_popped = False

        self._init_ui()
        self._setup_animations()

    def _init_ui(self):
        self.setFixedSize(160, 52)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        
        self.word_label = QLabel(self.word, self)
        self.word_label.setFont(QFont("Pretendard", 16, QFont.Bold))
        self.word_label.setAlignment(Qt.AlignCenter)
        self.word_label.setStyleSheet("color: #334155; background: transparent;")
        
        layout.addWidget(self.word_label)

        # 은은한 그림자 효과 (흰색 카드 입체감 부여)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 20))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)

        self._apply_normal_style()

    def _apply_normal_style(self):
        """요청하신 흰색 불투명 배경 QSS"""
        self.setStyleSheet("""
            WordCard {
                background-color: rgba(255, 255, 255, 0.95);
                border: 1px solid #E2E8F0;
                border-radius: 26px;
            }
        """)

    def pop_animation(self):
        """정답 클릭/인식 시 노란색 하이라이트 후 사라짐"""
        if self._is_popped:
            return

        self._is_popped = True
        self.setStyleSheet("""
            WordCard {
                background-color: #FDE047;
                border: 2px solid #F59E0B;
                border-radius: 26px;
            }
        """)
        self.anim_group.start()

    def _setup_animations(self):
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.anim_fade = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim_fade.setDuration(350)
        self.anim_fade.setStartValue(1.0)
        self.anim_fade.setEndValue(0.0)

        self.anim_group = QParallelAnimationGroup()
        self.anim_group.addAnimation(self.anim_fade)
        self.anim_group.finished.connect(self._on_animation_finished)

    def _on_animation_finished(self):
        self.hide()
        self.popped_finished.emit(self.word)