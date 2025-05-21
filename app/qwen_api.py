# app/qwen_api.py

import os
import json
import traceback
from openai import AsyncOpenAI
from typing import List, Dict, Optional, Union, Callable, Any, Tuple
from dotenv import load_dotenv
import config
from app.models.qwen_plus_latest import QwenAPIClient, QwenAPIException

# 加载 .env 文件中的环境变量
load_dotenv()


class QwenAPIException(Exception):
    """自定义异常类，用于封装 Qwen API 调用过程中的异常"""

    def __init__(self, error_type: str, message: str, details: Optional[Dict] = None):
        """
        初始化异常

        :param error_type: 错误类型，如 'api_error', 'connection_error', 'auth_error' 等
        :param message: 错误消息
        :param details: 错误详情，可包含原始异常信息、请求参数等
        """
        self.error_type = error_type
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        return f"{self.error_type}: {self.message}"

    def to_dict(self) -> Dict:
        """将异常转换为字典格式，方便序列化"""
        return {
            "error_type": self.error_type,
            "message": self.message,
            "details": self.details,
        }


class QwenAPIClient:
    """
    封装兼容 OpenAI API 的模型调用
    支持异步请求和流式输出
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        top_p: float = 1.0,  # OpenAI default is 1.0
        max_tokens: int = 2048,
        stream: bool = True,
        base_url: Optional[str] = None,
    ):
        cfg = config.get_config()
        self.api_key = api_key or cfg.get('api_key')
        if not self.api_key:
            raise ValueError(
                "API Key 未设置，请提供 api_key 参数或在配置中设置 api_key"
            )
        self.model = model or (cfg.get('models', ['qwen-plus-latest'])[0] if cfg.get('models') else 'qwen-plus-latest')
        self.temperature = temperature
        self.top_p = top_p
        self.max_tokens = max_tokens
        self.stream = stream
        self.base_url = base_url or cfg.get('api_base_url', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
        self.client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        callback: Optional[Callable[[str], None]] = None,
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> Union[Dict, str]:
        """
        发送聊天完成请求并返回结果 (OpenAI 兼容模式)

        :param messages: 对话历史，格式为 [{"role": "user", "content": "..."}, ...]
        :param callback: 如果是流式输出，每收到一段内容会调用该函数
        :param extra_params: 其他传递给 OpenAI API 的可选参数
        :return: 响应内容（流式时为拼接的完整字符串，非流式时为模型回复的字符串或错误时的字典）
        """
        request_params = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "max_tokens": self.max_tokens,
            "stream": self.stream,
            **(extra_params or {}),
        }

        try:
            if self.stream and callback:
                full_response_content = ""
                response_obj = await self.client.chat.completions.with_raw_response.create(
                    **request_params
                )
                # 检查响应状态码，但不使用 async with
                if response_obj.status_code != 200:
                    error_content = await response_obj.parse()
                    print(
                        f"[OpenAIClient ERROR] API Error Status {response_obj.status_code}: {error_content}"
                    )
                    raise QwenAPIException(
                        error_type="api_error",
                        message=f"API 调用错误: {error_content}",
                        details={"original_error": str(error_content), "request_params": request_params}
                    )

                # 如果状态码是200，则继续处理流式响应
                stream = await self.client.chat.completions.create(**request_params) # 重新创建流
                async for chunk in stream:
                    if chunk.choices:
                        content = chunk.choices[0].delta.content
                        if content:
                            callback(content)
                            full_response_content += content
                return full_response_content
            else:
                completion = await self.client.chat.completions.create(**request_params)
                if completion.choices:
                    return completion.choices[0].message.content or ""
                return ""
        except QwenAPIException:
            # 直接重新抛出已经格式化的 QwenAPIException
            raise
        except Exception as e:
            error_details = {
                "original_error": str(e),
                "traceback": traceback.format_exc(),
                "request_params": self._sanitize_params(request_params),
            }
            
            error_str = str(e).lower()
            error_class = e.__class__.__name__
            
            # 根据错误信息或类名分类异常
            if "api" in error_str or "api" in error_class:
                error_type = "api_error"
                user_message = f"API 调用错误: {e}"
            elif "connect" in error_str or "network" in error_str or "timeout" in error_str:
                error_type = "connection_error"
                user_message = "连接服务器失败，请检查网络连接"
            elif "rate" in error_str or "limit" in error_str or "quota" in error_str:
                error_type = "rate_limit_error"
                user_message = "API 调用频率超限，请稍后再试"
            elif "auth" in error_str or "key" in error_str or "token" in error_str or "permission" in error_str:
                error_type = "auth_error"
                user_message = "API 密钥无效或已过期，请检查您的 API 密钥"
            else:
                error_type = "unknown_error"
                user_message = f"未知错误: {e}"
            
            print(f"[OpenAIClient ERROR] {error_type}: {e}")
            print(traceback.format_exc())
            
            raise QwenAPIException(
                error_type=error_type,
                message=user_message,
                details=error_details,
            )

    def _sanitize_params(self, params: Dict) -> Dict:
        """
        清理请求参数，移除敏感信息

        :param params: 原始请求参数
        :return: 清理后的参数
        """
        sanitized = params.copy()
        # 移除或遮盖敏感信息
        if "api_key" in sanitized:
            sanitized["api_key"] = "***"
        return sanitized

    @staticmethod
    def format_messages(*contents: str) -> List[Dict[str, str]]:
        """
        快速构建对话历史（交替 user/assistant）

        :param contents: 内容列表，奇数为用户消息，偶数为助手消息
        :return: messages 列表
        """
        messages = []
        for i, content in enumerate(contents):
            role = "user" if i % 2 == 0 else "assistant"
            messages.append({"role": role, "content": content})
        return messages

    @staticmethod
    def format_error_message(error: Exception) -> Tuple[str, Dict]:
        """
        格式化错误信息，用于显示给用户

        :param error: 异常对象
        :return: 元组 (用户友好的错误消息, 详细错误信息字典)
        """
        if isinstance(error, QwenAPIException):
            user_message = error.message
            details = error.to_dict()
        else:
            user_message = f"发生错误: {str(error)}"
            details = {
                "error_type": "unknown_error",
                "message": str(error),
                "traceback": traceback.format_exc(),
            }

        return user_message, details
