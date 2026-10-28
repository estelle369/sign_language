import sys
from PyQt5.QtWidgets import QApplication, QStackedWidget, QScrollArea, QVBoxLayout, QWidget
from PyQt5.QtCore import Qt

from views.main_view import MainView
from views.practice_game.practice_view import PracticeView
from views.real_game.game_view import GameView 

class MainController(QWidget):
    """
    [메인 컨트롤러] QStackedWidget을 이용해 메인, 연습, 실전 게임 화면 전환을 총괄하는 매니저
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("손끝으로 전하는 마음 - 수어 학습 키오스크")
        
        # 노트북 화면(가로)에서 세로형 UI를 테스트하기 좋은 창 크기 설정 (폭 700, 높이 950)
        self.resize(700, 950)
        
        # 전체 창을 채우는 기본 레이아웃
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. 화면 전환을 관리할 QStackedWidget 생성 (여러 장의 도화지 원리)
        self.stacked_widget = QStackedWidget()
        
        # 2. 각 화면 인스턴스 생성 및 스택에 등록
        self.main_view = MainView()
        self.practice_view = PracticeView()
        self.game_view = GameView()
        
        self.stacked_widget.addWidget(self.main_view)      # Index 0: 메인 화면
        self.stacked_widget.addWidget(self.practice_view)  # Index 1: 연습 모드 화면
        self.stacked_widget.addWidget(self.game_view)      # Index 2: 실전 게임 모드 화면
        
        # 3. 노트북 가로 화면에서도 세로형 UI 전체를 위아래로 스크롤하며 볼 수 있는 QScrollArea 도입
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)  # 내부 위젯 크기에 맞춰 스크롤 영역 유연 조절
        self.scroll_area.setWidget(self.stacked_widget)
        
        main_layout.addWidget(self.scroll_area)
        
        # 4. 메인 화면 -> 연습/게임 모드 전환 시그널 연결
        self.main_view.request_practice_mode.connect(self.go_to_practice)
        self.main_view.request_game_mode.connect(self.go_to_game)
        
        # 5. 💡 [수정 완료] 연습 화면 / 게임 화면 -> 메인 화면 복귀 시그널 통합 연결
        # 연습 모드에서 보낸 back_to_main_requested 신호를 go_to_main 함수와 연결합니다.
        if hasattr(self.practice_view, 'back_to_main_requested'):
            self.practice_view.back_to_main_requested.connect(self.go_to_main)
        elif hasattr(self.practice_view, 'request_main_menu'):
            self.practice_view.request_main_menu.connect(self.go_to_main)
        elif hasattr(self.practice_view, 'back_btn'):
            self.practice_view.back_btn.clicked.connect(self.go_to_main)

        # 게임 뷰 복귀 신호 연결
        if hasattr(self.game_view, 'request_main_menu'):
            self.game_view.request_main_menu.connect(self.go_to_main)
        elif hasattr(self.game_view, 'back_btn'):
            self.game_view.back_btn.clicked.connect(self.go_to_main)
        
        # 처음 실행 시 메인 화면(Index 0) 세팅
        self.stacked_widget.setCurrentIndex(0)

    def go_to_practice(self):
        """연습 모드 화면(Index 1)으로 전환"""
        self.stacked_widget.setCurrentIndex(1)
        if hasattr(self.practice_view, 'start_mode'):
            self.practice_view.start_mode()

    def go_to_game(self):
        """실전 게임 모드 화면(Index 2)으로 전환"""
        self.stacked_widget.setCurrentIndex(2)
        if hasattr(self.game_view, 'start_game'):
            self.game_view.start_game()

    def go_to_main(self):
        """다시 메인 화면(Index 0)으로 전환"""
        # ★ 실전 전시 팁: 메인으로 돌아올 때 영상이나 카메라 리소스를 확실히 정지시켜야 튕김 현상을 막습니다!
        if hasattr(self.game_view, 'stop_game'):
            self.game_view.stop_game()
            
        if hasattr(self.practice_view, 'stop_mode'):
            self.practice_view.stop_mode()
        # 우리가 practice_view에 만들어둔 hideEvent나 영상 정지 기능과 연동됩니다.

        self.stacked_widget.setCurrentIndex(0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    controller = MainController()
    controller.show()
    sys.exit(app.exec_())