import os
import random
import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QLineEdit, 
    QVBoxLayout, QHBoxLayout, QFrame, QGridLayout, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPainter, QPixmap
from PyQt5.QtMultimedia import QSound  

from views.real_game.recognition_thread import RecognitionThread

class GameView(QWidget):

    request_main_menu = pyqtSignal()

    def __init__(self):
        super().__init__()
        

        
# 🌟 현재 game_view.py 파일 위치(views/real_game/)를 기준으로 최상위 폴더(sign_language)를 찾아간 뒤, image 폴더로 진입합니다.
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
        
        # 🌟 image 폴더 안에 있는 실제 파일명을 정확한 경로로 조립합니다.
        image_dir = os.path.join(root_dir, "image")
        
        self.bg_path = os.path.join(image_dir, "blue_bg.png")
        self.logo_path = os.path.join(image_dir, "seoil_logo.png")
        self.char_img_path = os.path.join(image_dir, "seoil_youngyoung_green.png")  
        self.retry_img_path = os.path.join(image_dir, "seoil_young_retry.png")
        
        # print("--------------------------------------------------")
        # print("1. image_dir 실제 경로:", image_dir)
        # print("2. 배경 이미지(blue_bg.png) 전체 경로:", self.bg_path)
        # print("3. 파일이 컴퓨터에 실제로 존재하나요? (True/False):", os.path.exists(self.bg_path))
        # print("--------------------------------------------------")
        # 24개 전용 학습 단어
        self.all_words = [
            "발가락", "슬프다", "자극", "영아", "성실", 
            "독서", "면역", "배드민턴", "변비", "불면증", 
            "사위", "찬물", "딸기", "떡국", "막걸리", 
            "부엌", "사이다", "이불", "주차장", "채팅", 
            "출근", "디자인", "예술", "참새"
        ]
        
        # 상태 변수
        self.score = 0
        self.remaining_words = []
        self.time_left = 120
        self.countdown_val = 3
        self.is_playing = False   # 게임 타이머가 도는 동안만 True. 이때만 인식 결과를 받는다

        # 웹캠 수어 인식 스레드 (게임 화면에 들어올 때 시작, 게임이 끝나거나 나갈 때 정지)
        self.recognition_thread = None
        # 프로그램을 닫을 때 스레드가 돌고 있으면 정지한다 (돌고 있는 QThread 가 지워지면 프로그램이 비정상 종료된다)
        QApplication.instance().aboutToQuit.connect(self._stop_recognition)

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
        painter = QPainter(self)
        if os.path.exists(self.bg_path):
            bg_pixmap = QPixmap(self.bg_path)
            # 🌟 1순위: 이미지를 정상적으로 그리되...
            painter.drawPixmap(self.rect(), bg_pixmap.scaled(self.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        else:
            # 🌟 2순위: 파일이 없으면 눈에 확 띄는 빨간색으로 채워라!
            painter.fillRect(self.rect(), Qt.red)
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
        self.logo_label.setStyleSheet("border: none; background: transparent;")
        if os.path.exists(self.logo_path):
            logo_pixmap = QPixmap(self.logo_path).scaled(35, 35, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.logo_label.setPixmap(logo_pixmap)
        else:
            self.logo_label.setText("[LOGO]")
            
        self.title_label = QLabel("수어 실전 게임")
        self.title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #014099; border: none; background: transparent;")
        logo_title_layout.addWidget(self.logo_label)
        logo_title_layout.addWidget(self.title_label)

        # 정보 상태 라벨
        self.timer_label = QLabel("02:00")
        self.timer_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #014099; background-color: #E6F0FA; padding: 8px 18px; border-radius: 15px; border: 1.5px solid #B8D5FF;")

        self.score_label = QLabel("SCORE: 0점")
        self.score_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #014099; background-color: #E6F0FA; padding: 8px 18px; border-radius: 15px; border: 1.5px solid #B8D5FF;")

        self.remain_label = QLabel(f"남은 단어: {len(self.all_words)} / {len(self.all_words)}")
        self.remain_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #014099; background-color: #E6F0FA; padding: 8px 18px; border-radius: 15px; border: 1.5px solid #B8D5FF;")

        # 메인 메뉴 버튼
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

        # 화면 중앙 효과 오버레이
        self.fx_overlay = QLabel(self.game_board_frame)
        self.fx_overlay.setAlignment(Qt.AlignCenter)
        self.fx_overlay.setHidden(True)

        # 게임 종료 시 나타날 결과 오버레이 팝업
        self.result_container = QWidget(self.game_board_frame)
        result_layout = QVBoxLayout(self.result_container)
        result_layout.setAlignment(Qt.AlignCenter)
        result_layout.setSpacing(20)

        self.lbl_result_title = QLabel("게임 클리어! 🎉", alignment=Qt.AlignCenter)
        self.lbl_result_title.setStyleSheet("font-size: 32px; font-weight: bold; color: #014099; background: transparent; border: none;")
        
        self.lbl_result_desc = QLabel("점수: 0점", alignment=Qt.AlignCenter)
        self.lbl_result_desc.setStyleSheet("font-size: 20px; font-weight: bold; color: #334155; background: transparent; border: none;")

        btn_retry = QPushButton("다시 하기")
        btn_retry.setStyleSheet("""
            QPushButton { font-size: 18px; font-weight: bold; color: white; background-color: #014099; padding: 12px; border-radius: 12px; border: none; }
            QPushButton:hover { background-color: #01307A; }
        """)
        btn_retry.clicked.connect(self._reset_game_state)

        btn_go_main = QPushButton("메인 화면으로 가기")
        btn_go_main.setStyleSheet("""
            QPushButton { font-size: 18px; font-weight: bold; color: #014099; background-color: #E6F0FA; padding: 12px; border-radius: 12px; border: 1.5px solid #B8D5FF; }
            QPushButton:hover { background-color: #D0E3FF; }
        """)
        btn_go_main.clicked.connect(self._on_click_back)

        result_layout.addWidget(self.lbl_result_title)
        result_layout.addWidget(self.lbl_result_desc)
        result_layout.addWidget(btn_retry)
        result_layout.addWidget(btn_go_main)

        self.result_container.setStyleSheet("""
            QWidget {
                background-color: rgba(255, 255, 255, 0.95);
                border-radius: 20px;
                border: 2px solid #014099;
            }
        """)
        self.result_container.setHidden(True)

        root_layout.addWidget(self.game_board_frame, 1)
        self.setLayout(root_layout)

    # ======================================================================
    # 게임 상태 리셋 및 카운트다운 로직
    # ======================================================================
    def showEvent(self, event):
        super().showEvent(event)
        self._reset_game_state()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'game_board_frame') and self.game_board_frame:
            w = self.game_board_frame.width()
            h = self.game_board_frame.height()
            self.fx_overlay.setGeometry(0, 0, w, h)
            
            popup_w, popup_h = 380, 300
            self.result_container.setGeometry(
                (w - popup_w) // 2,
                (h - popup_h) // 2,
                popup_w, popup_h
            )

    def _reset_game_state(self):
        self.game_timer.stop()
        self.countdown_timer.stop()
        self.fx_timer.stop()
        self.result_container.setHidden(True)

        self.score = 0
        self.time_left = 120
        self.countdown_val = 3
        self.remaining_words = self.all_words.copy()
        
        self.score_label.setText("SCORE: 0점")
        self.remain_label.setText(f"남은 단어: {len(self.all_words)} / {len(self.all_words)}")
        self.timer_label.setText("02:00")
        self.is_playing = False

        for w in self.word_widgets.values():
            self.board_grid.removeWidget(w)
            w.deleteLater()
        self.word_widgets.clear()

        shuffled = self.all_words.copy()
        random.shuffle(shuffled)

        for idx, word in enumerate(shuffled):
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

        # 카운트다운 동안 모델을 불러오고 카메라를 켜 둔다
        self._start_recognition()
        self._start_countdown()

    def _start_countdown(self):
        self.fx_overlay.setGeometry(0, 0, self.game_board_frame.width(), self.game_board_frame.height())
        self.fx_overlay.clear() 
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
        self.countdown_val -= 1
        if self.countdown_val > 0:
            self.fx_overlay.setText(str(self.countdown_val))
            self.fx_overlay.raise_()
        elif self.countdown_val == 0:
            # "1"이 끝난 직후: 사용자가 아직 차렷 자세일 때 쉬는 높이를 잰다
            if self.recognition_thread is not None:
                self.recognition_thread.request_calibration()
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
            self.is_playing = True
            self.game_timer.start(1000)

    # ======================================================================
    # 정답/오답 판정 및 효과 연출 (🌟 효과음 파일명 적용 부분)
    # 웹캠 수어 인식 스레드 시작·정지
    # ======================================================================
    def _start_recognition(self):
        self._stop_recognition()   # 이전 게임의 스레드가 남아 있으면 먼저 정지
        self.recognition_thread = RecognitionThread()
        self.recognition_thread.word_recognized.connect(self._on_word_recognized)
        self.recognition_thread.error_occurred.connect(self._on_recognition_error)
        self.recognition_thread.start()

    def _stop_recognition(self):
        if self.recognition_thread is not None:
            self.recognition_thread.stop()   # 스레드가 끝날 때까지 기다린다 (카메라가 꺼진다)
            self.recognition_thread = None

    def _on_recognition_error(self, message: str):
        """카메라·모델을 열지 못하면 게임을 할 수 없으므로 프로그램을 종료한다 (임시 처리)."""
        print(f"[수어 인식 오류] {message}", file=sys.stderr)
        QApplication.instance().exit(1)

    # ======================================================================
    # 정답/오답 판정 및 효과 연출 (캐릭터 이미지 등장 + 효과음)
    # ======================================================================
    def _on_word_recognized(self, word: str, prob: float):
        """
        인식 스레드가 확률 0.5 이상으로 인식한 단어를 받는다.
        0.5 미만은 스레드가 보내지 않으므로 피드백이 없다.
        """
        if not self.is_playing:
            return   # 카운트다운 중이거나 게임이 끝난 뒤에 도착한 결과는 무시

        # 1) 정답을 맞힌 경우
        if word in self.word_widgets and word in self.remaining_words:
            card_widget = self.word_widgets[word]
            
            card_widget.setStyleSheet("""
                QLabel {
                    font-size: 18px; font-weight: bold; color: #B45309;
                    background-color: #FEF08A;
                    padding: 15px; border-radius: 16px; border: 2px solid #EAB308;
                }
            """)
            
            def make_slot_empty(widget=card_widget):
                widget.setText("")  
                widget.setStyleSheet("""
                    QLabel {
                        background-color: rgba(240, 244, 248, 0.4);
                        border-radius: 16px;
                        border: 2px dashed #CBD5E1;
                    }
                """) 

            QTimer.singleShot(250, make_slot_empty)
            
            self.remaining_words.remove(word)
            self.score += 100  # 단어당 100점
            
            self.score_label.setText(f"SCORE: {self.score}점")
            self.remain_label.setText(f"남은 단어: {len(self.remaining_words)} / {len(self.all_words)}")
            
            # 🌟 [적용] 정답 효과음 파일: correct_sound.wav
            if os.path.exists("correct_sound.wav"):
                QSound.play("correct_sound.wav")

            self._show_character_popup(is_correct=True)
            
            if len(self.remaining_words) == 0:
                self.game_timer.stop()
                self.is_playing = False
                self._stop_recognition()
                self._show_game_result("게임 클리어! 🎉", f"모든 단어를 맞혔습니다!\n최종 점수: {self.score}점")

        # 2) 틀렸거나 오답인 경우
        else:
            # 🌟 [적용] 오답 효과음 파일: failed_sound.wav
            if os.path.exists("failed_sound.wav"):
                QSound.play("failed_sound.wav")

            # 🌟 오답 캐릭터(seoil_young_retry.png) 등장 연출 호출 (is_correct=False)
            self._show_character_popup(is_correct=False)

    def _show_character_popup(self, is_correct: bool):
        self.fx_overlay.setGeometry(0, 0, self.game_board_frame.width(), self.game_board_frame.height())
        self.fx_overlay.clear()
        
        target_path = self.char_img_path if is_correct else self.retry_img_path
        if os.path.exists(target_path):
            pixmap = QPixmap(target_path)
            scaled_pixmap = pixmap.scaled(220, 220, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.fx_overlay.setPixmap(scaled_pixmap)
        else:
            fallback_text = "✨ O ✨" if is_correct else "❌ X ❌"
            self.fx_overlay.setText(fallback_text)
            self.fx_overlay.setStyleSheet("font-size: 80px; font-weight: bold; color: #E74C3C; background: transparent;")

        self.fx_overlay.setStyleSheet("background-color: rgba(255, 255, 255, 0.75); border-radius: 20px;")
        self.fx_overlay.setHidden(False)
        self.fx_overlay.raise_()  
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
            self._show_game_result("시간 초과! ⏰", f"제한 시간이 종료되었습니다.\n최종 점수: {self.score}점")

    def _show_game_result(self, title: str, desc: str):
        self.lbl_result_title.setText(title)
        self.lbl_result_desc.setText(desc)
        self.result_container.setHidden(False)
        self.result_container.raise_()
        self.is_playing = False
        self._stop_recognition()
        
    def _on_click_back(self):
        self.game_timer.stop()
        self.countdown_timer.stop()
        self.fx_timer.stop()
        self.is_playing = False
        self._stop_recognition()
        self.request_main_menu.emit()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.game_timer.stop()
        self.countdown_timer.stop()
        self.fx_timer.stop()
        self.is_playing = False
        self._stop_recognition()