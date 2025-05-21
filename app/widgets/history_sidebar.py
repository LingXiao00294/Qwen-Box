# app/widgets/history_sidebar.py

from typing import Optional
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout, # Added QHBoxLayout
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox, # Added QMessageBox
    QDialog,
    QLineEdit,
    QTextEdit,
    QDialogButtonBox,
    QLabel,
    QAbstractItemView, # Import QAbstractItemView
)

from PyQt6.QtCore import pyqtSignal, Qt
from app.history_manager import HistoryManager

class HistorySidebar(QWidget):
    session_selected = pyqtSignal(str)  # Emits session_id when a session is selected
    new_chat_requested = pyqtSignal()
    config_requested = pyqtSignal()  # 新增信号

    def __init__(self, history_manager: HistoryManager, parent=None):
        super().__init__(parent)
        self.history_manager = history_manager
        self._init_ui()
        self.load_history()

    def _init_ui(self):
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)

        # Top bar with New Chat button
        self.top_bar_layout = QHBoxLayout()
        self.new_chat_button = QPushButton("➕ 新建对话")
        self.new_chat_button.setObjectName("NewChatButton")
        self.new_chat_button.clicked.connect(self.new_chat_requested.emit)
        self.top_bar_layout.addWidget(self.new_chat_button)
        self.layout.addLayout(self.top_bar_layout)

        self.history_list_widget = QListWidget()
        self.history_list_widget.setObjectName("HistoryList")
        self.history_list_widget.itemClicked.connect(self._on_item_clicked)
        self.history_list_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.history_list_widget.customContextMenuRequested.connect(self._show_context_menu)
        self.layout.addWidget(self.history_list_widget)

        # 左下角配置按钮
        self.bottom_bar_layout = QHBoxLayout()
        self.config_button = QPushButton("⚙ 配置")
        self.config_button.setObjectName("ConfigButton")
        self.config_button.clicked.connect(self.config_requested.emit)
        self.bottom_bar_layout.addWidget(self.config_button)
        self.layout.addLayout(self.bottom_bar_layout)

        self.setLayout(self.layout)
        self.setFixedWidth(200) # Adjust width as needed

    def _on_item_clicked(self, item: QListWidgetItem):
        session_id = item.data(Qt.ItemDataRole.UserRole) # Get session_id stored in the item
        if session_id:
            self.session_selected.emit(session_id)

    def load_history(self):
        self.history_list_widget.clear()
        session_ids = self.history_manager.get_all_session_ids()
        for session_id in session_ids:
            title = self.history_manager.get_session_title(session_id)
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, session_id)
            item.setToolTip(f"会话ID: {session_id}")
            self.history_list_widget.addItem(item)

    def _show_context_menu(self, position):
        item = self.history_list_widget.itemAt(position)
        if not item:
            return

        session_id = item.data(Qt.ItemDataRole.UserRole)
        if not session_id:
            return

        menu = QMenu(self)
        favorite_action = menu.addAction("⭐ 收藏")
        delete_action = menu.addAction("🗑️ 删除")
        config_action = menu.addAction("⚙️ 配置")
        edit_action = menu.addAction("✏️ 编辑会话信息")
        favorite_action.triggered.connect(lambda: self._favorite_session(session_id))
        delete_action.triggered.connect(lambda: self._confirm_delete_session(session_id))
        config_action.triggered.connect(lambda: self._config_session(session_id))
        edit_action.triggered.connect(lambda: self._edit_session_info(session_id))
        menu.exec(self.history_list_widget.mapToGlobal(position))

    def _confirm_delete_session(self, session_id: str):
        confirm_dialog = QMessageBox()
        confirm_dialog.setWindowTitle("删除确认")
        confirm_dialog.setText(f"您确定要删除会话 '{session_id}' 吗？此操作无法撤销。")
        confirm_dialog.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm_dialog.setDefaultButton(QMessageBox.StandardButton.No)
        delete_button = confirm_dialog.button(QMessageBox.StandardButton.Yes)
        delete_button.setText("删除")
        no_button = confirm_dialog.button(QMessageBox.StandardButton.No)
        no_button.setText("取消")

        ret = confirm_dialog.exec()
        if ret == QMessageBox.StandardButton.Yes:
            self._delete_session(session_id)

    def _delete_session(self, session_id: str):
        filepath = self.history_manager._get_session_filepath(session_id)
        try:
            import os
            os.remove(filepath)
            print(f"[HistorySidebar] Session '{session_id}' deleted.")
            self.load_history() # Refresh the list
            # Optionally, emit a signal if the currently active chat was deleted
            # self.active_chat_deleted.emit(session_id)
        except OSError as e:
            print(f"[HistorySidebar] Error deleting session file '{filepath}': {e}")
            QMessageBox.warning(self, "删除失败", f"无法删除会话文件：{e}")

    def _favorite_session(self, session_id: str):
        # Placeholder for favorite functionality
        print(f"[HistorySidebar] Session '{session_id}' marked as favorite (not implemented yet).")
        QMessageBox.information(self, "提示", f"会话 '{session_id}' 已标记为收藏（功能待实现）。")

    def _config_session(self, session_id: str):
        # Placeholder for config functionality
        print(f"[HistorySidebar] Config for session '{session_id}' (not implemented yet).")
        QMessageBox.information(self, "提示", f"配置会话 '{session_id}'（功能待实现）。")

    def _edit_session_info(self, session_id):
        data = self.history_manager.load_chat_session(session_id)
        if not data:
            QMessageBox.warning(self, "错误", "无法加载会话信息")
            return
        dlg = SessionInfoDialog(data.get('title', ''), data.get('system_prompt', ''), self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_title, new_prompt = dlg.get_values()
            data['title'] = new_title or '新对话'
            data['system_prompt'] = new_prompt or '你是一个有帮助的AI助手。'
            self.history_manager.save_chat_session(session_id, data)
            self.load_history()

    def add_session_to_top(self, session_id: str, preview: Optional[str] = None):
        title = self.history_manager.get_session_title(session_id)
        current_item = None
        for i in range(self.history_list_widget.count()):
            item = self.history_list_widget.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == session_id:
                current_item = item
                break
        if current_item:
            current_item.setText(title)
            current_item.setToolTip(f"会话ID: {session_id}")
            self.history_list_widget.setCurrentItem(current_item)
        else:
            new_item = QListWidgetItem(title)
            new_item.setData(Qt.ItemDataRole.UserRole, session_id)
            new_item.setToolTip(f"会话ID: {session_id}")
            self.history_list_widget.insertItem(0, new_item)
            self.history_list_widget.setCurrentItem(new_item)

    def select_session(self, session_id: str, move_to_top_on_select=False):
        """Selects a session in the list by its ID."""
        for i in range(self.history_list_widget.count()):
            item = self.history_list_widget.item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == session_id:
                if move_to_top_on_select and self.history_list_widget.row(item) != 0:
                    # This part is now mainly for new chats or explicit moves
                    self.history_list_widget.takeItem(self.history_list_widget.row(item))
                    self.history_list_widget.insertItem(0, item)
                self.history_list_widget.setCurrentItem(item)
                # Scroll to the item to make sure it's visible
                self.history_list_widget.scrollToItem(item, QAbstractItemView.ScrollHint.PositionAtCenter)
                break

class SessionInfoDialog(QDialog):
    def __init__(self, title='', system_prompt='', parent=None):
        super().__init__(parent)
        self.setWindowTitle('会话信息')
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel('标题:'))
        self.title_edit = QLineEdit(title)
        layout.addWidget(self.title_edit)
        layout.addWidget(QLabel('System Prompt:'))
        self.prompt_edit = QTextEdit(system_prompt)
        self.prompt_edit.setFixedHeight(80)
        layout.addWidget(self.prompt_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    def get_values(self):
        return self.title_edit.text().strip(), self.prompt_edit.toPlainText().strip()

if __name__ == '__main__':
    from PyQt6.QtWidgets import QApplication
    import sys

    # Create a dummy history manager for testing
    test_history_dir = "../chat_history_sidebar_test"
    if not os.path.exists(test_history_dir):
        os.makedirs(test_history_dir)
    
    hm = HistoryManager(history_dir=test_history_dir)
    # Create some dummy sessions for testing
    hm.save_chat_session("test_session_1", [{"role": "user", "content": "Hello from session 1"}])
    hm.save_chat_session("test_session_2", [{"role": "user", "content": "Test content for session 2 which is a bit longer to see how it wraps or truncates"}])

    app = QApplication(sys.argv)
    sidebar = HistorySidebar(hm)
    sidebar.show()
    sys.exit(app.exec())