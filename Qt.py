from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QPushButton, QVBoxLayout

app = QApplication([])

window = QWidget()
window.setWindowTitle("Hello PyQt5")

layout = QVBoxLayout()

label = QLabel("欢迎使用 PyQt5！")
button = QPushButton("点击我")

def on_click():
    label.setText("你点击了按钮！")

button.clicked.connect(on_click)

layout.addWidget(label)
layout.addWidget(button)
window.setLayout(layout)
window.show()

app.exec_()
