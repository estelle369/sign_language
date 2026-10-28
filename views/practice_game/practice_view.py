import os
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QScrollArea, QFrame
)

from .video_player import VideoPlayerWidget

class PracticeView(QWidget):
    """
    [연습 모드] 9:16 전용 인터랙티브 수어 학습 화면
    - 전체 배경색 #e3efff 적용
    - 타이틀 글씨 대폭 확대 및 정중앙 배치
    - 그리드 카드 형식으로 24개 단어 배치
    """
    back_to_main_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # 24개 수어 단어 데이터셋
        self.word_dataset = [
            {"word": "발가락", "video_path": "assets/videos/balgarak.mp4", "desc": "발가락을 가리키는 수어 동작입니다."},
            {"word": "슬프다", "video_path": "assets/videos/seulpeuda.mp4", "desc": "눈물을 닦아내는 듯한 동작의 수어입니다."},
            {"word": "자극", "video_path": "assets/videos/jageuk.mp4", "desc": "신체나 마음에 자극을 주는 모습을 표현합니다."},
            {"word": "영아", "video_path": "assets/videos/yeongah.mp4", "desc": "어린 아기를 안아주는 형태의 수어입니다."},
            {"word": "성실", "video_path": "assets/videos/seongsil.mp4", "desc": "반듯하고 성실한 태도를 나타내는 수어입니다."},
            {"word": "독서", "video_path": "assets/videos/dokseo.mp4", "desc": "책을 양손으로 펼쳐 읽는 모습을 표현합니다."},
            {"word": "면역", "video_path": "assets/videos/myeonyeok.mp4", "desc": "질병으로부터 몸을 보호하는 수어입니다."},
            {"word": "배드민턴", "video_path": "assets/videos/badminton.mp4", "desc": "라켓으로 셔틀콕을 치는 동작의 수어입니다."},
            {"word": "변비", "video_path": "assets/videos/byeonbi.mp4", "desc": "배변 활동의 어려움을 나타내는 수어입니다."},
            {"word": "불면증", "video_path": "assets/videos/bulmyeonjeung.mp4", "desc": "잠을 이루지 못해 눈이 말똥한 모습을 표현합니다."},
            {"word": "사위", "video_path": "assets/videos/sawui.mp4", "desc": "가족 관계 중 사위를 뜻하는 수어입니다."},
            {"word": "찬물", "video_path": "assets/videos/chanmul.mp4", "desc": "시원하거나 차가운 물을 나타내는 수어입니다."},
            {"word": "딸기", "video_path": "assets/videos/ttalgi.mp4", "desc": "딸기의 표면 씨앗과 형태를 표현한 수어입니다."},
            {"word": "떡국", "video_path": "assets/videos/tteokguk.mp4", "desc": "떡을 썰어 국에 넣는 모습을 표현한 수어입니다."},
            {"word": "막걸리", "video_path": "assets/videos/makgeolli.mp4", "desc": "탁주를 사발에 따라 마시는 동작의 수어입니다."},
            {"word": "부엌", "video_path": "assets/videos/bueok.mp4", "desc": "음식을 조리하는 공간인 부엌을 나타냅니다."},
            {"word": "사이다", "video_path": "assets/videos/saida.mp4", "desc": "톡 쏘는 탄산의 느낌을 표현한 수어입니다."},
            {"word": "에어컨", "video_path": "assets/videos/aircon.mp4", "desc": "시원한 바람이 나오는 기계를 표현한 수어입니다."},
            {"word": "주차장", "video_path": "assets/videos/juchajang.mp4", "desc": "차량이 주차되어 있는 공간을 나타냅니다."},
            {"word": "채팅", "video_path": "assets/videos/chatting.mp4", "desc": "손가락으로 글자를 타이핑하는 듯한 수어입니다."},
            {"word": "출근", "video_path": "assets/videos/chulgeun.mp4", "desc": "일터로 향하는 모습을 나타내는 수어입니다."},
            {"word": "디자인", "video_path": "assets/videos/design.mp4", "desc": "도면을 그리거나 디자인하는 동작의 수어입니다."},
            {"word": "예술", "video_path": "assets/videos/yesul.mp4", "desc": "예술적 감각과 창작을 표현하는 수어입니다."},
            {"word": "참새", "video_path": "assets/videos/chamsae.mp4", "desc": "새가 날아다니거나 부리를 표현한 수어입니다."}
        ]

        self.word_buttons = []
        self.init_ui()

    def init_ui(self):
        # 💡 [핵심 수정] PracticeView 전체 배경을 #e3efff로 확실하게 채워줍니다!
        self.setStyleSheet("PracticeView { background-color: #e3efff; }")
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # ----------------------------------------------------
        # 1. 상단: 메인으로 가기 버튼 & 정중앙에 커진 타이틀
        # ----------------------------------------------------
        header_layout = QHBoxLayout()
        
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
        # 💡 [핵심 수정] 글씨 크기를 30px로 더 키우고, 진한 파란색(#014099) 적용
        title_label.setStyleSheet("font-size: 30px; font-weight: 900; color: #014099; background-color: transparent;")

        header_layout.addWidget(self.btn_back)
        header_layout.addStretch(1)
        header_layout.addWidget(title_label)
        header_layout.addStretch(1)  # 좌우 여백을 똑같이 주어 완벽한 정중앙 정렬

        #main_layout.add.layout = header_layout # (오타 방지용 표준 addLayout 사용)
        main_layout.addLayout(header_layout, stretch=1)

        # ----------------------------------------------------
        # 2. 상단-중간: 수어 시연 영상 영역
        # ----------------------------------------------------
        self.video_player = VideoPlayerWidget(self)
        main_layout.addWidget(self.video_player, stretch=4)

        # 3. 중간: 현재 선택된 단어 및 설명 표시 영역
        # ----------------------------------------------------
        info_frame = QFrame()
        info_frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 16px;
                border: 2px solid #bcd3ff;
            }
        """)
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(15, 15, 15, 15)
        info_layout.setSpacing(8)

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
        
        main_layout.addWidget(info_frame, stretch=2)

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
        self.lbl_description.setText(word_data.get("desc", ""))
        self.video_player.load_video(word_data["video_path"])

    def _on_back_clicked(self):
        self.video_player.stop()
        self.back_to_main_requested.emit()

    def hideEvent(self, event):
        self.video_player.stop()
        super().hideEvent(event)