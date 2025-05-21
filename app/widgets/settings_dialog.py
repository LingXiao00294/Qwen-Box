from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QListWidget, QListWidgetItem, QHBoxLayout, QInputDialog, QMessageBox
from PyQt6.QtCore import Qt
import config

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('总体配置')
        self.setMinimumWidth(400)
        layout = QVBoxLayout(self)

        # 名称
        layout.addWidget(QLabel('配置名称:'))
        self.name_edit = QLineEdit()
        layout.addWidget(self.name_edit)

        # API Key
        layout.addWidget(QLabel('API Key:'))
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.api_key_edit)

        # 模型列表
        layout.addWidget(QLabel('模型列表:'))
        self.model_list = QListWidget()
        self.model_list.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        layout.addWidget(self.model_list)

        btn_layout = QHBoxLayout()
        self.add_model_btn = QPushButton('添加模型')
        self.remove_model_btn = QPushButton('删除选中')
        btn_layout.addWidget(self.add_model_btn)
        btn_layout.addWidget(self.remove_model_btn)
        layout.addLayout(btn_layout)

        self.add_model_btn.clicked.connect(self.add_model)
        self.remove_model_btn.clicked.connect(self.remove_model)

        # 底部按钮
        self.save_btn = QPushButton('保存')
        self.cancel_btn = QPushButton('取消')
        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.save_btn)
        bottom_layout.addWidget(self.cancel_btn)
        layout.addLayout(bottom_layout)

        self.save_btn.clicked.connect(self.save_config)
        self.cancel_btn.clicked.connect(self.reject)

        self.load_config()

    def load_config(self):
        cfg = config.get_config()
        self.name_edit.setText(cfg.get('name', ''))
        self.api_key_edit.setText(cfg.get('api_key', ''))
        self.model_list.clear()
        for m in cfg.get('models', []):
            self.model_list.addItem(m)

    def save_config(self):
        cfg = {
            'name': self.name_edit.text().strip(),
            'api_key': self.api_key_edit.text().strip(),
            'api_base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
            'models': [self.model_list.item(i).text() for i in range(self.model_list.count())]
        }
        config.set_config(cfg)
        QMessageBox.information(self, '提示', '配置已保存！')
        self.accept()

    def add_model(self):
        text, ok = QInputDialog.getText(self, '添加模型', '模型名称:')
        if ok and text.strip():
            self.model_list.addItem(text.strip())

    def remove_model(self):
        row = self.model_list.currentRow()
        if row >= 0:
            self.model_list.takeItem(row)
        else:
            QMessageBox.warning(self, '提示', '请先选中要删除的模型。')

    def get_config(self):
        return {
            'name': self.name_edit.text().strip(),
            'api_key': self.api_key_edit.text().strip(),
            'models': [self.model_list.item(i).text() for i in range(self.model_list.count())]
        } 