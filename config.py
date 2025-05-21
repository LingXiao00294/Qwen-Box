# config.py

import os
import json
from dotenv import load_dotenv

# 加载.env文件中的环境变量
load_dotenv()

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'user_config.json')

# 默认配置
DEFAULT_CONFIG = {
    'name': '默认配置',
    'api_key': os.getenv('OPENAI_API_KEY', ''),
    'api_base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    'models': ['qwen-plus-latest'],
}

def get_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def set_config(cfg: dict):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

# 兼容旧用法
OPENAI_API_KEY = get_config().get('api_key', '')
API_BASE_URL = get_config().get('api_base_url', DEFAULT_CONFIG['api_base_url'])
MODEL_NAME = get_config().get('models', DEFAULT_CONFIG['models'])[0] if get_config().get('models') else DEFAULT_CONFIG['models'][0]
HISTORY_DIR = 'chat_history' 