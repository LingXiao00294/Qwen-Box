# main.py

import sys
from PyQt6.QtWidgets import QApplication
from app.chat_window import ChatWindow
import config  # 导入配置


def main():
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
