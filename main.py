import sys
from PyQt5.QtWidgets import QApplication, QStackedWidget
from PyQt5.QtCore import Qt

# 1. 직접 구현해 두신 각 모드의 뷰(View) 클래스들을 임포트합니다.
from views.main_view import MainView
from views.practice_view import PracticeView
from views.real_game.game_view import GameView  # real_game 폴더 안의 game_view.py

class MainController(QStackedWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("손끝으로 전하는 마음 - 수어 학습 키오스크")
        self.resize(1280, 720)
        
        # 1. 각 화면 인스턴스 생성
        self.main_view = MainView()
        self.practice_view = PracticeView()
        self.game_view = GameView()
        
        # 2. QStackedWidget에 화면 등록 (인덱스 순서 부여)
        self.addWidget(self.main_view)      # Index 0: 메인 화면
        self.addWidget(self.practice_view)  # Index 1: 연습 모드 화면
        self.addWidget(self.game_view)      # Index 2: 실전 게임 모드 화면
        
        # 3. 메인 화면 -> 연습/게임 모드 전환 시그널 연결
        self.main_view.request_practice_mode.connect(self.go_to_practice)
        self.main_view.request_game_mode.connect(self.go_to_game)
        
        # 4. 연습 화면 / 게임 화면 -> 메인 화면 복귀 시그널 연결 (★ 핵심 수정 부분)
        # GameView 내부의 메인 복귀 시그널이나 버튼 클릭 이벤트 연동
        if hasattr(self.game_view, 'request_main_menu'):
            self.game_view.request_main_menu.connect(self.go_to_main)
        elif hasattr(self.game_view, 'back_btn'):
            self.game_view.back_btn.clicked.connect(self.go_to_main)

        # PracticeView 내부의 메인 복귀 시그널이나 버튼 클릭 이벤트 연동
        if hasattr(self.practice_view, 'request_main_menu'):
            self.practice_view.request_main_menu.connect(self.go_to_main)
        elif hasattr(self.practice_view, 'back_btn'):
            self.practice_view.back_btn.clicked.connect(self.go_to_main)
        
        # 처음 실행 시 메인 화면(Index 0) 세팅
        self.setCurrentIndex(0)

    def go_to_practice(self):
        """연습 모드 화면(Index 1)으로 전환"""
        self.setCurrentIndex(1)
        # 연습 화면으로 넘어갈 때 카메라/재생 등을 재시작하는 메서드가 있다면 호출
        if hasattr(self.practice_view, 'start_mode'):
            self.practice_view.start_mode()

    def go_to_game(self):
        """실전 게임 모드 화면(Index 2)으로 전환"""
        self.setCurrentIndex(2)
        # 게임 화면으로 넘어갈 때 타이머/카메라를 시작하는 메서드가 있다면 호출
        if hasattr(self.game_view, 'start_game'):
            self.game_view.start_game()

    def go_to_main(self):
        """다시 메인 화면(Index 0)으로 전환"""
        # ★ 전시용 실무 팁: 메인으로 돌아갈 때 게임이나 카메라 프로세스를 정지해주어야 메모리 누수나 버벅임이 없습니다.
        if hasattr(self.game_view, 'stop_game'):
            self.game_view.stop_game()
            
        if hasattr(self.practice_view, 'stop_mode'):
            self.practice_view.stop_mode()

        self.setCurrentIndex(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = MainController()
    controller.show()
    sys.exit(app.exec_())