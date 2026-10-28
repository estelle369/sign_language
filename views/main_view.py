import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QApplication, QFrame, QGraphicsDropShadowEffect
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPainter, QPixmap, QFontDatabase

class MainView(QWidget):

    request_practice_mode = pyqtSignal()
    request_game_mode = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._load_custom_font()
        self._init_ui()

    def _load_custom_font(self):
        """프로젝트 폴더 내의 폰트 파일을 읽어와서 앱에 등록하는 함수"""
        font_filename = "MonaS10.ttf"  
        
        if os.path.exists(font_filename):
            font_id = QFontDatabase.addApplicationFont(font_filename)
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    MainView.CUSTOM_FONT_FAMILY = families[0]
                    return
        
        MainView.CUSTOM_FONT_FAMILY = "NanumGothic"

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(60, 60, 60, 60)
        main_layout.setSpacing(40)

        # 1. 상단 타이틀 영역 ("손끝으로 전하는 마음"은 삭제하고 부제목부터 시작)
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setSpacing(10)

        # 💡 "손끝으로 전하는 마음" title_label 코드는 여기서 완전히 삭제되었습니다!

        subtitle_label = QLabel("수어 학습 키오스크")
        subtitle_label.setFont(QFont(MainView.CUSTOM_FONT_FAMILY, 26, QFont.Bold)) # 글씨 크기를 살짝 키워 시선 집중
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #FF5A5F; background: transparent;")

        desc_label = QLabel("원하시는 모드를 선택하여 수어를 배워보고 게임에 도전해보세요!")
        desc_label.setFont(QFont(MainView.CUSTOM_FONT_FAMILY, 16))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #64748B; background: transparent; margin-top: 6px;")

        # 부제목과 설명만 레이아웃에 추가
        header_layout.addWidget(subtitle_label)
        header_layout.addWidget(desc_label)

        main_layout.addLayout(header_layout)
        main_layout.addStretch(1)

        # 2. 중앙 카드 선택 영역
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(40)
        cards_layout.setAlignment(Qt.AlignCenter)

        # 연습 모드 카드
        self.practice_card = self._create_mode_card(
            title="연습 모드",
            desc="차근차근 수어 동작을 보고<br>따라하며 학습합니다.",
            icon_path="practice_mainbg.png",  
            btn_text="학습 시작하기",
            callback=self.request_practice_mode.emit,
            is_highlighted=False
        )

        # 실전 게임 모드 카드 
        self.game_card = self._create_mode_card(
            title="실전 게임 모드",
            desc="25개의 수어 단어를<br>제한시간 내에 터뜨려보세요!",
            icon_path="real_bgimg.png", 
            btn_text="게임 도전하기",
            callback=self.request_game_mode.emit,
            is_highlighted=True
        )

        cards_layout.addWidget(self.practice_card)
        cards_layout.addWidget(self.game_card)

        main_layout.addLayout(cards_layout)
        main_layout.addStretch(1)

        self._apply_card_styles()

    def paintEvent(self, event):
        """메인 화면 전체 배경에 main_background.jpg를 창 크기에 맞게 꽉 채워 그림"""
        painter = QPainter(self)
        pixmap = QPixmap("main_background.jpg")
        
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter.drawPixmap(0, 0, scaled_pixmap)
        else:
            painter.fillRect(self.rect(), QColor("#F8FAFC"))

    def _create_mode_card(self, title: str, desc: str, btn_text: str, callback, icon_text: str = None, icon_path: str = None, is_highlighted: bool = False) -> QFrame:
        card = QFrame()
        card.setFixedSize(380, 320)
        card.setCursor(Qt.PointingHandCursor)
        card.setObjectName("modeCardHighlighted" if is_highlighted else "modeCard")
        
        card.mousePressEvent = lambda event: callback()

        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(12)
        layout.setContentsMargins(25, 25, 25, 25)

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent;")

        if icon_path:
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(130, 130, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label.setPixmap(scaled_pixmap)
            else:
                icon_label.setText("🎮")  
        elif icon_text:
            icon_label.setText(icon_text)
            icon_label.setFont(QFont("Segoe UI Emoji", 36))

        title_label = QLabel(title)
        title_label.setFont(QFont(MainView.CUSTOM_FONT_FAMILY, 22, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #1E293B; background: transparent;")

        desc_label = QLabel(desc)
        desc_label.setFont(QFont(MainView.CUSTOM_FONT_FAMILY, 14))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #475569; background: transparent; line-height: 140%;")

        action_btn_label = QLabel(f"{btn_text} >")
        action_btn_label.setFont(QFont(MainView.CUSTOM_FONT_FAMILY, 14, QFont.Bold))
        action_btn_label.setAlignment(Qt.AlignCenter)
        
        if is_highlighted:
            action_btn_label.setStyleSheet("""
                color: #FFFFFF; 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #FF5A5F, stop:1 #FF8E53);
                border-radius: 18px;
                padding: 10px 20px;
                margin-top: 8px;
            """)
        else:
            action_btn_label.setStyleSheet("""
                color: #2563EB; 
                background: #EFF6FF;
                border-radius: 18px;
                padding: 10px 20px;
                margin-top: 8px;
            """)

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)
        layout.addWidget(action_btn_label)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(15, 23, 42, 20))
        shadow.setOffset(0, 10)
        card.setGraphicsEffect(shadow)

        return card

    def _apply_card_styles(self):
        self.setStyleSheet("""
            QFrame#modeCard {
                background-color: rgba(255, 255, 255, 0.90);
                border: 1px solid rgba(226, 232, 240, 0.8);
                border-radius: 24px;
            }
            QFrame#modeCard:hover {
                background-color: rgba(255, 255, 255, 1.0);
                border: 2px solid #3B82F6;
            }
            QFrame#modeCardHighlighted {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(255, 248, 248, 0.95), stop:1 rgba(255, 235, 235, 0.95));
                border: 2px solid #FF5A5F;
                border-radius: 24px;
            }
            QFrame#modeCardHighlighted:hover {
                border: 2px solid #E0484D;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainView()
    window.resize(1280, 720)
    window.show()
    sys.exit(app.exec_())