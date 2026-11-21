import os
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout,
    QGridLayout, QScrollArea, QFrame, QSizePolicy
)

from views.custom_font import load_custom_font_family
from .video_player import VideoPlayerWidget

class PracticeView(QWidget):

    back_to_main_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 24개 수어 단어 데이터셋
        self.word_dataset = [
            {"word": "자극", "video_path": "videos/WORD0010.mp4"},
            {"word": "영아", "video_path": "videos/WORD0015.mp4"},
            {"word": "성실", "video_path": "videos/WORD0023.mp4"},
            {"word": "면역", "video_path": "videos/WORD0036.mp4"},
            {"word": "배드민턴", "video_path": "videos/WORD0038.mp4"},
            {"word": "변비", "video_path": "videos/WORD0039.mp4"},
            {"word": "불면증", "video_path": "videos/WORD0042.mp4"},
            {"word": "사위", "video_path": "videos/WORD0045.mp4"},
            {"word": "냄비", "video_path": "videos/WORD0081.mp4"},
            {"word": "찬물", "video_path": "videos/WORD0082.mp4"},
            {"word": "딸기", "video_path": "videos/WORD0088.mp4"},
            {"word": "떡국", "video_path": "videos/WORD0089.mp4"},
            {"word": "부엌", "video_path": "videos/WORD0096.mp4"},
            {"word": "사이다", "video_path": "videos/WORD0100.mp4"},
            {"word": "구급차", "video_path": "videos/WORD0149.mp4"},
            {"word": "주차장", "video_path": "videos/WORD0168.mp4"},
            {"word": "출근", "video_path": "videos/WORD0170.mp4"},
            {"word": "백화점", "video_path": "videos/WORD0197.mp4"},
            {"word": "디자인", "video_path": "videos/WORD0264.mp4"},
            {"word": "예술", "video_path": "videos/WORD0272.mp4"},
            {"word": "강아지", "video_path": "videos/WORD0292.mp4"},
            {"word": "참새", "video_path": "videos/WORD0308.mp4"},
            {"word": "탈춤", "video_path": "videos/WORD0353.mp4"},
            {"word": "청진기", "video_path": "videos/WORD0861.mp4"}
        ]

        self.word_buttons = []
        self.init_ui()

    def init_ui(self):
        self.bg_path = "blue_bg.png"
        self.setStyleSheet("PracticeView { background-color: #e3efff; }")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # ----------------------------------------------------
        # 1. 상단: 메인으로 가기 버튼 & 정중앙에 커진 타이틀
        # ----------------------------------------------------
        header_layout = QGridLayout()
        
        self.btn_back = QPushButton("← 메인으로")
        self.btn_back.setStyleSheet("""
            QPushButton {
                background-color: #014099;
                color: white;
                font-size: 16px;
                font-weight: bold;
                border-radius: 10px;
                padding: 12px 20px;
            }
            QPushButton:hover { background-color: #002b6b; }
        """)
        self.btn_back.clicked.connect(self._on_back_clicked)
        
        title_label = QLabel("수어 연습 모드")
        title_label.setAlignment(Qt.AlignCenter)
        font_family = load_custom_font_family()
        if font_family:
            title_label.setFont(QFont(font_family))
        title_label.setStyleSheet("font-size: 30px; font-weight: 900; color: #014099; background-color: transparent;")

        side_width = self.btn_back.sizeHint().width()
        header_layout.setColumnMinimumWidth(0, side_width)
        header_layout.setColumnMinimumWidth(2, side_width)
        header_layout.setColumnStretch(0, 1)
        header_layout.setColumnStretch(2, 1)
        header_layout.addWidget(self.btn_back, 0, 0, Qt.AlignLeft)
        header_layout.addWidget(title_label, 0, 1)
        header_layout.addWidget(QWidget(), 0, 2)

        main_layout.addLayout(header_layout, stretch=1)

        # ----------------------------------------------------
        # 2. 상단-중간: 수어 시연 영상 영역
        # ----------------------------------------------------
        self.video_player = VideoPlayerWidget(self)
        main_layout.addWidget(self.video_player, stretch=4)

        # 3. 중간: 현재 선택된 단어 및 설명 표시 영역
        # ----------------------------------------------------
        info_frame = QFrame()
        info_frame.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 16px;
                border: 2px solid #bcd3ff;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(15, 8, 15, 8)
        info_layout.setSpacing(4)

        self.lbl_current_word = QLabel("단어를 선택하세요")
        self.lbl_current_word.setAlignment(Qt.AlignCenter)
        self.lbl_current_word.setStyleSheet("""
            font-size: 36px; 
            font-weight: 900; 
            color: #014099; 
            background-color: transparent;
            border: none;
        """)

        self.lbl_description = QLabel("아래 카드에서 학습할 단어를 터치해주세요.")
        self.lbl_description.setAlignment(Qt.AlignCenter)
        self.lbl_description.setStyleSheet("""
            font-size: 16px; 
            color: #666666; 
            background-color: transparent;
            border: none;
        """)

        info_layout.addWidget(self.lbl_current_word)
        info_layout.addWidget(self.lbl_description)
        
        main_layout.addWidget(info_frame)

        # ----------------------------------------------------
        # 4. 하단: 24개 단어 그리드 카드 영역 (스크롤 지원)
        # ----------------------------------------------------
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                width: 8px;
                background: #d0e1ff;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #014099;
                border-radius: 4px;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        grid_layout = QGridLayout(scroll_content)
        grid_layout.setSpacing(10)
        grid_layout.setContentsMargins(5, 5, 5, 5)

        # 24개 단어를 3열(Columns) 카드로 배치
        row, col = 0, 0
        for data in self.word_dataset:
            card_btn = QPushButton(data["word"])
            card_btn.setMinimumHeight(55)
            card_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #014099;
                    font-size: 16px;
                    font-weight: bold;
                    border: 2px solid #bcd3ff;
                    border-radius: 10px;
                }
                QPushButton:hover {
                    background-color: #d0e1ff;
                }
                QPushButton:checked {
                    background-color: #014099;
                    color: #ffffff;
                    border: 2px solid #002b6b;
                }
            """)
            card_btn.setCheckable(True)
            card_btn.clicked.connect(lambda checked, d=data, btn=card_btn: self._on_card_clicked(d, btn))
            
            grid_layout.addWidget(card_btn, row, col)
            self.word_buttons.append(card_btn)

            col += 1
            if col >= 3:
                col = 0
                row += 1

        scroll_area.setWidget(scroll_content)
        main_layout.addWidget(scroll_area, stretch=4)

        # 첫 번째 단어 기본 선택
        if self.word_buttons:
            self._on_card_clicked(self.word_dataset[0], self.word_buttons[0])

    def _on_card_clicked(self, word_data: dict, clicked_btn: QPushButton):
        """카드 선택 시 처리"""
        for btn in self.word_buttons:
            btn.setChecked(False)
        clicked_btn.setChecked(True)

        self.lbl_current_word.setText(word_data["word"])
        description = word_data.get("desc", "")
        self.lbl_description.setText(description)
        self.lbl_description.setVisible(bool(description))
        self.video_player.load_video(word_data["video_path"])

    def _on_back_clicked(self):
        self.video_player.stop()
        self.back_to_main_requested.emit()

    def hideEvent(self, event):
        self.video_player.stop()
        super().hideEvent(event)