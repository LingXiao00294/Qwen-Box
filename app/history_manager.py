# app/history_manager.py
import json
import os
from datetime import datetime
from typing import List, Dict, Optional

class HistoryManager:
    def __init__(self, history_dir: str = "chat_history"):
        self.history_dir = history_dir
        if not os.path.exists(self.history_dir):
            os.makedirs(self.history_dir)

    def _get_session_filepath(self, session_id: str) -> str:
        return os.path.join(self.history_dir, f"{session_id}.json")

    def save_chat_session(self, session_id: str, messages: list, title: str = None, system_prompt: str = None) -> None:
        """
        保存会话，包含标题和system prompt。
        """
        filepath = self._get_session_filepath(session_id)
        # 兼容旧调用方式
        if isinstance(messages, dict):
            data = messages
        else:
            data = {
                "title": title or "新对话",
                "system_prompt": system_prompt or "你是一个有帮助的AI助手。",
                "messages": messages
            }
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            print(f"[HistoryManager] Session '{session_id}' saved to {filepath}")
        except IOError as e:
            print(f"[HistoryManager] Error saving session '{session_id}': {e}")

    def load_chat_session(self, session_id: str):
        """
        加载会话，返回dict，兼容旧格式。
        旧格式会话加载时，尝试使用第一个用户消息作为标题。
        """
        filepath = self._get_session_filepath(session_id)
        if not os.path.exists(filepath):
            return None
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 兼容旧格式 (只有消息列表)
            if isinstance(data, list):
                # 尝试从旧格式消息列表中提取第一个用户消息作为标题
                first_user_message = "(无内容)"
                for msg in data:
                    if msg.get("role") == "user" and msg.get("content"):
                        first_user_message = msg["content"][:30] + ('...' if len(msg["content"]) > 30 else '')
                        break

                return {
                    "title": first_user_message, # 使用第一个用户消息作为标题
                    "system_prompt": "你是一个有帮助的AI助手。", # 默认 system prompt
                    "messages": data
                }
            return data
        except (IOError, json.JSONDecodeError) as e:
            print(f"[HistoryManager] Error loading session '{session_id}': {e}")
            return None

    def get_session_title(self, session_id: str) -> str:
        data = self.load_chat_session(session_id)
        if data and isinstance(data, dict):
            return data.get("title", "新对话")
        return "新对话"

    def get_session_system_prompt(self, session_id: str) -> str:
        data = self.load_chat_session(session_id)
        if data and isinstance(data, dict):
            return data.get("system_prompt", "你是一个有帮助的AI助手。")
        return "你是一个有帮助的AI助手。"

    def get_session_messages(self, session_id: str):
        data = self.load_chat_session(session_id)
        if data and isinstance(data, dict):
            return data.get("messages", [])
        return data or []

    def get_session_preview(self, session_id: str) -> str:
        data = self.load_chat_session(session_id)
        if data and isinstance(data, dict):
            msgs = data.get("messages", [])
            for msg in msgs:
                if msg["role"] == "user":
                    return msg["content"][:30]
            return "(无内容)"
        elif isinstance(data, list):
            for msg in data:
                if msg["role"] == "user":
                    return msg["content"][:30]
            return "(无内容)"
        return "(无内容)"

    def get_all_session_ids(self) -> List[str]:
        """
        Returns a list of all saved session IDs (filenames without .json).
        Sorted by modification time, newest first.
        """
        try:
            files = [
                f for f in os.listdir(self.history_dir) 
                if os.path.isfile(os.path.join(self.history_dir, f)) and f.endswith(".json")
            ]
            # Sort by modification time, newest first
            files.sort(key=lambda f: os.path.getmtime(os.path.join(self.history_dir, f)), reverse=True)
            session_ids = [os.path.splitext(f)[0] for f in files]
            return session_ids
        except OSError as e:
            print(f"[HistoryManager] Error listing session files: {e}")
            return []

    def generate_session_id(self) -> str:
        """Generates a new session ID based on the current timestamp."""
        return datetime.now().strftime("%Y%m%d_%H%M%S_%f")

if __name__ == '__main__':
    # Example Usage
    manager = HistoryManager(history_dir="../chat_history_test") # Use a test directory

    # Clean up test directory if it exists from previous runs
    if os.path.exists(manager.history_dir):
        for f in os.listdir(manager.history_dir):
            os.remove(os.path.join(manager.history_dir, f))
        os.rmdir(manager.history_dir)
    
    manager = HistoryManager(history_dir="../chat_history_test") # Recreate

    session1_id = manager.generate_session_id()
    messages1 = [
        {"role": "user", "content": "Hello AI!"},
        {"role": "assistant", "content": "Hello User! How can I help you today?"}
    ]
    manager.save_chat_session(session1_id, messages1)

    session2_id = manager.generate_session_id()
    messages2 = [
        {"role": "user", "content": "What's the weather like?"},
        {"role": "assistant", "content": "It's sunny today!"}
    ]
    manager.save_chat_session(session2_id, messages2)

    print("All session IDs:", manager.get_all_session_ids())

    loaded_messages = manager.load_chat_session(session1_id)
    if loaded_messages:
        print(f"Loaded session '{session1_id}':", loaded_messages)
    
    print(f"Preview for session '{session1_id}':", manager.get_session_preview(session1_id))
    print(f"Preview for session '{session2_id}':", manager.get_session_preview(session2_id))

    # Clean up test directory
    if os.path.exists(manager.history_dir):
        for f in os.listdir(manager.history_dir):
            os.remove(os.path.join(manager.history_dir, f))
        os.rmdir(manager.history_dir)
        print("Cleaned up test directory.")