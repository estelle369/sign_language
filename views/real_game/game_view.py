import os
import random
import sys
import cv2
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, 
    QVBoxLayout, QHBoxLayout, QFrame, QGridLayout)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QPainter, QPixmap, QImage
from PyQt5.QtMultimedia import QSound  

from views.real_game.recognition_thread import RecognitionThread

class GameView(QWidget):

    request_main_menu = pyqtSignal()

    def __init__(self):
        super().__init__()
        
        # 파일 경로 설정
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(current_dir, "../../"))
        image_dir = os.path.join(root_dir, "image")
        
        self.bg_path = os.path.join(image_dir, "blue_bg.png")
        self.logo_path = os.path.join(image_dir, "seoil_logo.png")
        self.char_img_path = os.path.join(image_dir, "seoil_youngyoung_green.png")  
        self.retry_img_path = os.path.join(image_dir, "seoil_young_retry.png")
        
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
        self.is_playing = False   

        # 대기 및 인식 카운트 변수
        self.ready_frame_count = 0        
        self.required_frames = 20         # 약 0.6초 동안 자세 유지 시 시작
        self.is_waiting_for_user = True   
        self.is_counting_down = False     

        self.recognition_thread = None
        QApplication.instance().aboutToQuit.connect(self._stop_recognition)

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

        # 1. 상단 헤더 바
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

        self.timer_label = QLabel("02:00")
        self.timer_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #014099; background-color: #E6F0FA; padding: 8px 18px; border-radius: 15px; border: 1.5px solid #B8D5FF;")

        self.score_label = QLabel("SCORE: 0점")
        self.score_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #014099; background-color: #E6F0FA; padding: 8px 18px; border-radius: 15px; border: 1.5px solid #B8D5FF;")

        self.remain_label = QLabel(f"남은 단어: {len(self.all_words)} / {len(self.all_words)}")
        self.remain_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #014099; background-color: #E6F0FA; padding: 8px 18px; border-radius: 15px; border: 1.5px solid #B8D5FF;")

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

        # 2. 게임판 영역 (단어들이 들어가는 곳)
        self.game_board_frame = QFrame()
        self.game_board_frame.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.85);
                border-radius: 20px;
                border: 2px solid #014099;
            }
        """)
        
        self.board_grid = QGridLayout(self.game_board_frame)
        self.board_grid.setContentsMargins(20, 20, 20, 20)
        self.board_grid.setSpacing(12)

        # 웹캠 미리보기 화면: 게임판 전체를 가득 채우는 화면
        self.webcam_preview_label = QLabel(self.game_board_frame)
        self.webcam_preview_label.setAlignment(Qt.AlignCenter)
        self.webcam_preview_label.setStyleSheet("""
            QLabel {
                background-color: #0f172a;
                border-radius: 16px;
                color: white;
                font-size: 20px;
                font-weight: bold;
            }
        """)
        self.webcam_preview_label.setText("웹캠 연결 및 모델 로딩 중...")

        self.word_widgets = {}

        # 화면 중앙 효과 오버레이 (안내 문구 및 카운트다운)
        self.fx_overlay = QLabel(self.game_board_frame)
        self.fx_overlay.setAlignment(Qt.AlignCenter)
        self.fx_overlay.setHidden(True)

        # 게임 종료 시 결과 팝업
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

    def showEvent(self, event):
        super().showEvent(event)
        self._reset_game_state()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'game_board_frame') and self.game_board_frame:
            w = self.game_board_frame.width()
            h = self.game_board_frame.height()
            
            # 웹캠 미리보기 창은 게임판 전체를 채우기
            self.webcam_preview_label.setGeometry(10, 10, w - 20, h - 20)
            
            # 만약 대기 안내 팝업이 떠 있는 상태라면 크기 유지 (또는 중앙 정렬)
            if self.is_waiting_for_user:
                card_w, card_h = 520, 260
                self.fx_overlay.setGeometry((w - card_w) // 2, (h - card_h) // 2, card_w, card_h)
            else:
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
        
        self.ready_frame_count = 0
        self.is_waiting_for_user = True
        self.is_counting_down = False

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

        # 처음 시작 시 단어판들은 숨기고 웹캠 미리보기 띄우기
        for w in self.word_widgets.values():
            w.setHidden(True)

        self._start_recognition()
        self._show_waiting_for_user_guide()

    def _show_waiting_for_user_guide(self):
        """웹캠 화면은 전체로 뜨고, 중앙에 깔끔한 안내 카드 띄우기"""
        self.webcam_preview_label.setHidden(False)
        self.webcam_preview_label.raise_()

        # fx_overlay를 화면 중앙에 예쁜 카드 형태로 배치하기 위해 크기 지정
        w = self.game_board_frame.width()
        h = self.game_board_frame.height()
        card_w, card_h = 520, 260
        self.fx_overlay.setGeometry((w - card_w) // 2, (h - card_h) // 2, card_w, card_h)
        
        self.fx_overlay.clear() 
        self.fx_overlay.setText("웹캠 앞에 서서\n어깨와 손을 보여주세요!\n\n(자세 유지 시 자동 시작)")
        
        # 깔끔하고 세련된 흰색 카드 스타일 (테두리와 둥근 모서리 적용)
        self.fx_overlay.setStyleSheet("""
            QLabel {
                font-size: 24px; 
                font-weight: bold; 
                color: #014099;
                background-color: rgb(255, 255, 255); 
                border-radius: 20px;
                border: 3px solid #014099;
                padding: 20px;
            }
        """)
        self.fx_overlay.setHidden(False)
        self.fx_overlay.raise_() # 웹캠보다 위에 오도록 맨 위로 올리기

    def _start_countdown(self):
        """자세 인식이 끝나면 1, 2, 3 카운트다운 시작"""
        self.is_waiting_for_user = False
        self.is_counting_down = True
        
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
            if self.recognition_thread is not None:
                self.recognition_thread.request_calibration()
            self.fx_overlay.setText("GAME START!")
            self.fx_overlay.setStyleSheet("""
                QLabel {
                    font-size: 70px; font-weight: bold; color: #2ECC71;
                    background-color: rgba(255, 255, 255, 0.95); border-radius: 20px;
                }
            """)
            self.fx_overlay.raise_()
        else:
            self.countdown_timer.stop()
            self.fx_overlay.setHidden(True)
            
            # 카운트다운과 GAME START가 끝나면 웹캠 숨기고 단어판 켜기!
            self.webcam_preview_label.setHidden(True)
            for w in self.word_widgets.values():
                w.setHidden(False)

            self.is_playing = True
            self.game_timer.start(1000)

    def _start_recognition(self):
        self._stop_recognition()   
        self.recognition_thread = RecognitionThread()
        self.recognition_thread.word_recognized.connect(self._on_word_recognized)
        self.recognition_thread.error_occurred.connect(self._on_recognition_error)
        
        # 1. 웹캠 프레임 화면 띄우기 연결
        if hasattr(self.recognition_thread, 'frame_ready'):
            self.recognition_thread.frame_ready.connect(self._update_webcam_preview)
            
        # 2. 🌟 진짜 어깨·손 인식 여부(True/False) 판정 연결!
        if hasattr(self.recognition_thread, 'body_status_checked'):
            self.recognition_thread.body_status_checked.connect(self._on_body_status_received)
            
        self.recognition_thread.start()

    def _update_webcam_preview(self, frame):
        """스레드에서 넘어온 프레임을 거울 모드로 변환하여 전체 화면에 띄움"""
        if frame is None:
            return

        flipped_frame = cv2.flip(frame, 1)
        rgb_image = cv2.cvtColor(flipped_frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        p = convert_to_qt_format.scaled(
            self.webcam_preview_label.width(), 
            self.webcam_preview_label.height(), 
            Qt.KeepAspectRatio, 
            Qt.SmoothTransformation
        )
        self.webcam_preview_label.setPixmap(QPixmap.fromImage(p))

        # 대기 상태일 때 프레임 누적 체크
        if self.is_waiting_for_user and not self.is_counting_down:
            self.ready_frame_count += 1
            
            # 🌟 관람객이 자세를 잡고 목표 프레임에 도달한 순간!
            if self.ready_frame_count >= self.required_frames:
                self.is_counting_down = True  # 중복 인식 방지 잠금
                
                # 1단계: 카메라 화면은 그대로 둔 채, 안내 문구를 "인식 완료!"로 변경
                self.fx_overlay.setText("✨ 인식 완료! ✨")
                self.fx_overlay.setStyleSheet("""
                    QLabel {
                        font-size: 50px; 
                        font-weight: bold; 
                        color: #2ECC71;
                        background-color: rgba(255, 255, 255, 0.85); 
                        border-radius: 20px;
                        padding: 20px;
                    }
                """)
                self.fx_overlay.setHidden(False)
                self.fx_overlay.raise_()
                
                # 2단계: 1초(1000ms) 동안 "인식 완료!"를 보여준 뒤, 진짜 3, 2, 1 카운트다운으로 점프!
                QTimer.singleShot(1000, self._start_real_countdown)

    def _start_real_countdown(self):
        """인식 완료 후, 카메라가 켜진 상태에서 3, 2, 1 카운트다운을 시작하는 함수"""
        self.countdown_val = 3
        self.fx_overlay.setText(str(self.countdown_val))
        self.fx_overlay.setStyleSheet("""
            QLabel {
                font-size: 140px; 
                font-weight: bold; 
                color: #FF6B81;
                background-color: rgba(255, 255, 255, 0.90); 
                border-radius: 20px;
            }
        """)
        self.countdown_timer.start(1000) # 1초마다 _run_countdown 호출
    def _stop_recognition(self):
        if self.recognition_thread is not None:
            self.recognition_thread.stop()   
            self.recognition_thread = None

    def _on_recognition_error(self, message: str):
        print(f"[수어 인식 오류] {message}", file=sys.stderr)
        QApplication.instance().exit(1)

    def _on_word_recognized(self, word: str, prob: float):
        if not self.is_playing:
            return   

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
            self.score += 100  
            
            self.score_label.setText(f"SCORE: {self.score}점")
            self.remain_label.setText(f"남은 단어: {len(self.remaining_words)} / {len(self.all_words)}")
            
            if os.path.exists("correct_sound.wav"):
                QSound.play("correct_sound.wav")

            self._show_character_popup(is_correct=True)
            
            if len(self.remaining_words) == 0:
                self.game_timer.stop()
                self.is_playing = False
                self._stop_recognition()
                self._show_game_result("게임 클리어! 🎉", f"모든 단어를 맞혔습니다!\n최종 점수: {self.score}점")
        else:
            if os.path.exists("failed_sound.wav"):
                QSound.play("failed_sound.wav")
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
        if self.is_waiting_for_user:
            return
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
        self.webcam_preview_label.setHidden(True)
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
        
    def _on_body_status_received(self, is_detected: bool):
        """
        스레드가 보내준 진짜 어깨·손 인식 결과(True/False)를 받아 처리하는 함수입니다.
        관람객이 카메라 앞에서 바른 자세를 잡고 있을 때만 카운트가 올라갑니다.
        """
        if not self.is_waiting_for_user or self.is_counting_down:
            return  # 이미 카운트다운 중이거나 게임 중이면 무시

        if is_detected:
            # 🌟 관람객이 어깨와 손을 올리고 있을 때만 프레임 카운트 증가!
            self.ready_frame_count += 1
            
            if self.ready_frame_count >= self.required_frames:
                self.is_counting_down = True  # 중복 트리거 방지 잠금
                
                # "인식 완료!" 연출 팝업 띄우기
                self.fx_overlay.setText("✨ 인식 완료! ✨")
                self.fx_overlay.setStyleSheet("""
                    QLabel {
                        font-size: 50px; 
                        font-weight: bold; 
                        color: #2ECC71;
                        background-color: rgba(255, 255, 255, 0.85); 
                        border-radius: 20px;
                        padding: 20px;
                    }
                """)
                self.fx_overlay.setHidden(False)
                self.fx_overlay.raise_()
                
                # 1초 뒤에 진짜 카운트다운(3, 2, 1) 시작 함수로 점프!
                QTimer.singleShot(1000, self._start_real_countdown)
        else:
            # 💡 관람객이 자리를 비우거나 자세가 틀어지면 카운트를 다시 0으로 초기화 (안전장치)
            if self.ready_frame_count > 0:
                self.ready_frame_count = 0