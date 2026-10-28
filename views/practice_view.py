# views/practice_view.py

import os
import random
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QLineEdit, 
    QVBoxLayout, QHBoxLayout, QFrame
)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPainter, QPixmap

# ==============================================================================
# [가이드 영상/웹캠 연동 시 필요한 모듈 (추후 주석 해제)]
# import cv2
# from PyQt5.QtCore import QTimer
# from PyQt5.QtGui import QImage
# ==============================================================================

class PracticeView(QWidget):

    # 상단 메인 메뉴 버튼 클릭 시 main.py로 전송할 무전기 신호
    request_main_menu = pyqtSignal()

    def __init__(self):
        super().__init__()
        
        # 1. 리소스 경로 설정
        self.bg_path = "main_background.jpg"
        self.logo_path = "practice_mainbg.png"
        
        # 2. 지정된 25개 수어 학습 단어 목록
        self.all_words = [
            "발가락", "슬프다", "자극", "영아", "성실", 
            "독서", "면역", "배드민턴", "변비", "불면증", 
            "사위", "찬물", "딸기", "떡국", "막걸리", 
            "부엌", "사이다", "에어컨", "주차장", "채팅", 
            "출근", "디자인", "예술", "벚꽃", "참새"
        ]
        
        # 상태 변수
        self.shuffled_words = []
        self.current_index = 0
        
        self.init_ui()

    def paintEvent(self, event):
        """화면 전체에 메인 배경을 유연하게 스케일링하여 그려줍니다."""
        painter = QPainter(self)
        if os.path.exists(self.bg_path):
            bg_pixmap = QPixmap(self.bg_path)
            painter.drawPixmap(self.rect(), bg_pixmap.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        else:
            painter.fillRect(self.rect(), Qt.white)
        super().paintEvent(event)

    def showEvent(self, event):
 
        super().showEvent(event)
        self._reset_and_update()

    def _reset_and_update(self):
        """단어 리스트 초기화 및 첫 번째 단어 UI 반영"""
        self._reset_word_list()
        self._update_word_ui()

    def _reset_word_list(self):
        """25개 단어를 무작위로 섞습니다."""
        self.shuffled_words = self.all_words.copy()
        random.shuffle(self.shuffled_words)
        self.current_index = 0

    def init_ui(self):
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(15)

        # ======================================================================
        # 1. 상단 헤더 바 (로고, 타이틀, 남은 단어, 메인 메뉴 버튼)
        # ======================================================================
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.85);
                border-radius: 20px;
                border: 2px solid #FFFFFF;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 10, 20, 10)

        # 로고 & 타이틀
        logo_title_layout = QHBoxLayout()
        self.logo_label = QLabel()
        if os.path.exists(self.logo_path):
            logo_pixmap = QPixmap(self.logo_path).scaled(35, 35, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(logo_pixmap)
        else:
            self.logo_label.setText("[LOGO]")
            
        self.title_label = QLabel("수어 연습 게임")
        self.title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #5B6B9C; border: none; background: transparent;")

        logo_title_layout.addWidget(self.logo_label)
        logo_title_layout.addWidget(self.title_label)

        # 진행 상황 표시
        self.remain_label = QLabel()
        self.remain_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #4A73E8;
                background-color: #E6EEFF;
                padding: 8px 18px;
                border-radius: 15px;
                border: none;
            }
        """)

        # 상단 우측 메인 메뉴 버튼
        self.btn_top_main = QPushButton("메인 메뉴")
        self.btn_top_main.setStyleSheet("""
            QPushButton {
                font-size: 15px;
                font-weight: bold;
                color: #E75A7C;
                background-color: #FFE6EE;
                padding: 8px 18px;
                border-radius: 15px;
                border: none;
            }
            QPushButton:hover {
                background-color: #FFCCD9;
            }
        """)
        self.btn_top_main.clicked.connect(self._on_click_back)

        header_layout.addLayout(logo_title_layout)
        header_layout.addStretch(1)
        header_layout.addWidget(self.remain_label)
        header_layout.addWidget(self.btn_top_main)

        root_layout.addWidget(header_frame)

        # ======================================================================
        # 2. 하단 콘텐츠 영역 (좌: 수어 가이드 / 우: 단어 입력 및 판정)
        # ======================================================================
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        # [2-1] 좌측: 수어 가이드 영상 영역
        left_frame = QFrame()
        left_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.7);
                border-radius: 20px;
                border: 2px solid #FFFFFF;
            }
        """)
        left_layout = QVBoxLayout(left_frame)
        left_layout.setContentsMargins(15, 15, 15, 15)

        # 🎬 [가이드 영상 연동 포인트]
        self.video_label = QLabel("[수어 가이드 영상 영역]\n(화면 구현 단계)")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setStyleSheet("""
            QLabel {
                background-color: rgba(230, 235, 245, 0.6); 
                color: #7A89B8; 
                font-size: 18px; 
                font-weight: bold;
                border-radius: 15px;
                border: none;
            }
        """)
        self.video_label.setMinimumSize(600, 450)
        left_layout.addWidget(self.video_label)

        # [2-2] 우측: 학습 단어 및 입력 패널
        right_frame = QFrame()
        right_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.7);
                border-radius: 20px;
                border: 2px solid #FFFFFF;
            }
        """)
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(20, 20, 20, 20)
        right_layout.setSpacing(15)

        # 학습 단어 라벨
        self.word_label = QLabel()
        self.word_label.setAlignment(Qt.AlignCenter)
        self.word_label.setStyleSheet("""
            QLabel {
                font-size: 26px; 
                font-weight: bold; 
                color: #4A5B8C; 
                padding: 10px;
                background: transparent;
                border: none;
            }
        """)

        # 타자 입력창
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("단어를 입력하고 Enter를 누르세요")
        self.input_field.setStyleSheet("""
            QLineEdit {
                font-size: 16px;
                padding: 12px;
                border: 2px solid #FFC0D9;
                border-radius: 12px;
                background-color: #FFFFFF;
                color: #333333;
            }
            QLineEdit:focus {
                border: 2px solid #FF80B2;
            }
        """)
        self.input_field.returnPressed.connect(self._check_answer)

        # 정답 확인 버튼
        self.btn_submit = QPushButton("정답 확인")
        self.btn_submit.setStyleSheet("""
            QPushButton {
                font-size: 16px; 
                padding: 12px; 
                background-color: #52D68A; 
                color: white; 
                border-radius: 12px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #43C27B;
            }
        """)
        self.btn_submit.clicked.connect(self._check_answer)

        # 결과 메시지 라벨
        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("font-size: 16px; font-weight: bold; min-height: 30px; background: transparent; border: none;")

        # 다음 단어 보기 버튼
        self.btn_next_word = QPushButton("다음 단어 보기")
        self.btn_next_word.setStyleSheet("""
            QPushButton {
                font-size: 16px; 
                padding: 12px; 
                background-color: #5B92E5; 
                color: white; 
                border-radius: 12px;
                font-weight: bold;
                border: none;
            }
            QPushButton:hover {
                background-color: #4A7FD4;
            }
        """)
        self.btn_next_word.clicked.connect(self._go_to_next_word)

        right_layout.addWidget(self.word_label)
        right_layout.addWidget(self.input_field)
        right_layout.addWidget(self.btn_submit)
        right_layout.addWidget(self.result_label)
        right_layout.addWidget(self.btn_next_word)
        right_layout.addStretch(1)

        content_layout.addWidget(left_frame, 65)
        content_layout.addWidget(right_frame, 35)

        root_layout.addLayout(content_layout)
        self.setLayout(root_layout)

    # ======================================================================
    # 내부 판정 및 UI 갱신 로직
    # ======================================================================
    def _update_word_ui(self):
        """현재 단어로 UI 세팅"""
        if not self.shuffled_words:
            return
            
        current_word = self.shuffled_words[self.current_index]
        total_count = len(self.shuffled_words)
        
        self.word_label.setText(f"학습 단어: {current_word}")
        self.remain_label.setText(f"남은 단어: {total_count - self.current_index} / {total_count}")
        
        self.input_field.clear()
        self.result_label.setText("")
        self.input_field.setFocus()

    def _check_answer(self):
        """정답/오답 확인"""
        user_input = self.input_field.text().strip()
        target_word = self.shuffled_words[self.current_index]

        if not user_input:
            self.result_label.setText("단어를 입력해 주세요.")
            self.result_label.setStyleSheet("color: #E67E22; font-size: 16px; font-weight: bold; background: transparent; border: none;")
            return

        if user_input == target_word:
            self.result_label.setText("정답입니다! 다음 단어로 이동합니다.")
            self.result_label.setStyleSheet("color: #2ECC71; font-size: 16px; font-weight: bold; background: transparent; border: none;")
            self._go_to_next_word()
        else:
            self.result_label.setText("다시 해보세요.")
            self.result_label.setStyleSheet("color: #E74C3C; font-size: 16px; font-weight: bold; background: transparent; border: none;")
            self.input_field.selectAll()

    def _go_to_next_word(self):
        """다음 단어로 이동하며 25개 완료 시 다시 섞음"""
        self.current_index += 1
        if self.current_index >= len(self.shuffled_words):
            self._reset_word_list()
        self._update_word_ui()

    def _on_click_back(self):
        """메인 메뉴 버튼 클릭 시 신호 발송"""
        self.request_main_menu.emit()