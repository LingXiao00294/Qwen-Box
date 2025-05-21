# app/widgets/chat_area.py

from PyQt6.QtWidgets import QTextEdit
from PyQt6.QtGui import QTextCursor, QColor, QFont
from PyQt6.QtCore import QTimer, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, QAbstractAnimation

class ChatArea(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ChatArea")
        self.setReadOnly(True)
        # 样式将通过外部 QSS 文件加载
        self.currentCharIndex = 0
        self.animation_timers = [] # Store timers to manage them
        self.current_message_spans = []
        self.streaming_message_open = False # Flag to indicate if an assistant message stream is active

    def _escape_html(self, text):
        # Basic HTML escaping
        return str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    def append_message(self, role: str, message: str):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        escaped_message = self._escape_html(message)

        if role == "user":
            if self.streaming_message_open: # Finalize any open assistant stream before user message
                self.finalize_stream()
            html = f'<div style="color:#4CAF50; margin: 8px 0;"><b>你：</b>{escaped_message}</div><br>'
            cursor.insertHtml(html)
        elif role == "assistant":
            if not message: # This is the start of a new stream (placeholder)
                if self.streaming_message_open:
                    self.finalize_stream() # Close previous stream if any
                # Start a new streaming message structure, leaving content span open
                html_prefix = f'<div style="color:#FFA726; margin: 8px 0;"><b>Qwen：</b><span class="assistant-content">' # Open span
                cursor.insertHtml(html_prefix)
                self.streaming_message_open = True
            else: # This is a non-streaming, complete assistant message
                if self.streaming_message_open:
                    self.finalize_stream()
                html = f'<div style="color:#FFA726; margin: 8px 0;"><b>Qwen：</b><span class="assistant-content">{escaped_message}</span></div><br>'
                cursor.insertHtml(html)
        else: # Other roles (e.g., system, not typically displayed directly like this)
            if self.streaming_message_open:
                self.finalize_stream()
            html = f'<div style="margin: 8px 0;"><b>{self._escape_html(role)}：</b>{escaped_message}</div><br>'
            cursor.insertHtml(html)
        
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def stream_token(self, token_text: str):
        """Appends a token to the currently open assistant message stream."""
        if self.streaming_message_open:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            # Insert HTML escaped text into the open span
            escaped_token = self._escape_html(token_text)
            # Using insertText here is generally safer for plain text tokens
            # as it handles the QTextEdit's internal representation correctly.
            # If tokens could contain HTML to be rendered, insertHtml would be needed.
            cursor.insertText(escaped_token)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
        # else:
            # print("[ChatArea WARNING] stream_token called but no stream is open.")

    def finalize_stream(self):
        """Closes the HTML tags for the current assistant message stream."""
        if self.streaming_message_open:
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.End)
            # Close the content span and the message div, then add a line break for separation
            cursor.insertHtml('</span></div><br>') 
            self.setTextCursor(cursor)
            self.ensureCursorVisible()
            self.streaming_message_open = False
        # else:
            # print("[ChatArea WARNING] finalize_stream called but no stream was open.")