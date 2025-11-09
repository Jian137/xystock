"""
LLM模块 - 大语言模型相关功能
包含OpenAI客户端、Google Gemini客户端、使用记录等功能
"""

from .openai_client import OpenAIClient
from .usage_logger import UsageLogger

try:
    from .google_client import GoogleClient
    GOOGLE_CLIENT_AVAILABLE = True
except ImportError:
    GoogleClient = None
    GOOGLE_CLIENT_AVAILABLE = False

__all__ = [
    'OpenAIClient',
    'UsageLogger'
]

if GOOGLE_CLIENT_AVAILABLE:
    __all__.append('GoogleClient')

# 版本信息
__version__ = '1.0.0'
__author__ = 'XYStock Team'
__description__ = 'Enhanced LLM clients (OpenAI, Google Gemini) with usage tracking and configuration management'
