# app/widgets/input_bar.py

from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLineEdit, QPushButton
from PyQt6.QtCore import pyqtSignal

class InputBar(QWidget):
    send_clicked = pyqtSignal(str) # 定义信号，在发送按钮点击时发射

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InputBar")
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0) # 移除边距，使其更紧凑

        self.input_box = QLineEdit()
        self.input_box.setObjectName("InputBox")
        self.input_box.setPlaceholderText("输入你的问题...")
        # 样式将通过外部 QSS 文件加载
        self.input_box.returnPressed.connect(self._on_send_clicked) # 支持回车发送

        self.send_button = QPushButton("发送")
        self.send_button.setObjectName("SendButton")
        # 样式将通过外部 QSS 文件加载
        self.send_button.clicked.connect(self._on_send_clicked)

        layout.addWidget(self.input_box, stretch=4)
        layout.addWidget(self.send_button, stretch=1)
        self.setLayout(layout)

    def _on_send_clicked(self):
        user_input = self.input_box.text().strip()
        if user_input:
            self.send_clicked.emit(user_input) # 发射信号
            self.input_box.clear()

    def get_input_text(self) -> str:
        return self.input_box.text().strip()

    def clear_input(self):
        self.input_box.clear()