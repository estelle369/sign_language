# 하단 단어 목록 리스트 UI 위젯
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QAbstractItemView
from PyQt5.QtCore import pyqtSignal, Qt

class WordListWidget(QListWidget):
    """
    수어 학습 단어 목록을 카드 형태로 보여주는 위젯
    """
    # 단어가 선택되었을 때 발송할 커스텀 시그널 (선택된 단어 정보 전달)
    word_selected = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        # 세로형 화면에 맞춘 스타일링 (터치/클릭 용이)
        self.setStyleSheet("""
            QListWidget {
                background-color: #F8F9FA;
                border: 2px solid #E9ECEF;
                border-radius: 12px;
                padding: 8px;
            }
            QListWidget::item {
                background-color: #FFFFFF;
                border: 1px solid #DEE2E6;
                border-radius: 8px;
                padding: 16px;
                margin-bottom: 8px;
                font-size: 18px;
                font-weight: bold;
                color: #333333;
            }
            QListWidget::item:selected {
                background-color: #4C6EF5;
                color: #FFFFFF;
                border: none;
            }
            QListWidget::item:hover {
                background-color: #EDF2FF;
            }
        """)
        self.itemClicked.connect(self._on_item_clicked)

    def set_words(self, word_data_list: list):
        """단어 리스트 데이터를 받아 아이템 생성"""
        self.clear()
        for data in word_data_list:
            item = QListWidgetItem(data["word"])
            # 사용자 정의 데이터(단어 정보 전체)를 아이템에 숨겨둠
            item.setData(Qt.UserRole, data)
            self.addItem(item)

        # 첫 번째 항목 기본 선택
        if self.count() > 0:
            self.setCurrentRow(0)
            self._on_item_clicked(self.item(0))

    def _on_item_clicked(self, item: QListWidgetItem):
        word_data = item.data(Qt.UserRole)
        self.word_selected.emit(word_data)