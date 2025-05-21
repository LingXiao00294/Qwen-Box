# app/chat_window.py

import asyncio
import threading
import json
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QMessageBox, QHBoxLayout, QSplitter
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from app.qwen_api import QwenAPIClient, QwenAPIException
from app.widgets.config_bar import ConfigBar
from app.widgets.chat_area import ChatArea
from app.widgets.input_bar import InputBar
from app.history_manager import HistoryManager
from app.widgets.history_sidebar import HistorySidebar, SessionInfoDialog


# 用于在非GUI线程中更新GUI的信号载体
class WorkerSignals(QObject):
    token_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    finished = pyqtSignal()


class ChatWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qwen AI 桌面助手")
        self.resize(1000, 700) # Increased size to accommodate sidebar

        # 初始化可能在后续逻辑中条件访问的成员
        try:
            self.qwen_client = QwenAPIClient()
        except ValueError as e:
            QMessageBox.warning(self, "API初始化错误", str(e))
            self.qwen_client = None
        self.config_bar = None
        self.chat_area = None
        self.input_bar = None
        self.status_label = None
        self.history_sidebar = None # Added for history sidebar

        self._load_styles()
        
        self.history_manager = HistoryManager()
        self.current_session_id = None
        self.current_messages = []
        self.assistant_response_buffer = ""

        self._init_ui()
        self._connect_signals()

        self.history_sidebar.load_history()
        self._load_latest_session_on_startup()

        self.input_bar.input_box.setFocus()

    def _load_styles(self):
        try:
            with open("app/styles.qss", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("错误：未找到样式文件 app/styles.qss")
        except Exception as e:
            print(f"加载样式文件时出错: {e}")

    def _init_ui(self):
        # Main horizontal layout
        self.root_layout = QHBoxLayout(self)
        self.setLayout(self.root_layout)

        # History Sidebar (Left)
        self.history_sidebar = HistorySidebar(self.history_manager)
        
        # Main chat area (Right)
        self.chat_panel_widget = QWidget()
        self.main_layout = QVBoxLayout(self.chat_panel_widget) # Layout for the right panel
        self.main_layout.setContentsMargins(0,0,0,0)

        self.config_bar = ConfigBar()
        self.chat_area = ChatArea()
        self.input_bar = InputBar()

        self.status_label = QLabel("就绪")
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)

        self.main_layout.addWidget(self.config_bar)
        self.main_layout.addWidget(self.chat_area, stretch=1)
        self.main_layout.addWidget(self.input_bar)
        self.main_layout.addWidget(self.status_label)
        self.chat_panel_widget.setLayout(self.main_layout)

        # Splitter to allow resizing sidebar and chat panel
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.addWidget(self.history_sidebar)
        self.splitter.addWidget(self.chat_panel_widget)
        self.splitter.setSizes([200, 800]) # Initial sizes
        self.splitter.setCollapsible(0, False) # Prevent sidebar from collapsing completely
        self.splitter.setCollapsible(1, False)

        self.root_layout.addWidget(self.splitter)

    def _connect_signals(self):
        if self.input_bar:
            self.input_bar.send_clicked.connect(self.on_user_input)
        self.signals = WorkerSignals()  # 用于线程通信
        self.signals.token_received.connect(self._handle_stream_token)
        self.signals.error_occurred.connect(self._handle_stream_error)
        self.signals.finished.connect(self._handle_stream_finished)
        if self.history_sidebar:
            self.history_sidebar.session_selected.connect(self._load_chat_session)
            self.history_sidebar.new_chat_requested.connect(self._start_new_chat_session)
            self.history_sidebar.config_requested.connect(self._show_config_dialog)

        self.stream_buffer = ""  # 存储待处理的字符
        self.char_display_timer = QTimer(self)  # 用于逐字显示的定时器
        self.char_display_timer.timeout.connect(self._display_next_char)
        self.char_display_interval = 50  # ms, 字符显示间隔
        self.assistant_response_buffer = "" # Buffer for the complete assistant response in a stream

    def on_user_input(self, user_input: str):
        if not user_input:
            return
        if self.chat_area:
            self.chat_area.append_message("user", user_input)
        # 获取当前会话的system prompt
        session_data = self.history_manager.load_chat_session(self.current_session_id)
        system_prompt = session_data.get('system_prompt', '你是一个有帮助的AI助手。') if session_data else '你是一个有帮助的AI助手。'
        # 构造messages，首条为system prompt
        messages = [{"role": "system", "content": system_prompt}]
        messages += self.current_messages
        messages.append({"role": "user", "content": user_input})
        self.current_messages.append({"role": "user", "content": user_input})
        if self.status_label:
            self.status_label.setText("正在思考...")
        if not self.qwen_client:
            if self.chat_area:
                self.chat_area.append_message(
                    "assistant", "错误：Qwen API客户端未初始化。"
                )
            if self.status_label:
                self.status_label.setText("错误")
            return
        self.is_first_token = True  # Reset for the new stream
        self.assistant_response_buffer = "" # Clear buffer for new response
        # 启动异步任务在子线程中执行
        thread = threading.Thread(
            target=self._run_qwen_request_in_thread, args=(messages,)
        )
        thread.start()

    def _run_qwen_request_in_thread(self, messages_context: list[dict[str,str]]):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self._get_qwen_response_async(messages_context))
        loop.close()

    async def _get_qwen_response_async(self, messages_context: list[dict[str,str]]):
        if not self.qwen_client:
            self.signals.error_occurred.emit("Qwen API客户端未初始化。")
            return

        current_top_p = (
            self.config_bar.get_top_p_value()
            if self.config_bar
            else self.qwen_client.top_p
        )
        self.qwen_client.top_p = current_top_p
        self.qwen_client.stream = True
        
        print(f"[DEBUG] _get_qwen_response_async: Sending messages to Qwen API: {messages_context}")
        print(f"[DEBUG] _get_qwen_response_async: Using top_p: {self.qwen_client.top_p}, stream: {self.qwen_client.stream}")

        def stream_callback_adapter(token):
            # print(f"[DEBUG] stream_callback_adapter: Received token: {token}")
            self.signals.token_received.emit(token)

        try:
            print("[DEBUG] _get_qwen_response_async: Calling qwen_client.chat_completion")
            await self.qwen_client.chat_completion(
                messages=messages_context, # Use the provided context
                callback=stream_callback_adapter
            )
            print("[DEBUG] _get_qwen_response_async: qwen_client.chat_completion finished")
        except QwenAPIException as e:
            print(f"[DEBUG] _get_qwen_response_async: QwenAPIException: {e.error_type} - {e.message}")
            user_message, error_details = QwenAPIClient.format_error_message(e)
            print(f"[ERROR] {e.error_type}: {e.message}")
            print(f"[ERROR] Details: {json.dumps(error_details, ensure_ascii=False, indent=2)}")
            self.signals.error_occurred.emit(user_message)
        except Exception as e:
            print(f"[DEBUG] _get_qwen_response_async: Unexpected error: {e}")
            user_message, error_details = QwenAPIClient.format_error_message(e)
            print(f"[ERROR] Unexpected error: {error_details}")
            self.signals.error_occurred.emit(f"发生未知错误: {e}")
        finally:
            print("[DEBUG] _get_qwen_response_async: Emitting finished signal")
            self.signals.finished.emit()

    def _handle_stream_token(self, token: str):
        # print(f"[ChatWindow DEBUG] _handle_stream_token: Received token: '{token}'")
        if self.is_first_token and self.chat_area:
            # print("[ChatWindow DEBUG] First token, creating assistant message placeholder.")
            self.chat_area.append_message(
                "assistant", ""
            )  # Create placeholder structure
            self.is_first_token = False
        
        self.assistant_response_buffer += token # Accumulate full assistant response
        self.stream_buffer += token
        if not self.char_display_timer.isActive():
            # print("[ChatWindow DEBUG] Starting char_display_timer.")
            self.char_display_timer.start(self.char_display_interval)

    def _display_next_char(self):
        if not self.stream_buffer:
            self.char_display_timer.stop()
            return

        char_to_display = self.stream_buffer[0]
        self.stream_buffer = self.stream_buffer[1:]

        if self.chat_area:
            self.chat_area.stream_token(char_to_display)

        if not self.stream_buffer:  # 如果缓冲区空了，停止定时器
            self.char_display_timer.stop()

    def _handle_stream_error(self, error_message: str):
        """处理流式输出过程中的错误"""
        if self.chat_area:
            if self.chat_area.streaming_message_open: # Check if a stream was active
                self.chat_area.finalize_stream() # Finalize stream even on error
            formatted_message = (
                f"<span style='color: #FF5252;'>🛑 错误: {error_message}</span>"
            )
            self.chat_area.append_message("system", formatted_message) # Use "system" role for errors

        if self.status_label:
            self.status_label.setText("错误")

        print(f"[ERROR] Stream error: {error_message}")
        if self.char_display_timer.isActive():
            self.char_display_timer.stop()
        self.stream_buffer = "" 
        self.assistant_response_buffer = "" 

    def _handle_stream_finished(self):
        while self.stream_buffer:
            self._display_next_char()
        
        if self.char_display_timer.isActive():
            self.char_display_timer.stop()

        if self.chat_area and self.chat_area.streaming_message_open:
            self.chat_area.finalize_stream()
        
        if self.assistant_response_buffer:
            self.current_messages.append({"role": "assistant", "content": self.assistant_response_buffer})
            if self.current_session_id:
                # 保存时带上标题和system prompt
                session_data = self.history_manager.load_chat_session(self.current_session_id)
                title = session_data.get('title', '新对话') if session_data else '新对话'
                system_prompt = session_data.get('system_prompt', '你是一个有帮助的AI助手。') if session_data else '你是一个有帮助的AI助手。'
                self.history_manager.save_chat_session(
                    self.current_session_id,
                    self.current_messages,
                    title=title,
                    system_prompt=system_prompt
                )
                if self.history_sidebar:
                    self.history_sidebar.add_session_to_top(self.current_session_id, title)
            self.assistant_response_buffer = ""

        if self.status_label:
            self.status_label.setText("就绪")
        print("[ChatWindow DEBUG] Stream finished and finalized.")

    def _start_new_chat_session(self, add_to_sidebar=True):
        # 弹窗输入标题和system prompt
        dlg = SessionInfoDialog(parent=self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            title, system_prompt = dlg.get_values()
            title = title or '新对话'
            system_prompt = system_prompt or '你是一个有帮助的AI助手。'
        else:
            # 用户取消则不新建
            return
        self.current_session_id = self.history_manager.generate_session_id()
        self.current_messages = []
        if self.chat_area:
            self.chat_area.clear()
        # 保存空会话（带标题和system prompt）
        self.history_manager.save_chat_session(
            self.current_session_id,
            [],
            title=title,
            system_prompt=system_prompt
        )
        if add_to_sidebar:
            self.history_sidebar.add_session_to_top(self.current_session_id, title)
            self.history_sidebar.select_session(self.current_session_id)
        print(f"[ChatWindow] Started new session: {self.current_session_id}")

    def _load_latest_session_on_startup(self):
        all_sessions = self.history_manager.get_all_session_ids()
        if all_sessions:
            latest_session_id = all_sessions[0] # get_all_session_ids returns sorted by newest first
            self._load_chat_session(latest_session_id)
        else:
            # No history, so don't load or create anything. Chat area will be empty.
            self.current_session_id = None
            self.current_messages = []
            if self.chat_area:
                self.chat_area.clear()
            print("[ChatWindow] No history found. Starting with an empty session.")

    def _load_chat_session(self, session_id: str):
        session_data = self.history_manager.load_chat_session(session_id)
        if session_data:
            # Ensure we have the messages list
            messages = session_data.get('messages', [])
            self.current_session_id = session_id
            # Store the loaded messages including system prompt if it exists in the file
            # However, we should only display user/assistant messages
            self.current_messages = messages # Keep full history internally

            if self.chat_area:
                self.chat_area.clear()
                # Display only user and assistant messages
                for msg in messages:
                    if msg['role'] in ['user', 'assistant']:
                         self.chat_area.append_message(msg['role'], msg['content'])

            if self.status_label:
                # Use the title for status label if available
                title = session_data.get('title', session_id[:8] + '...')
                self.status_label.setText(f"已加载会话: {title}")

            if self.history_sidebar:
                # Update the sidebar to show title
                title = session_data.get('title', session_id[:8] + '...')
                self.history_sidebar.add_session_to_top(session_id, title) # Use title

        else:
            if self.status_label:
                self.status_label.setText(f"无法加载会话: {session_id}")
            QMessageBox.warning(self, "加载失败", f"无法加载会话 '{session_id}'。文件可能已损坏或被删除。")
            # Fallback to a new chat session if loading fails
            self._start_new_chat_session()

    async def mock_api_call(self, text):
        # 模拟 API 延迟
        await asyncio.sleep(0.5)
        return "这是一个示例回复，当前输入是：" + text

    def _show_config_dialog(self):
        # TODO: 弹出配置页面
        from app.widgets.settings_dialog import SettingsDialog
        dlg = SettingsDialog(self)
        dlg.exec()
