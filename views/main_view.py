import sys
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QApplication, QFrame, QGraphicsDropShadowEffect, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPainter, QPixmap, QFontDatabase

class MainView(QWidget):

    # 화면 전환을 위한 시그널 정의
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
        # 전체 레이아웃 설정
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(60, 40, 60, 20)
        main_layout.setSpacing(30)

        # 1. 상단 타이틀 영역 (부제목 및 설명)
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignCenter)
        header_layout.setSpacing(10)

        subtitle_label = QLabel("수어 학습 키오스크")
        subtitle_label.setFont(QFont(MainView.CUSTOM_FONT_FAMILY, 26, QFont.Bold))
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #014099; background: transparent;")

        desc_label = QLabel("원하시는 모드를 선택하여 수어를 배워보고 게임에 도전해보세요!")
        desc_label.setFont(QFont(MainView.CUSTOM_FONT_FAMILY, 16))
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setStyleSheet("color: #64748B; background: transparent; margin-top: 6px;")

        header_layout.addWidget(subtitle_label)
        header_layout.addWidget(desc_label)

        main_layout.addLayout(header_layout)
        main_layout.addStretch(1)

        # 2. 중앙 카드 선택 영역 (연습 모드 / 실전 게임 모드)
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

        # 실전 게임 모드 카드 (#014099 테마 및 클릭 시그널 연결 완료)
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

        # 3. 우측 하단 인사하는 캐릭터(용용이) 영역 (안전하게 고정된 정지형태)
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch(1) # 왼쪽 공간을 밀어내어 캐릭터를 우측 하단으로 정렬
        
        self.character_label = QLabel()
        self.character_label.setAlignment(Qt.AlignCenter)
        self.character_label.setStyleSheet("background: transparent;")
        
        # seoil_young 이미지 로드 및 크기 설정 (160x160)
        char_pixmap = QPixmap("seoil_young.png")
        if not char_pixmap.isNull():
            scaled_char = char_pixmap.scaled(160, 160, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.character_label.setPixmap(scaled_char)
        else:
            self.character_label.setText("👋 (용용이)")
            self.character_label.setFont(QFont(MainView.CUSTOM_FONT_FAMILY, 16, QFont.Bold))
            self.character_label.setStyleSheet("color: #014099; background: transparent;")
            
        bottom_layout.addWidget(self.character_label)
        main_layout.addLayout(bottom_layout)

        self._apply_card_styles()

    def paintEvent(self, event):
        """메인 화면 전체 배경에 배경화면 이미지를 창 크기에 맞게 꽉 채워 그림"""
        painter = QPainter(self)
        pixmap = QPixmap("seoil_vg.png")
        
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            painter.drawPixmap(0, 0, scaled_pixmap)
        else:
            painter.fillRect(self.rect(), QColor("#F8FAFC"))

    def _create_mode_card(self, title: str, desc: str, btn_text: str, callback, icon_path: str = None, is_highlighted: bool = False) -> QFrame:
        card = QFrame()
        card.setMinimumSize(360, 480)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        card.setCursor(Qt.PointingHandCursor)
        card.setObjectName("modeCardHighlighted" if is_highlighted else "modeCard")
        card.mousePressEvent = lambda event: callback()

        layout = QVBoxLayout(card)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(16)
        layout.setContentsMargins(30, 30, 30, 30)

        icon_label = QLabel()
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("background: transparent;")

        if icon_path:
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                scaled_pixmap = pixmap.scaled(120, 120, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label.setPixmap(scaled_pixmap)

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
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #014099, stop:1 #0256cc);
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
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(240, 244, 255, 0.95), stop:1 rgba(225, 235, 255, 0.95));
                border: 2px solid #014099;
                border-radius: 24px;
            }
            QFrame#modeCardHighlighted:hover {
                border: 2px solid #022b6b;
            }
        """)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainView()
    window.resize(700, 950)
    window.show()
    sys.exit(app.exec_())