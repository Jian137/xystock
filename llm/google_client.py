"""
Google Gemini API 增强封装
包含 token 使用记录、配置管理、错误处理等功能
"""
import time
import logging
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

try:
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
    GOOGLE_AI_AVAILABLE = True
except ImportError:
    GOOGLE_AI_AVAILABLE = False
    genai = None
    google_exceptions = None

# 添加项目根目录到路径，以便导入配置管理器
sys.path.append(str(Path(__file__).parent.parent))
from config_manager import config
from .usage_logger import UsageLogger

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.get('LLM_LOGGING.LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GoogleClient:
    """增强的 Google Gemini API 客户端"""
    
    def __init__(self, api_key: Optional[str] = None, usage_logger: Optional[UsageLogger] = None):
        """
        初始化 Google Gemini 客户端
        
        Args:
            api_key: API 密钥，如果为空则从配置文件读取
            usage_logger: 使用记录器，如果为空则自动创建
        """
        if not GOOGLE_AI_AVAILABLE:
            raise ImportError(
                "Google Generative AI 库未安装。请运行: pip install google-generativeai"
            )
        
        # 从配置获取API密钥
        self.api_key = api_key or config.get('LLM_GOOGLE.API_KEY')
        if not self.api_key:
            raise ValueError("API密钥未设置，请在配置文件中设置 LLM_GOOGLE.API_KEY")
        
        # 配置 Google AI
        genai.configure(api_key=self.api_key)
        
        # 获取其他配置
        google_config = config.get_google_config()
        timeout = google_config.get('TIMEOUT', 60)
        max_retries = google_config.get('MAX_RETRIES', 3)
        
        self.timeout = timeout
        self.max_retries = max_retries
        
        # 初始化使用记录器
        if config.get('LLM_LOGGING.ENABLE_LOGGING', True):
            log_file = config.get('LLM_LOGGING.USAGE_LOG_FILE', 'data/logs/google_usage.csv')
            if not Path(log_file).is_absolute():
                project_root = Path(__file__).parent.parent
                log_file = project_root / log_file
            self.usage_logger = usage_logger or UsageLogger(str(log_file))
        else:
            self.usage_logger = None
        
        # 默认参数
        self.default_model = google_config.get('DEFAULT_MODEL', 'gemini-pro')
        self.inference_model = google_config.get('INFERENCE_MODEL', 'gemini-pro')
        self.default_temperature = google_config.get('DEFAULT_TEMPERATURE', 0.7)
        
        logger.info("Google Gemini 客户端初始化完成")
    
    def _convert_messages_to_google_format(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        将 OpenAI 格式的消息转换为 Google Gemini 格式
        
        Args:
            messages: OpenAI 格式的消息列表
            
        Returns:
            Google Gemini 格式的消息列表
        """
        google_messages = []
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            
            # Google Gemini 使用 'user' 和 'model' 角色
            # 将 'system' 和 'assistant' 转换为合适的格式
            if role == 'system':
                # 系统消息通常作为第一个用户消息的一部分
                if google_messages and google_messages[0].get('role') == 'user':
                    google_messages[0]['parts'] = [f"System: {content}\n\n{google_messages[0].get('parts', [''])[0]}"]
                else:
                    google_messages.append({
                        'role': 'user',
                        'parts': [f"System: {content}"]
                    })
            elif role == 'assistant':
                google_messages.append({
                    'role': 'model',
                    'parts': [content]
                })
            elif role == 'user':
                google_messages.append({
                    'role': 'user',
                    'parts': [content]
                })
        
        return google_messages
    
    def _convert_google_messages_to_openai_format(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        将 Google Gemini 格式的消息转换为 OpenAI 格式（用于兼容）
        
        Args:
            messages: Google Gemini 格式的消息列表
            
        Returns:
            OpenAI 格式的消息列表
        """
        openai_messages = []
        for msg in messages:
            role = msg.get('role', 'user')
            parts = msg.get('parts', [])
            content = ' '.join(parts) if isinstance(parts, list) else str(parts)
            
            if role == 'model':
                openai_messages.append({'role': 'assistant', 'content': content})
            elif role == 'user':
                openai_messages.append({'role': 'user', 'content': content})
        
        return openai_messages
    
    def ask(self, 
            prompt: str, 
            model: Optional[str] = None, 
            model_type: Optional[str] = "default",
            temperature: Optional[float] = None, 
            max_tokens: Optional[int] = None,
            system_message: Optional[str] = None,
            messages: Optional[List[Dict[str, str]]] = None,
            json_mode: bool = False,
            debug: bool = False) -> str:
        """
        发送聊天请求
        
        Args:
            prompt: 用户输入
            model: 模型名称，会覆盖model_type
            model_type: 模型类型，'default'使用分析模型，'inference'使用推理模型
            temperature: 温度参数
            max_tokens: 最大token数
            system_message: 系统消息
            messages: 完整的消息列表（如果提供，将覆盖prompt和system_message）
            json_mode: 是否强制返回JSON格式
            debug: 是否打印调试信息
            
        Returns:
            AI回复内容
        """
        start_time = time.time()
        
        # 根据model_type选择默认模型
        if model is None:
            if model_type == "inference":
                model = self.inference_model
            else:
                model = self.default_model
        
        # 使用默认温度
        temperature = temperature or self.default_temperature
        
        try:
            # 构建消息列表
            if messages is None:
                messages = []
                if system_message:
                    messages.append({"role": "system", "content": system_message})
                messages.append({"role": "user", "content": prompt})
            
            # 处理系统消息和用户消息
            system_prompt = ""
            user_prompt = prompt
            
            # 提取系统消息
            if messages:
                system_msgs = [msg.get('content', '') for msg in messages if msg.get('role') == 'system']
                if system_msgs:
                    system_prompt = '\n'.join(system_msgs)
                
                # 获取最后一个用户消息作为主要提示
                user_msgs = [msg.get('content', '') for msg in messages if msg.get('role') == 'user']
                if user_msgs:
                    user_prompt = user_msgs[-1]
            
            # 组合提示（如果有系统消息）
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
            else:
                full_prompt = user_prompt
            
            # 如果启用了JSON模式，添加JSON指令
            if json_mode:
                full_prompt = f"You must respond with valid JSON only.\n\n{full_prompt}"
            
            # 获取模型实例
            model_instance = genai.GenerativeModel(model)
            
            # 构建生成配置
            generation_config = {
                'temperature': temperature,
            }
            if max_tokens:
                generation_config['max_output_tokens'] = max_tokens
            
            # 发送请求（带重试逻辑）
            response = None
            retry_count = 0
            max_retries = self.max_retries
            
            while retry_count <= max_retries:
                try:
                    response = model_instance.generate_content(
                        full_prompt,
                        generation_config=generation_config
                    )
                    break  # 成功，退出循环
                except Exception as e:
                    # 检查是否是配额限制错误（429）
                    error_str = str(e)
                    is_quota_error = (
                        '429' in error_str or 
                        'quota' in error_str.lower() or 
                        'ResourceExhausted' in error_str or
                        (google_exceptions and isinstance(e, google_exceptions.ResourceExhausted))
                    )
                    
                    if is_quota_error and retry_count < max_retries:
                        # 尝试从错误信息中提取等待时间
                        import re
                        wait_time_match = re.search(r'Please retry in ([\d.]+)s', error_str)
                        if wait_time_match:
                            wait_time = float(wait_time_match.group(1))
                        else:
                            # 默认等待时间：根据重试次数递增
                            wait_time = 30 + (retry_count * 10)  # 30s, 40s, 50s...
                        
                        retry_count += 1
                        print(f"⚠️  配额限制错误（429），等待 {wait_time:.1f} 秒后重试（{retry_count}/{max_retries}）...")
                        print(f"   提示：免费层限制为每分钟 10 个请求")
                        time.sleep(wait_time)
                        continue
                    else:
                        # 其他错误或达到最大重试次数，抛出异常
                        raise
            
            # 检查响应是否成功
            if response is None:
                raise Exception("所有重试都失败了，无法获取响应")
            
            # 计算响应时间
            response_time = time.time() - start_time
            
            # 获取回复内容
            content = response.text
            
            # 估算 token 使用（Google API 不直接提供 token 计数）
            # 使用简单的字符数估算（1 token ≈ 4 字符）
            input_text = prompt if not messages else str(messages)
            input_chars = len(input_text)
            output_chars = len(content)
            estimated_input_tokens = input_chars // 4
            estimated_output_tokens = output_chars // 4
            estimated_total_tokens = estimated_input_tokens + estimated_output_tokens
            
            # 构建使用数据
            usage_data = {
                'prompt_tokens': estimated_input_tokens,
                'completion_tokens': estimated_output_tokens,
                'total_tokens': estimated_total_tokens
            }
            
            # 记录使用情况
            if self.usage_logger:
                self.usage_logger.log_usage(
                    model=model,
                    usage_data=usage_data,
                    input_text=input_text,
                    output_text=content,
                    response_time=response_time,
                    temperature=temperature,
                    success=True
                )
            
            # 调试输出
            if debug:
                print(f"模型: {model}")
                print(f"输入: {prompt}")
                print(f"输出: {content}")
                print(f"估算Token使用: {usage_data}")
                print(f"响应时间: {response_time:.2f}秒")
            
            logger.info(f"API调用成功，模型: {model}, 估算tokens: {estimated_total_tokens}")
            
            return content
            
        except Exception as e:
            response_time = time.time() - start_time
            error_message = str(e)
            
            # 记录错误
            if self.usage_logger:
                input_text = prompt if not messages else str(messages)
                self.usage_logger.log_usage(
                    model=model,
                    usage_data={},
                    input_text=input_text,
                    output_text="",
                    response_time=response_time,
                    temperature=temperature,
                    success=False,
                    error_message=error_message
                )
            
            logger.error(f"API调用失败: {error_message}")
            raise
    
    def chat(self, 
             messages: List[Dict[str, str]], 
             model: Optional[str] = None,
             model_type: Optional[str] = "default",
             temperature: Optional[float] = None,
             max_tokens: Optional[int] = None,
             json_mode: bool = False,
             debug: bool = False) -> str:
        """
        多轮对话
        
        Args:
            messages: 消息列表
            model: 模型名称
            model_type: 模型类型，'default'使用分析模型，'inference'使用推理模型
            temperature: 温度参数
            max_tokens: 最大token数
            json_mode: 是否强制返回JSON格式
            debug: 是否打印调试信息
            
        Returns:
            AI回复内容
        """
        return self.ask(
            prompt="",  # 这里prompt为空，因为使用messages
            model=model,
            model_type=model_type,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=messages,
            json_mode=json_mode,
            debug=debug
        )
    
    def get_usage_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        获取使用统计
        
        Args:
            days: 统计天数
            
        Returns:
            统计信息
        """
        if self.usage_logger:
            return self.usage_logger.get_usage_stats(days)
        return {}
    
    def export_usage_report(self, output_file: str = "reports/usage_report.html"):
        """
        导出使用报告
        
        Args:
            output_file: 输出文件路径
        """
        if self.usage_logger:
            self.usage_logger.export_usage_report(output_file)


# 示例和测试
if __name__ == "__main__":
    try:
        # 创建客户端
        client = GoogleClient()
        
        # 简单问答 - 使用默认分析模型
        print("=== 默认分析模型测试 ===")
        response = client.ask("用一句话详细评价AAPL股票", debug=True)
        print(f"分析模型回复: {response}")
        
        # 简单问答 - 使用推理模型
        print("=== 推理模型测试 ===")
        response = client.ask("用一句话评价AAPL股票", model_type="inference", debug=True)
        print(f"推理模型回复: {response}")
        
        # 多轮对话测试 - 使用默认分析模型
        print("\n=== 多轮对话测试 ===")
        messages = [
            {"role": "system", "content": "你是一个专业的股票分析师"},
            {"role": "user", "content": "分析一下苹果公司的投资价值"},
            {"role": "assistant", "content": "苹果公司作为科技巨头..."},
            {"role": "user", "content": "那它的主要风险是什么？"}
        ]
        response = client.chat(messages, debug=True)
        print(f"回复: {response}")
        
        # 获取使用统计
        print("\n=== 使用统计 ===")
        stats = client.get_usage_stats()
        if stats:
            print(f"总请求数: {stats.get('total_requests', 0)}")
            print(f"总Token数: {stats.get('total_tokens', 0)}")
            print(f"总成本: ${stats.get('total_cost', 0):.4f}")
        
        # 导出使用报告
        client.export_usage_report()
        print("使用报告已导出")
        
    except Exception as e:
        print(f"测试失败: {e}")

