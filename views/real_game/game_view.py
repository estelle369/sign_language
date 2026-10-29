# views/real_game/game_view.py

import os
import random
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QLineEdit, 
    QVBoxLayout, QHBoxLayout, QFrame, QGridLayout, QMessageBox
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPainter, QPixmap, QFont
from PyQt5.QtMultimedia import QSound  # 효과음 재생용

class GameView(QWidget):

    request_main_menu = pyqtSignal()

    def __init__(self):
        super().__init__()
        
        # 리소스 경로
        self.bg_path = "blue_bg.png"
        self.logo_path = "seoil_logo.png"
        self.char_img_path = "seoil_youngyoung_green.png"  
        self.retry_img_path = "seoil_young_retry.png"
        
        # 24개 전용 학습 단어
        self.all_words = [
            "발가락", "슬프다", "자극", "영아", "성실", 
            "독서", "면역", "배드민턴", "변비", "불면증", 
            "사위", "찬물", "딸기", "떡국", "막걸리", 
            "부엌", "사이다", "에어컨", "주차장", "채팅", 
            "출근", "디자인", "예술", "참새"
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
        
        # 캐릭터 이미지 팝업을 잠시 보여주었다가 숨기기 위한 타이머 (약 0.8초)
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
        # 1. 상단 헤더 바 (네이비 #014099 테마 적용)
        # ======================================================================
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.9);
                border-radius: 20px;
                border: 2px solid #014099;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 10, 20, 10)
        
        
        # 로고 및 타이틀
        logo_title_layout = QHBoxLayout()
        self.logo_label = QLabel()
        self.logo_label.setStyleSheet("""
            QLabel {
                border: none;
                background: transparent;
            }
        """)
        if os.path.exists(self.logo_path):
            logo_pixmap = QPixmap(self.logo_path).scaled(35, 35, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(logo_pixmap)

        else:
            self.logo_label.setText("[LOGO]")
            

            
        self.title_label = QLabel("수어 실전 게임")
        # 🌟 메인과 동일한 #014099 적용
        self.title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #014099; border: none; background: transparent;")
        logo_title_layout.addWidget(self.logo_label)
        logo_title_layout.addWidget(self.title_label)

        # 정보 상태 라벨 (소프트 블루 #E6F0FA 배경과 #014099 글씨 조합)
        self.timer_label = QLabel("02:00")
        self.timer_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #014099; background-color: #E6F0FA; padding: 8px 18px; border-radius: 15px; border: 1.5px solid #B8D5FF;")

        self.score_label = QLabel("SCORE: 0점")
        self.score_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #014099; background-color: #E6F0FA; padding: 8px 18px; border-radius: 15px; border: 1.5px solid #B8D5FF;")

        self.remain_label = QLabel(f"남은 단어: {len(self.all_words)} / {len(self.all_words)}")
        self.remain_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #014099; background-color: #E6F0FA; padding: 8px 18px; border-radius: 15px; border: 1.5px solid #B8D5FF;")

        # 메인 메뉴 버튼 (모던한 딥블루 스타일)
        self.btn_top_main = QPushButton("메인 메뉴")
        self.btn_top_main.setStyleSheet("""
            QPushButton { font-size: 15px; font-weight: bold; color: #014099; background-color: #E6F0FA; padding: 8px 18px; border-radius: 15px; border: 1.5px solid #B8D5FF; }
            QPushButton:hover { background-color: #D0E3FF; }
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
                background-color: rgba(255, 255, 255, 0.75);
                border-radius: 20px;
                border: 2px solid #014099;
            }
        """)
        self.board_grid = QGridLayout(self.game_board_frame)
        self.board_grid.setContentsMargins(20, 20, 20, 20)
        self.board_grid.setSpacing(12)

        # 24개 단어 라벨 위젯 사전
        self.word_widgets = {}

        # 🌟 화면 중앙 효과 오버레이 (카운트다운 및 정답 시 캐릭터 이미지를 띄울 용도)
        self.fx_overlay = QLabel(self.game_board_frame)
        self.fx_overlay.setAlignment(Qt.AlignCenter)
        self.fx_overlay.setHidden(True)

        root_layout.addWidget(self.game_board_frame, 1)

        # ======================================================================
        # 3. 하단 입력 패널
        # ======================================================================
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: rgba(255, 255, 255, 0.9); border-radius: 20px; border: 2px solid #014099;")
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(15, 10, 15, 10)
        input_layout.setSpacing(10)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("단어를 입력하고 Enter를 누르세요...")
        self.input_field.setStyleSheet("""
            QLineEdit { font-size: 16px; padding: 12px; border: 2px solid #93C5FD; border-radius: 12px; background-color: #FFFFFF; color: #333333; }
            QLineEdit:focus { border: 2px solid #014099; }
        """)
        self.input_field.returnPressed.connect(self._check_answer)

        self.btn_submit = QPushButton("입력")
        self.btn_submit.setStyleSheet("""
            QPushButton { font-size: 16px; font-weight: bold; color: white; background-color: #014099; padding: 12px 25px; border-radius: 12px; border: none; }
            QPushButton:hover { background-color: #01307A; }
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
        """창 크기가 바뀔 때 오버레이 레이어 크기 자동 조율"""
        super().resizeEvent(event)
        if hasattr(self, 'game_board_frame') and self.game_board_frame:
            self.fx_overlay.setGeometry(0, 0, self.game_board_frame.width(), self.game_board_frame.height())

    def _reset_game_state(self):
        """상태 초기화 및 24개 단어 위치 섞어 재배치 (가로 4개 x 세로 6개 구조)"""
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
            # 🌟 요청하신 가로 4개, 세로 6개 배치 공식 (idx // 4, idx % 4)
            row = idx // 4
            col = idx % 4
            
            word_chip = QLabel(word)
            word_chip.setAlignment(Qt.AlignCenter)
            word_chip.setStyleSheet("""
                QLabel {
                    font-size: 18px; font-weight: bold; color: #334155;
                    background-color: rgba(255, 255, 255, 0.95);
                    padding: 15px; border-radius: 16px; border: 1.5px solid #CBD5E1;
                }
            """)
            self.board_grid.addWidget(word_chip, row, col)
            self.word_widgets[word] = word_chip

        self._start_countdown()

    def _start_countdown(self):
        """3, 2, 1 카운트다운 연출"""
        self.fx_overlay.setGeometry(0, 0, self.game_board_frame.width(), self.game_board_frame.height())
        self.fx_overlay.clear()  # 이미지 초기화 후 텍스트 설정
        self.fx_overlay.setText(str(self.countdown_val))
        self.fx_overlay.setStyleSheet("""
            QLabel {
                font-size: 140px; font-weight: bold; color: #FF6B81;
                background-color: rgba(255, 255, 255, 0.95); border-radius: 20px;
            }
        """)
        self.fx_overlay.setHidden(False)
        self.fx_overlay.raise_()  
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
    # 정답/오답 판정 및 효과 연출 (캐릭터 이미지 등장 + 효과음)
    # ======================================================================
    def _check_answer(self):
        if self.countdown_val > 0:
            return

        user_input = self.input_field.text().strip()

        # 1) 정답을 맞힌 경우
        if user_input in self.word_widgets and user_input in self.remaining_words:
            card_widget = self.word_widgets[user_input]
            
            # 🌟 정답 시 카드가 노란색으로 변하며 사라지는 시각적 피드백
            card_widget.setStyleSheet("""
                QLabel {
                    font-size: 18px; font-weight: bold; color: #B45309;
                    background-color: #FEF08A;
                    padding: 15px; border-radius: 16px; border: 2px solid #EAB308;
                }
            """)
            QTimer.singleShot(250, lambda: card_widget.setVisible(False)) # 살짝 노란색으로 번쩍였다가 숨김
            
            self.remaining_words.remove(user_input)
            self.score += 100  # 단어당 100점
            
            self.score_label.setText(f"SCORE: {self.score}점")
            self.remain_label.setText(f"남은 단어: {len(self.remaining_words)} / {len(self.all_words)}")
            
            # 🌟 정답 효과음 재생 (correct.wav 파일이 있을 경우)
            if os.path.exists("correct.wav"):
                QSound.play("correct.wav")

            # 🌟 정답 캐릭터(seoil_youngyoung_green.png) 등장 연출 호출 (is_correct=True)
            self._show_character_popup(is_correct=True)
            
            # 게임 올클리어 체크
            if len(self.remaining_words) == 0:
                self.game_timer.stop()
                QMessageBox.information(self, "클리어! 🎉", f"모든 수어 단어를 맞혔습니다!\n최종 점수: {self.score}점")

        # 2) 틀렸거나(오답) 화면에 없는 단어를 입력한 경우 🌟
        elif user_input:
            # (선택사항) 틀렸을 때 오답 효과음이 있다면 재생
            if os.path.exists("wrong.wav"):
                QSound.play("wrong.wav")
                
            # 🌟 오답 캐릭터(seoil_young_retry.png) 등장 연출 호출 (is_correct=False)
            self._show_character_popup(is_correct=False)

        self.input_field.clear()
        self.input_field.setFocus()

    def _show_character_popup(self, is_correct: bool):
        """
        is_correct가 True면 정답 캐릭터(초록이), False면 오답(재시도) 캐릭터를 화면 중앙에 띄웁니다.
        """
        self.fx_overlay.setGeometry(0, 0, self.game_board_frame.width(), self.game_board_frame.height())
        self.fx_overlay.clear()
        
        # 상황에 따라 이미지 경로 선택
        target_path = self.char_img_path if is_correct else self.retry_img_path
        
        if os.path.exists(target_path):
            pixmap = QPixmap(target_path)
            # 캐릭터 크기를 적절히 (예: 220x220) 유지하며 부드럽게 스케일링
            scaled_pixmap = pixmap.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.fx_overlay.setPixmap(scaled_pixmap)
        else:
            # 이미지 파일이 없을 경우 대비용 텍스트
            fallback_text = "✨ O ✨" if is_correct else "❌ X ❌"
            self.fx_overlay.setText(fallback_text)
            self.fx_overlay.setStyleSheet("font-size: 80px; font-weight: bold; color: #E74C3C; background: transparent;")

        self.fx_overlay.setStyleSheet("background-color: rgba(255, 255, 255, 0.75); border-radius: 20px;")
        self.fx_overlay.setHidden(False)
        self.fx_overlay.raise_()  
        
        # 0.8초(800ms) 동안 보여준 뒤 자동으로 숨기기
        self.fx_timer.start(800)

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
            QMessageBox.warning(self, "시간 초과", "제한 시간이 종료되었습니다!")

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