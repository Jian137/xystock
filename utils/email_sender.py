"""
邮件发送模块
用于发送股票分析报告到指定邮箱
"""

import os
import json
import html
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict
from datetime import datetime
import traceback


class EmailSender:
    """邮件发送器"""
    
    def __init__(self, smtp_server: str, smtp_port: int, 
                 sender_email: str, sender_password: str,
                 use_tls: bool = True, use_ssl: bool = False,
                 timeout: int = 30):
        """
        初始化邮件发送器
        
        Args:
            smtp_server: SMTP服务器地址
            smtp_port: SMTP端口
            sender_email: 发送者邮箱
            sender_password: 发送者邮箱密码或授权码
            use_tls: 是否使用TLS加密（STARTTLS，用于端口587）
            use_ssl: 是否使用SSL加密（用于端口465）
            timeout: 连接超时时间（秒）
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.timeout = timeout
    
    def send_email(self, 
                   recipient_emails: List[str],
                   subject: str,
                   body: str,
                   attachments: Optional[List[tuple]] = None,
                   is_html: bool = False) -> bool:
        """
        发送邮件
        
        Args:
            recipient_emails: 收件人邮箱列表
            subject: 邮件主题
            body: 邮件正文
            attachments: 附件列表，格式为 [(文件路径, 文件名), ...]
            is_html: 正文是否为HTML格式
        
        Returns:
            是否发送成功
        """
        try:
            # 创建邮件对象
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = ', '.join(recipient_emails)
            msg['Subject'] = subject
            
            # 添加正文
            if is_html:
                msg.attach(MIMEText(body, 'html', 'utf-8'))
            else:
                msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # 添加附件
            if attachments:
                for file_path, filename in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename= {filename}'
                            )
                            msg.attach(part)
            
            # 连接SMTP服务器并发送
            # 根据配置选择使用 SSL 或 TLS
            if self.use_ssl:
                # 使用 SSL 连接（通常用于端口 465）
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port, timeout=self.timeout)
            else:
                # 使用普通连接，然后可能需要 STARTTLS（通常用于端口 587）
                server = smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=self.timeout)
                # 设置调试级别（可选，用于排查问题）
                # server.set_debuglevel(1)
                if self.use_tls:
                    server.starttls()
            
            # 登录
            server.login(self.sender_email, self.sender_password)
            
            # 发送邮件
            server.send_message(msg)
            
            # 关闭连接
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"❌ 邮件发送失败: {e}")
            traceback.print_exc()
            return False
    
    def _load_analysis_data(self, analysis_result_dir: str) -> Optional[Dict]:
        """加载分析结果数据"""
        try:
            # 查找详细汇总文件
            if not os.path.exists(analysis_result_dir):
                return None
            
            files = os.listdir(analysis_result_dir)
            detailed_file = None
            
            for file in files:
                if file.startswith("batch_analysis_detailed_") and file.endswith(".json"):
                    detailed_file = file
                    break
            
            if not detailed_file:
                return None
            
            # 读取详细数据
            detailed_path = os.path.join(analysis_result_dir, detailed_file)
            with open(detailed_path, 'r', encoding='utf-8') as f:
                detailed_data = json.load(f)
            
            return detailed_data
        except Exception as e:
            print(f"⚠️  加载分析数据失败: {e}")
            return None
    
    def _convert_analysis_to_html(self, analysis_data: Dict, summary_text: str = None) -> str:
        """将分析结果转换为HTML格式"""
        try:
            batch_info = analysis_data.get('batch_info', {})
            results = analysis_data.get('results', [])
            
            # HTML头部样式
            html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #3498db;
            padding-left: 15px;
        }
        h3 {
            color: #555;
            margin-top: 20px;
        }
        .summary-box {
            background-color: #ecf0f1;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }
        .stock-card {
            background-color: #f8f9fa;
            border-left: 4px solid #3498db;
            padding: 20px;
            margin: 20px 0;
            border-radius: 5px;
        }
        .stock-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .stock-title {
            font-size: 1.3em;
            font-weight: bold;
            color: #2c3e50;
        }
        .stock-status {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.9em;
        }
        .status-success {
            background-color: #d4edda;
            color: #155724;
        }
        .status-failed {
            background-color: #f8d7da;
            color: #721c24;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #3498db;
            color: white;
            font-weight: bold;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .metric {
            display: inline-block;
            margin: 10px 15px 10px 0;
            padding: 8px 15px;
            background-color: #e8f4f8;
            border-radius: 5px;
        }
        .metric-label {
            font-size: 0.9em;
            color: #666;
        }
        .metric-value {
            font-size: 1.2em;
            font-weight: bold;
            color: #2c3e50;
        }
        .ai-analysis {
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
            border-radius: 5px;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 0.9em;
            text-align: center;
        }
    </style>
</head>
<body>
    <div class="container">
"""
            
            # 标题
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            html_content += f"<h1>📊 XY Stock 股票分析报告</h1>"
            html_content += f"<p><strong>分析时间:</strong> {timestamp}</p>"
            
            # 摘要信息
            if summary_text:
                summary_text_escaped = html.escape(summary_text)
                html_content += f'<div class="summary-box"><pre style="white-space: pre-wrap; margin: 0;">{summary_text_escaped}</pre></div>'
            
            # 批次统计
            if batch_info:
                html_content += "<h2>📈 分析统计</h2>"
                html_content += '<div class="summary-box">'
                html_content += f'<div class="metric"><span class="metric-label">成功数量</span><br><span class="metric-value">{batch_info.get("success_count", 0)}</span></div>'
                html_content += f'<div class="metric"><span class="metric-label">失败数量</span><br><span class="metric-value">{batch_info.get("failed_count", 0)}</span></div>'
                html_content += f'<div class="metric"><span class="metric-label">总耗时</span><br><span class="metric-value">{batch_info.get("total_duration", 0):.2f}秒</span></div>'
                html_content += '</div>'
            
            # 详细分析结果
            if results:
                html_content += "<h2>📄 详细分析结果</h2>"
                
                for i, result in enumerate(results, 1):
                    stock_code = result.get('stock_code', 'N/A')
                    stock_name = result.get('stock_name', 'N/A')
                    status = result.get('status', 'unknown')
                    summary = result.get('summary', {})
                    analysis_data = result.get('analysis_data', {})
                    
                    # 股票卡片
                    status_class = 'status-success' if status == 'success' else 'status-failed'
                    html_content += f'<div class="stock-card">'
                    html_content += f'<div class="stock-header">'
                    html_content += f'<div class="stock-title">{i}. {stock_name} ({stock_code})</div>'
                    html_content += f'<span class="stock-status {status_class}">{status}</span>'
                    html_content += '</div>'
                    
                    # 摘要信息
                    if summary:
                        html_content += '<table>'
                        html_content += '<tr><th>指标</th><th>数值</th></tr>'
                        
                        summary_fields = [
                            ('当前价格', 'current_price', lambda x: f"{x:.2f}" if isinstance(x, (int, float)) else str(x)),
                            ('涨跌幅', 'change_percent', lambda x: f"{x:.2f}%" if isinstance(x, (int, float)) else str(x)),
                            ('技术趋势', 'technical_trend', str),
                            ('RSI水平', 'rsi_level', str),
                            ('新闻数量', 'news_count', str),
                            ('盈利比例', 'profit_ratio', lambda x: f"{x}%" if isinstance(x, (int, float)) else str(x)),
                            ('分析完成数', 'analysis_count', str),
                            ('包含AI分析', 'has_ai_analysis', lambda x: '是' if x else '否'),
                            ('行业', 'industry', str),
                        ]
                        
                        for label, key, formatter in summary_fields:
                            value = summary.get(key, 'N/A')
                            if value != 'N/A' and value is not None:
                                try:
                                    display_value = formatter(value)
                                    html_content += f'<tr><td><strong>{label}</strong></td><td>{display_value}</td></tr>'
                                except:
                                    html_content += f'<tr><td><strong>{label}</strong></td><td>{value}</td></tr>'
                        
                        html_content += '</table>'
                    
                    # AI分析结果 - 检查所有类型的AI分析
                    ai_analyses = []
                    
                    # 1. 综合分析 (可能有多个字段名)
                    comprehensive_ai = analysis_data.get('comprehensive_ai') or analysis_data.get('comprehensive_analysis')
                    if comprehensive_ai:
                        ai_text = comprehensive_ai.get('analysis_result') or comprehensive_ai.get('report')
                        if ai_text:
                            ai_analyses.append(('🤖 AI综合分析', ai_text))
                    
                    # 2. 基本面分析
                    if 'fundamental_ai' in analysis_data:
                        ai_result = analysis_data['fundamental_ai']
                        ai_text = ai_result.get('analysis_result') or ai_result.get('report')
                        if ai_text:
                            ai_analyses.append(('📊 AI基本面分析', ai_text))
                    
                    # 3. 公司分析
                    if 'company_ai' in analysis_data:
                        ai_result = analysis_data['company_ai']
                        ai_text = ai_result.get('analysis_result') or ai_result.get('report')
                        if ai_text:
                            ai_analyses.append(('🏢 AI公司分析', ai_text))
                    
                    # 4. 技术分析
                    if 'technical_ai' in analysis_data:
                        ai_result = analysis_data['technical_ai']
                        ai_text = ai_result.get('analysis_result') or ai_result.get('report')
                        if ai_text:
                            ai_analyses.append(('📈 AI技术分析', ai_text))
                    
                    # 5. 新闻分析 (可能在news_analysis中)
                    news_info = analysis_data.get('news_analysis', {})
                    if news_info and news_info.get('ai_analysis'):
                        ai_result = news_info['ai_analysis']
                        ai_text = ai_result.get('report') or ai_result.get('analysis_result')
                        if ai_text:
                            ai_analyses.append(('📰 AI新闻分析', ai_text))
                    
                    # 6. 筹码分析
                    if 'chip_ai' in analysis_data:
                        ai_result = analysis_data['chip_ai']
                        ai_text = ai_result.get('analysis_result') or ai_result.get('report')
                        if ai_text:
                            ai_analyses.append(('🎯 AI筹码分析', ai_text))
                    
                    # 显示所有AI分析结果
                    if ai_analyses:
                        for ai_title, ai_text in ai_analyses:
                            html_content += '<div class="ai-analysis">'
                            html_content += f'<h3>{ai_title}</h3>'
                            # 限制长度，避免邮件过大
                            if len(ai_text) > 2000:
                                ai_text = ai_text[:2000] + "...\n\n(内容已截断，完整内容请查看详细报告)"
                            # 转义HTML特殊字符
                            ai_text_escaped = html.escape(ai_text)
                            html_content += f'<pre style="white-space: pre-wrap; margin: 0;">{ai_text_escaped}</pre>'
                            html_content += '</div>'
                    
                    # 错误信息
                    if status == 'failed':
                        error_msg = result.get('error_message', '未知错误')
                        error_msg_escaped = html.escape(str(error_msg))
                        html_content += f'<p style="color: #d32f2f;"><strong>错误信息:</strong> {error_msg_escaped}</p>'
                    
                    html_content += '</div>'
            
            # 页脚
            html_content += """
        <div class="footer">
            <p>此邮件由 XY Stock 系统自动发送</p>
            <p>报告生成时间: """ + timestamp + """</p>
        </div>
    </div>
</body>
</html>
"""
            return html_content
        except Exception as e:
            print(f"⚠️  转换分析结果为HTML失败: {e}")
            traceback.print_exc()
            # 返回简单的文本格式
            return f"<html><body><h1>XY Stock 股票分析报告</h1><p>分析结果转换失败: {str(e)}</p></body></html>"
    
    def send_analysis_report(self,
                            recipient_emails: List[str],
                            analysis_result_dir: str,
                            report_files: Optional[List[str]] = None,
                            summary_text: Optional[str] = None) -> bool:
        """
        发送分析报告邮件（不包含附件，内容直接嵌入邮件正文）
        
        Args:
            recipient_emails: 收件人邮箱列表
            analysis_result_dir: 分析结果目录
            report_files: 报告文件列表（已废弃，不再使用）
            summary_text: 邮件正文摘要文本
        
        Returns:
            是否发送成功
        """
        # 生成邮件主题
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        subject = f"XY Stock 股票分析报告 - {timestamp}"
        
        # 加载分析数据并转换为HTML
        analysis_data = self._load_analysis_data(analysis_result_dir)
        
        if analysis_data:
            # 转换为HTML格式
            html_body = self._convert_analysis_to_html(analysis_data, summary_text)
        else:
            # 如果没有分析数据，使用简单的文本格式
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }}
        h1 {{ color: #2c3e50; }}
    </style>
</head>
<body>
    <h1>📊 XY Stock 股票分析报告</h1>
    <p><strong>分析时间:</strong> {timestamp}</p>
    <p><strong>结果目录:</strong> {analysis_result_dir}</p>
    <pre>{summary_text or '未找到分析数据'}</pre>
    <hr>
    <p style="color: #666; font-size: 0.9em;">此邮件由 XY Stock 系统自动发送</p>
</body>
</html>
"""
        
        # 发送邮件（不包含附件）
        return self.send_email(
            recipient_emails=recipient_emails,
            subject=subject,
            body=html_body,
            attachments=None,  # 不添加附件
            is_html=True  # 使用HTML格式
        )


def create_email_sender_from_config(config_manager=None) -> Optional[EmailSender]:
    """
    从配置文件创建邮件发送器
    
    Args:
        config_manager: 配置管理器实例
    
    Returns:
        EmailSender实例，如果配置不完整则返回None
    """
    try:
        if config_manager is None:
            from config_manager import ConfigManager
            config_manager = ConfigManager()
        
        # 读取邮件配置
        email_config = config_manager.get_section('EMAIL')
        
        if not email_config:
            print("⚠️  未找到邮件配置，邮件功能将不可用")
            return None
        
        # 检查必需的配置项
        required_keys = ['SMTP_SERVER', 'SMTP_PORT', 'SENDER_EMAIL', 'SENDER_PASSWORD']
        missing_keys = [key for key in required_keys if key not in email_config]
        
        if missing_keys:
            print(f"⚠️  邮件配置不完整，缺少: {', '.join(missing_keys)}")
            return None
        
        # 创建邮件发送器
        # 根据端口自动判断使用 SSL 还是 TLS
        smtp_port = int(email_config['SMTP_PORT'])
        use_ssl = email_config.get('USE_SSL', False)
        # 如果端口是 465，默认使用 SSL
        if smtp_port == 465 and 'USE_SSL' not in email_config:
            use_ssl = True
            use_tls = False
        else:
            use_tls = email_config.get('USE_TLS', True)
        
        sender = EmailSender(
            smtp_server=email_config['SMTP_SERVER'],
            smtp_port=smtp_port,
            sender_email=email_config['SENDER_EMAIL'],
            sender_password=email_config['SENDER_PASSWORD'],
            use_tls=use_tls,
            use_ssl=use_ssl,
            timeout=email_config.get('TIMEOUT', 30)
        )
        
        print("✅ 邮件发送器初始化成功")
        return sender
        
    except Exception as e:
        print(f"❌ 创建邮件发送器失败: {e}")
        return None

