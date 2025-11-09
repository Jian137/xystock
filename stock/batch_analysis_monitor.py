"""
批量分析进度监控和错误处理模块
提供实时进度监控、错误处理和结果通知功能
"""

import os
import sys
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from queue import Queue
import traceback

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)


@dataclass
class ProgressUpdate:
    """进度更新信息"""
    timestamp: str
    stock_code: str
    stock_name: str
    status: str  # 'started', 'completed', 'failed', 'progress'
    message: str
    progress_percent: float = 0.0
    error_details: Optional[str] = None


@dataclass
class AnalysisStats:
    """分析统计信息"""
    total_stocks: int
    completed_stocks: int
    failed_stocks: int
    current_stock: str
    start_time: str
    elapsed_time: float
    estimated_remaining: float
    success_rate: float


class BatchAnalysisMonitor:
    """批量分析监控器"""
    
    def __init__(self, total_stocks: int, callback: Optional[Callable] = None):
        """
        初始化监控器
        
        Args:
            total_stocks: 总股票数量
            callback: 进度更新回调函数
        """
        self.total_stocks = total_stocks
        self.callback = callback
        self.start_time = datetime.now()
        self.completed_stocks = 0
        self.failed_stocks = 0
        self.current_stock = ""
        self.progress_queue = Queue()
        self.stats_lock = threading.Lock()
        self.is_running = False
        
        # 统计信息
        self.stock_times = {}  # 每只股票的分析时间
        self.error_log = []    # 错误日志
        
    def start_monitoring(self):
        """开始监控"""
        self.is_running = True
        self.start_time = datetime.now()
        self._send_update("monitor", "监控开始", "监控器已启动")
    
    def stop_monitoring(self):
        """停止监控"""
        self.is_running = False
        self._send_update("monitor", "监控结束", "监控器已停止")
    
    def update_stock_start(self, stock_code: str, stock_name: str = ""):
        """更新股票开始分析"""
        with self.stats_lock:
            self.current_stock = stock_code
            self.stock_times[stock_code] = {
                'start_time': datetime.now(),
                'stock_name': stock_name
            }
        
        self._send_update(stock_code, "开始分析", f"开始分析 {stock_code} ({stock_name})")
    
    def update_stock_progress(self, stock_code: str, progress_percent: float, message: str = ""):
        """更新股票分析进度"""
        self._send_update(stock_code, "分析中", message, progress_percent)
    
    def update_stock_complete(self, stock_code: str, success: bool = True, error_message: str = ""):
        """更新股票分析完成"""
        with self.stats_lock:
            if stock_code in self.stock_times:
                end_time = datetime.now()
                start_time = self.stock_times[stock_code]['start_time']
                duration = (end_time - start_time).total_seconds()
                self.stock_times[stock_code]['duration'] = duration
                self.stock_times[stock_code]['end_time'] = end_time
            
            if success:
                self.completed_stocks += 1
                status = "分析完成"
                message = f"{stock_code} 分析成功"
            else:
                self.failed_stocks += 1
                status = "分析失败"
                message = f"{stock_code} 分析失败: {error_message}"
                self.error_log.append({
                    'stock_code': stock_code,
                    'error': error_message,
                    'timestamp': datetime.now().isoformat()
                })
        
        self._send_update(stock_code, status, message)
    
    def _send_update(self, stock_code: str, status: str, message: str, progress_percent: float = 0.0):
        """发送进度更新"""
        update = ProgressUpdate(
            timestamp=datetime.now().isoformat(),
            stock_code=stock_code,
            stock_name=self.stock_times.get(stock_code, {}).get('stock_name', ''),
            status=status,
            message=message,
            progress_percent=progress_percent
        )
        
        self.progress_queue.put(update)
        
        if self.callback:
            try:
                self.callback(update)
            except Exception as e:
                print(f"❌ 回调函数执行失败: {e}")
    
    def get_current_stats(self) -> AnalysisStats:
        """获取当前统计信息"""
        with self.stats_lock:
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
            
            # 计算预估剩余时间
            if self.completed_stocks > 0:
                avg_time_per_stock = elapsed_time / self.completed_stocks
                remaining_stocks = self.total_stocks - self.completed_stocks - self.failed_stocks
                estimated_remaining = avg_time_per_stock * remaining_stocks
            else:
                estimated_remaining = 0
            
            success_rate = (self.completed_stocks / (self.completed_stocks + self.failed_stocks) * 100) if (self.completed_stocks + self.failed_stocks) > 0 else 0
            
            return AnalysisStats(
                total_stocks=self.total_stocks,
                completed_stocks=self.completed_stocks,
                failed_stocks=self.failed_stocks,
                current_stock=self.current_stock,
                start_time=self.start_time.isoformat(),
                elapsed_time=elapsed_time,
                estimated_remaining=estimated_remaining,
                success_rate=success_rate
            )
    
    def get_progress_updates(self, max_updates: int = 100) -> List[ProgressUpdate]:
        """获取进度更新列表"""
        updates = []
        count = 0
        
        while not self.progress_queue.empty() and count < max_updates:
            try:
                update = self.progress_queue.get_nowait()
                updates.append(update)
                count += 1
            except:
                break
        
        return updates
    
    def get_error_summary(self) -> Dict[str, Any]:
        """获取错误摘要"""
        with self.stats_lock:
            error_summary = {
                'total_errors': len(self.error_log),
                'error_by_stock': {},
                'common_errors': {},
                'recent_errors': self.error_log[-10:] if self.error_log else []
            }
            
            # 按股票统计错误
            for error in self.error_log:
                stock_code = error['stock_code']
                if stock_code not in error_summary['error_by_stock']:
                    error_summary['error_by_stock'][stock_code] = 0
                error_summary['error_by_stock'][stock_code] += 1
            
            # 统计常见错误
            error_messages = [error['error'] for error in self.error_log]
            for error_msg in error_messages:
                if error_msg not in error_summary['common_errors']:
                    error_summary['common_errors'][error_msg] = 0
                error_summary['common_errors'][error_msg] += 1
            
            return error_summary
    
    def save_monitor_log(self, filepath: str):
        """保存监控日志"""
        log_data = {
            'monitor_info': {
                'total_stocks': self.total_stocks,
                'start_time': self.start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration': (datetime.now() - self.start_time).total_seconds()
            },
            'final_stats': asdict(self.get_current_stats()),
            'error_summary': self.get_error_summary(),
            'stock_times': self.stock_times,
            'progress_updates': [asdict(update) for update in self.get_progress_updates(1000)]
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            print(f"📋 监控日志已保存: {filepath}")
        except Exception as e:
            print(f"❌ 保存监控日志失败: {e}")


class ErrorHandler:
    """错误处理器"""
    
    def __init__(self, monitor: Optional[BatchAnalysisMonitor] = None):
        """
        初始化错误处理器
        
        Args:
            monitor: 监控器实例
        """
        self.monitor = monitor
        self.retry_strategies = {
            'network_error': self._handle_network_error,
            'data_error': self._handle_data_error,
            'ai_error': self._handle_ai_error,
            'timeout_error': self._handle_timeout_error,
            'unknown_error': self._handle_unknown_error
        }
    
    def handle_error(self, stock_code: str, error: Exception, context: str = "") -> Dict[str, Any]:
        """
        处理错误
        
        Args:
            stock_code: 股票代码
            error: 异常对象
            context: 错误上下文
            
        Returns:
            处理结果字典
        """
        error_type = self._classify_error(error)
        error_message = str(error)
        
        print(f"❌ {stock_code} 发生错误: {error_type} - {error_message}")
        
        # 记录错误到监控器
        if self.monitor:
            self.monitor.update_stock_complete(stock_code, success=False, error_message=error_message)
        
        # 根据错误类型选择处理策略
        if error_type in self.retry_strategies:
            return self.retry_strategies[error_type](stock_code, error, context)
        else:
            return self.retry_strategies['unknown_error'](stock_code, error, context)
    
    def _classify_error(self, error: Exception) -> str:
        """分类错误类型"""
        error_str = str(error).lower()
        
        if any(keyword in error_str for keyword in ['network', 'connection', 'timeout', 'http']):
            return 'network_error'
        elif any(keyword in error_str for keyword in ['data', 'parse', 'format', 'empty']):
            return 'data_error'
        elif any(keyword in error_str for keyword in ['ai', 'llm', 'openai', 'model']):
            return 'ai_error'
        elif 'timeout' in error_str:
            return 'timeout_error'
        else:
            return 'unknown_error'
    
    def _handle_network_error(self, stock_code: str, error: Exception, context: str) -> Dict[str, Any]:
        """处理网络错误"""
        return {
            'should_retry': True,
            'retry_delay': 5,  # 5秒后重试
            'max_retries': 3,
            'error_type': 'network_error',
            'suggestion': '网络连接问题，建议稍后重试'
        }
    
    def _handle_data_error(self, stock_code: str, error: Exception, context: str) -> Dict[str, Any]:
        """处理数据错误"""
        return {
            'should_retry': False,
            'error_type': 'data_error',
            'suggestion': '数据格式或内容问题，可能需要检查数据源'
        }
    
    def _handle_ai_error(self, stock_code: str, error: Exception, context: str) -> Dict[str, Any]:
        """处理AI分析错误"""
        return {
            'should_retry': True,
            'retry_delay': 10,  # 10秒后重试
            'max_retries': 2,
            'error_type': 'ai_error',
            'suggestion': 'AI服务暂时不可用，建议稍后重试'
        }
    
    def _handle_timeout_error(self, stock_code: str, error: Exception, context: str) -> Dict[str, Any]:
        """处理超时错误"""
        return {
            'should_retry': True,
            'retry_delay': 3,  # 3秒后重试
            'max_retries': 2,
            'error_type': 'timeout_error',
            'suggestion': '请求超时，建议稍后重试'
        }
    
    def _handle_unknown_error(self, stock_code: str, error: Exception, context: str) -> Dict[str, Any]:
        """处理未知错误"""
        return {
            'should_retry': False,
            'error_type': 'unknown_error',
            'suggestion': '未知错误，请检查日志或联系技术支持'
        }


class ProgressReporter:
    """进度报告器"""
    
    def __init__(self, monitor: BatchAnalysisMonitor):
        """
        初始化进度报告器
        
        Args:
            monitor: 监控器实例
        """
        self.monitor = monitor
        self.last_report_time = datetime.now()
        self.report_interval = 30  # 30秒报告一次
    
    def should_report(self) -> bool:
        """判断是否应该报告进度"""
        now = datetime.now()
        return (now - self.last_report_time).total_seconds() >= self.report_interval
    
    def report_progress(self):
        """报告当前进度"""
        if not self.should_report():
            return
        
        stats = self.monitor.get_current_stats()
        
        print(f"\n📊 批量分析进度报告:")
        print(f"   总股票数: {stats.total_stocks}")
        print(f"   已完成: {stats.completed_stocks}")
        print(f"   失败: {stats.failed_stocks}")
        print(f"   当前分析: {stats.current_stock}")
        print(f"   成功率: {stats.success_rate:.1f}%")
        print(f"   已用时间: {stats.elapsed_time:.1f}秒")
        print(f"   预估剩余: {stats.estimated_remaining:.1f}秒")
        
        # 显示错误摘要
        error_summary = self.monitor.get_error_summary()
        if error_summary['total_errors'] > 0:
            print(f"   错误数量: {error_summary['total_errors']}")
            if error_summary['recent_errors']:
                recent_error = error_summary['recent_errors'][-1]
                print(f"   最近错误: {recent_error['stock_code']} - {recent_error['error']}")
        
        self.last_report_time = datetime.now()


# 便捷函数
def create_monitor(total_stocks: int, callback: Optional[Callable] = None) -> BatchAnalysisMonitor:
    """创建监控器"""
    return BatchAnalysisMonitor(total_stocks, callback)


def create_error_handler(monitor: Optional[BatchAnalysisMonitor] = None) -> ErrorHandler:
    """创建错误处理器"""
    return ErrorHandler(monitor)


def create_progress_reporter(monitor: BatchAnalysisMonitor) -> ProgressReporter:
    """创建进度报告器"""
    return ProgressReporter(monitor)


if __name__ == "__main__":
    # 测试监控器
    def test_callback(update: ProgressUpdate):
        print(f"[{update.timestamp}] {update.stock_code}: {update.message}")
    
    monitor = create_monitor(5, test_callback)
    monitor.start_monitoring()
    
    # 模拟分析过程
    stocks = ["000001", "600519", "300750", "601318", "002594"]
    
    for stock in stocks:
        monitor.update_stock_start(stock, f"股票{stock}")
        time.sleep(1)  # 模拟分析时间
        monitor.update_stock_complete(stock, success=True)
    
    monitor.stop_monitoring()
    
    # 显示最终统计
    stats = monitor.get_current_stats()
    print(f"\n最终统计: {stats}")
    
    # 保存日志
    monitor.save_monitor_log("./test_monitor_log.json")
