# views/real_game/game_view.py

import os
import random
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QLineEdit, 
    QVBoxLayout, QHBoxLayout, QFrame, QGridLayout
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPainter, QPixmap

class GameView(QWidget):

    request_main_menu = pyqtSignal()

    def __init__(self):
        super().__init__()
        
        # 리소스 경로
        self.bg_path = "main_background.jpg"
        self.logo_path = "practice_mainbg.png"
        
        # 25개 전용 학습 단어
        self.all_words = [
            "발가락", "슬프다", "자극", "영아", "성실", 
            "독서", "면역", "배드민턴", "변비", "불면증", 
            "사위", "찬물", "딸기", "떡국", "막걸리", 
            "부엌", "사이다", "에어컨", "주차장", "채팅", 
            "출근", "디자인", "예술", "벚꽃", "참새"
        ]
        
        # 상태 변수
        self.score = 0
        self.remaining_words = []
        self.time_left = 120
        self.countdown_val = 3
        
        # 타이머 정의
        self.game_timer = QTimer(self)
        self.game_timer.timeout.connect(self._update_timer)
        
        self.countdown_timer = QTimer(self)
        self.countdown_timer.timeout.connect(self._run_countdown)
        
        self.fx_timer = QTimer(self)
        self.fx_timer.setSingleShot(True)
        self.fx_timer.timeout.connect(self._hide_fx_overlay)

        self.init_ui()

    def paintEvent(self, event):
        """전체화면 비율에 맞춰 메인 배경을 유연하게 스케일링합니다."""
        painter = QPainter(self)
        if os.path.exists(self.bg_path):
            bg_pixmap = QPixmap(self.bg_path)
            painter.drawPixmap(self.rect(), bg_pixmap.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        else:
            painter.fillRect(self.rect(), Qt.white)
        super().paintEvent(event)

    def init_ui(self):
        root_layout = QVBoxLayout()
        root_layout.setContentsMargins(20, 20, 20, 20)
        root_layout.setSpacing(15)

        # ======================================================================
        # 1. 상단 헤더 바
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

        # 로고 및 타이틀
        logo_title_layout = QHBoxLayout()
        self.logo_label = QLabel()
        if os.path.exists(self.logo_path):
            logo_pixmap = QPixmap(self.logo_path).scaled(35, 35, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(logo_pixmap)
        else:
            self.logo_label.setText("[LOGO]")
            
        self.title_label = QLabel("수어 실전 게임")
        self.title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #5B6B9C; border: none; background: transparent;")
        logo_title_layout.addWidget(self.logo_label)
        logo_title_layout.addWidget(self.title_label)

        # 정보 상태 라벨
        self.timer_label = QLabel("02:00")
        self.timer_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #E74C3C; background-color: #FDEDEC; padding: 8px 18px; border-radius: 15px; border: none;")

        self.score_label = QLabel("SCORE: 0점")
        self.score_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #E75A7C; background-color: #FFE6EE; padding: 8px 18px; border-radius: 15px; border: none;")

        self.remain_label = QLabel("남은 단어: 25 / 25")
        self.remain_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4A73E8; background-color: #E6EEFF; padding: 8px 18px; border-radius: 15px; border: none;")

        self.btn_top_main = QPushButton("메인 메뉴")
        self.btn_top_main.setStyleSheet("""
            QPushButton { font-size: 15px; font-weight: bold; color: #E75A7C; background-color: #FFE6EE; padding: 8px 18px; border-radius: 15px; border: none; }
            QPushButton:hover { background-color: #FFCCD9; }
        """)
        self.btn_top_main.clicked.connect(self._on_click_back)

        header_layout.addLayout(logo_title_layout)
        header_layout.addStretch(1)
        header_layout.addWidget(self.timer_label)
        header_layout.addWidget(self.score_label)
        header_layout.addWidget(self.remain_label)
        header_layout.addWidget(self.btn_top_main)

        root_layout.addWidget(header_frame)

        # ======================================================================
        # 2. 게임판 영역 및 효과 오버레이
        # ======================================================================
        self.game_board_frame = QFrame()
        self.game_board_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.65);
                border-radius: 20px;
                border: 2px solid #FFFFFF;
            }
        """)
        self.board_grid = QGridLayout(self.game_board_frame)
        self.board_grid.setContentsMargins(20, 20, 20, 20)
        self.board_grid.setSpacing(15)

        # 25개 단어 라벨 위젯 사전
        self.word_widgets = {}

        # 화면 중앙 효과 오버레이
        self.fx_overlay = QLabel(self.game_board_frame)
        self.fx_overlay.setAlignment(Qt.AlignCenter)
        self.fx_overlay.setHidden(True)

        root_layout.addWidget(self.game_board_frame, 1)

        # ======================================================================
        # 3. 하단 입력 패널
        # ======================================================================
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.85); border-radius: 20px; border: 2px solid #FFFFFF;")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(15, 10, 15, 10)
        input_layout.setSpacing(10)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("단어를 입력하고 Enter를 누르세요...")
        self.input_field.setStyleSheet("""
            QLineEdit { font-size: 16px; padding: 12px; border: 2px solid #FFC0D9; border-radius: 12px; background-color: #FFFFFF; color: #333333; }
            QLineEdit:focus { border: 2px solid #FF80B2; }
        """)
        self.input_field.returnPressed.connect(self._check_answer)

        self.btn_submit = QPushButton("입력")
        self.btn_submit.setStyleSheet("""
            QPushButton { font-size: 16px; font-weight: bold; color: white; background-color: #FFB3C6; padding: 12px 25px; border-radius: 12px; border: none; }
            QPushButton:hover { background-color: #FF99B2; }
        """)
        self.btn_submit.clicked.connect(self._check_answer)

        input_layout.addWidget(self.input_field, 1)
        input_layout.addWidget(self.btn_submit)

        root_layout.addWidget(input_frame)
        self.setLayout(root_layout)

    # ======================================================================
    # 게임 상태 리셋 및 카운트다운 로직
    # ======================================================================
    def showEvent(self, event):
        """메인에서 진입할 때마다 완전히 리셋 후 시작"""
        super().showEvent(event)
        self._reset_game_state()

    def resizeEvent(self, event):
        """창 크기가 바뀔 때 카운트다운 레이어 크기도 자동 조율"""
        super().resizeEvent(event)
        if hasattr(self, 'game_board_frame') and self.game_board_frame:
            self.fx_overlay.setGeometry(0, 0, self.game_board_frame.width(), self.game_board_frame.height())

    def _reset_game_state(self):
        """상태 초기화 및 25개 단어 위치 섞어 재배치"""
        self.score = 0
        self.time_left = 120
        self.countdown_val = 3
        self.remaining_words = self.all_words.copy()
        
        self.score_label.setText("SCORE: 0점")
        self.remain_label.setText(f"남은 단어: {len(self.all_words)} / {len(self.all_words)}")
        self.timer_label.setText("02:00")
        self.input_field.clear()
        self.input_field.setEnabled(False)

        for w in self.word_widgets.values():
            self.board_grid.removeWidget(w)
            w.deleteLater()
        self.word_widgets.clear()

        shuffled = self.all_words.copy()
        random.shuffle(shuffled)

        for idx, word in enumerate(shuffled):
            row = idx // 5
            col = idx % 5
            word_chip = QLabel(word)
            word_chip.setAlignment(Qt.AlignCenter)
            word_chip.setStyleSheet("""
                QLabel {
                    font-size: 18px; font-weight: bold; color: #4A5B8C;
                    background-color: rgba(255, 255, 255, 0.9);
                    padding: 12px; border-radius: 20px; border: 1.5px solid #E2E8F0;
                }
            """)
            self.board_grid.addWidget(word_chip, row, col)
            self.word_widgets[word] = word_chip

        self._start_countdown()

    def _start_countdown(self):
        """3, 2, 1 카운트다운 연출 (최상단 레이어 고정)"""
        self.fx_overlay.setGeometry(0, 0, self.game_board_frame.width(), self.game_board_frame.height())
        self.fx_overlay.setText(str(self.countdown_val))
        self.fx_overlay.setStyleSheet("""
            QLabel {
                font-size: 140px; font-weight: bold; color: #FF6B81;
                background-color: rgba(255, 255, 255, 0.95); border-radius: 20px;
            }
        """)
        self.fx_overlay.setHidden(False)
        self.fx_overlay.raise_()  # 🌟 단어 카드들보다 위로 끌어올림!
        self.countdown_timer.start(1000)

    def _run_countdown(self):
        """카운트다운 숫자 감소 및 START! 연출"""
        self.countdown_val -= 1
        if self.countdown_val > 0:
            self.fx_overlay.setText(str(self.countdown_val))
            self.fx_overlay.raise_()
        elif self.countdown_val == 0:
            self.fx_overlay.setText("START!")
            self.fx_overlay.setStyleSheet("""
                QLabel {
                    font-size: 90px; font-weight: bold; color: #2ECC71;
                    background-color: rgba(255, 255, 255, 0.95); border-radius: 20px;
                }
            """)
            self.fx_overlay.raise_()
        else:
            self.countdown_timer.stop()
            self.fx_overlay.setHidden(True)
            self.input_field.setEnabled(True)
            self.input_field.setFocus()
            self.game_timer.start(1000)

    # ======================================================================
    # 정답/오답 판정 및 효과 연출
    # ======================================================================
    def _check_answer(self):
        if self.countdown_val > 0:
            return

        user_input = self.input_field.text().strip()

        if user_input in self.word_widgets and user_input in self.remaining_words:
            widget = self.word_widgets[user_input]
            widget.setVisible(False)
            
            self.remaining_words.remove(user_input)
            self.score += 10
            
            self.score_label.setText(f"SCORE: {self.score}점")
            self.remain_label.setText(f"남은 단어: {len(self.remaining_words)} / {len(self.all_words)}")
            
            self._show_fx("O", "#2ECC71")

        elif user_input:
            self._show_fx("X", "#E74C3C")

        self.input_field.clear()
        self.input_field.setFocus()

    def _show_fx(self, text, color_hex):
        """O / X 피드백 최상단 레이어 팝업 연출"""
        self.fx_overlay.setGeometry(0, 0, self.game_board_frame.width(), self.game_board_frame.height())
        self.fx_overlay.setText(text)
        self.fx_overlay.setStyleSheet(f"""
            QLabel {{
                font-size: 160px; font-weight: bold; color: {color_hex};
                background-color: rgba(255, 255, 255, 0.85); border-radius: 20px;
            }}
        """)
        self.fx_overlay.setHidden(False)
        self.fx_overlay.raise_()  # 🌟 단어 카드들보다 위로 끌어올림!
        self.fx_timer.start(500)

    def _hide_fx_overlay(self):
        self.fx_overlay.setHidden(True)

    def _update_timer(self):
        self.time_left -= 1
        minutes = self.time_left // 60
        seconds = self.time_left % 60
        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")

        if self.time_left <= 0:
            self.game_timer.stop()
            self.timer_label.setText("TIME OVER")
            self.input_field.setEnabled(False)

    def _on_click_back(self):
        self.game_timer.stop()
        self.countdown_timer.stop()
        self.fx_timer.stop()
        self.request_main_menu.emit()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.game_timer.stop()
        self.countdown_timer.stop()
        self.fx_timer.stop()