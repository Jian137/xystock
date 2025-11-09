"""
批量股票分析模块
提供批量分析多只股票的功能，支持多种分析类型和配置选项
"""

import os
import sys
import time
import json
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
import traceback

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from stock.stock_data_tools import get_stock_tools
from stock.stock_code_map import get_stock_identity
from utils.format_utils import judge_rsi_level
from stock.batch_analysis_monitor import BatchAnalysisMonitor, ErrorHandler, ProgressReporter


@dataclass
class BatchAnalysisConfig:
    """批量分析配置"""
    stock_codes: List[str]
    analysis_types: List[str]  # ['basic', 'technical', 'news', 'chip', 'comprehensive']
    use_cache: bool = True
    force_refresh: bool = False
    include_ai_analysis: bool = True
    max_workers: int = 3
    max_retry: int = 2
    user_opinion: str = ""
    user_position: str = "不确定"
    output_dir: str = "./batch_analysis_results"
    save_individual_reports: bool = True
    save_summary_report: bool = True


@dataclass
class StockAnalysisResult:
    """单只股票分析结果"""
    stock_code: str
    stock_name: str
    status: str  # 'success', 'failed', 'partial'
    error_message: Optional[str] = None
    analysis_data: Optional[Dict] = None
    analysis_time: Optional[str] = None
    summary: Optional[Dict] = None


@dataclass
class BatchAnalysisResult:
    """批量分析结果"""
    config: BatchAnalysisConfig
    results: List[StockAnalysisResult]
    start_time: str
    end_time: str
    total_duration: float
    success_count: int
    failed_count: int
    summary_stats: Dict


class BatchStockAnalyzer:
    """批量股票分析器"""
    
    def __init__(self, enable_monitoring: bool = True):
        """
        初始化批量分析器
        
        Args:
            enable_monitoring: 是否启用监控功能
        """
        self.stock_tools = get_stock_tools()
        self.results = []
        self.enable_monitoring = enable_monitoring
        self.monitor = None
        self.error_handler = None
        self.progress_reporter = None
        
    def analyze_single_stock(self, stock_code: str, config: BatchAnalysisConfig) -> StockAnalysisResult:
        """分析单只股票"""
        start_time = datetime.now()
        stock_name = ""
        analysis_data = {}
        errors = []
        
        # 通知监控器开始分析
        if self.monitor:
            self.monitor.update_stock_start(stock_code, stock_name)
        
        try:
            # 获取股票身份信息
            stock_identity = get_stock_identity(stock_code)
            if not stock_identity:
                error_msg = f"无法获取股票 {stock_code} 的身份信息"
                if self.monitor:
                    self.monitor.update_stock_complete(stock_code, success=False, error_message=error_msg)
                return StockAnalysisResult(
                    stock_code=stock_code,
                    stock_name="未知",
                    status="failed",
                    error_message=error_msg
                )
            
            stock_name = stock_identity.get('name', '')
            print(f"📊 开始分析 {stock_code} ({stock_name})")
            
            # 更新监控器股票名称
            if self.monitor:
                self.monitor.update_stock_start(stock_code, stock_name)
            
            # 根据配置进行不同类型的分析
            analysis_types = config.analysis_types
            total_types = len(analysis_types)
            
            for i, analysis_type in enumerate(analysis_types):
                # 更新进度
                if self.monitor:
                    progress = (i / total_types) * 100
                    self.monitor.update_stock_progress(stock_code, progress, f"正在执行{analysis_type}分析")
                
                if analysis_type == 'basic':
                    try:
                        basic_data = self.stock_tools.get_basic_info(
                            stock_identity, 
                            use_cache=config.use_cache,
                            force_refresh=config.force_refresh,
                            include_ai_analysis=config.include_ai_analysis
                        )
                        analysis_data['basic_info'] = basic_data
                    except Exception as e:
                        error_msg = f"基本面分析失败: {str(e)}"
                        errors.append(error_msg)
                        print(f"❌ {stock_code} {error_msg}")
                        
                        # 使用错误处理器
                        if self.error_handler:
                            self.error_handler.handle_error(stock_code, e, "基本面分析")
            
                elif analysis_type == 'technical':
                    try:
                        kline_data = self.stock_tools.get_stock_kline_data(
                            stock_identity,
                            use_cache=config.use_cache,
                            force_refresh=config.force_refresh,
                            include_ai_analysis=config.include_ai_analysis
                        )
                        analysis_data['technical_analysis'] = kline_data
                    except Exception as e:
                        error_msg = f"技术分析失败: {str(e)}"
                        errors.append(error_msg)
                        print(f"❌ {stock_code} {error_msg}")
                        
                        if self.error_handler:
                            self.error_handler.handle_error(stock_code, e, "技术分析")
                
                elif analysis_type == 'news':
                    try:
                        news_data = self.stock_tools.get_stock_news_data(
                            stock_identity,
                            use_cache=config.use_cache,
                            force_refresh=config.force_refresh,
                            include_ai_analysis=config.include_ai_analysis
                        )
                        analysis_data['news_analysis'] = news_data
                    except Exception as e:
                        error_msg = f"新闻分析失败: {str(e)}"
                        errors.append(error_msg)
                        print(f"❌ {stock_code} {error_msg}")
                        
                        if self.error_handler:
                            self.error_handler.handle_error(stock_code, e, "新闻分析")
                
                elif analysis_type == 'chip':
                    try:
                        chip_data = self.stock_tools.get_stock_chip_data(
                            stock_identity,
                            use_cache=config.use_cache,
                            force_refresh=config.force_refresh,
                            include_ai_analysis=config.include_ai_analysis
                        )
                        analysis_data['chip_analysis'] = chip_data
                    except Exception as e:
                        error_msg = f"筹码分析失败: {str(e)}"
                        errors.append(error_msg)
                        print(f"❌ {stock_code} {error_msg}")
                        
                        if self.error_handler:
                            self.error_handler.handle_error(stock_code, e, "筹码分析")
                
                elif analysis_type == 'comprehensive':
                    try:
                        comprehensive_data = self.stock_tools.get_comprehensive_ai_analysis(
                            stock_identity,
                            user_opinion=config.user_opinion,
                            user_position=config.user_position,
                            use_cache=config.use_cache,
                            force_refresh=config.force_refresh
                        )
                        analysis_data['comprehensive_analysis'] = comprehensive_data
                    except Exception as e:
                        error_msg = f"综合分析失败: {str(e)}"
                        errors.append(error_msg)
                        print(f"❌ {stock_code} {error_msg}")
                        
                        if self.error_handler:
                            self.error_handler.handle_error(stock_code, e, "综合分析")
            
            # 生成股票摘要
            summary = self._generate_stock_summary(analysis_data)
            
            # 确定分析状态
            if not errors:
                status = "success"
            elif len(errors) < len(config.analysis_types):
                status = "partial"
            else:
                status = "failed"
            
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            result = StockAnalysisResult(
                stock_code=stock_code,
                stock_name=stock_name,
                status=status,
                error_message="; ".join(errors) if errors else None,
                analysis_data=analysis_data,
                analysis_time=end_time.strftime('%Y-%m-%d %H:%M:%S'),
                summary=summary
            )
            
            # 通知监控器分析完成
            if self.monitor:
                self.monitor.update_stock_complete(stock_code, success=(status != "failed"), 
                                                 error_message=result.error_message)
            
            print(f"✅ {stock_code} ({stock_name}) 分析完成 - 状态: {status}")
            return result
            
        except Exception as e:
            error_msg = f"分析过程中发生未知错误: {str(e)}"
            print(f"❌ {stock_code} {error_msg}")
            traceback.print_exc()
            
            # 使用错误处理器
            if self.error_handler:
                self.error_handler.handle_error(stock_code, e, "未知错误")
            
            # 通知监控器分析失败
            if self.monitor:
                self.monitor.update_stock_complete(stock_code, success=False, error_message=error_msg)
            
            return StockAnalysisResult(
                stock_code=stock_code,
                stock_name=stock_name,
                status="failed",
                error_message=error_msg,
                analysis_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            )
    
    def _generate_stock_summary(self, analysis_data: Dict) -> Dict:
        """生成股票分析摘要"""
        summary = {
            'current_price': 0,
            'change_percent': 0,
            'industry': '',
            'technical_trend': '未知',
            'rsi_level': '中性',
            'news_count': 0,
            'profit_ratio': 0,
            'analysis_count': 0,
            'has_ai_analysis': False
        }
        
        # 基本信息摘要
        if 'basic_info' in analysis_data and analysis_data['basic_info']:
            basic = analysis_data['basic_info']
            if 'error' not in basic:
                summary['current_price'] = basic.get('current_price', 0)
                summary['change_percent'] = basic.get('change_percent', 0)
                summary['industry'] = basic.get('industry', '')
                summary['analysis_count'] += 1
                
                # 检查是否有AI分析
                if 'ai_analysis' in basic and 'error' not in basic.get('ai_analysis', {}):
                    summary['has_ai_analysis'] = True
        
        # 技术分析摘要
        if 'technical_analysis' in analysis_data and analysis_data['technical_analysis']:
            tech = analysis_data['technical_analysis']
            if 'error' not in tech:
                indicators = tech.get('indicators', {})
                summary['technical_trend'] = f"{indicators.get('ma_trend', '未知')} | MACD {indicators.get('macd_trend', '未知')}"
                summary['rsi_level'] = judge_rsi_level(indicators.get('rsi_14', 50))
                summary['analysis_count'] += 1
                
                # 检查是否有AI分析
                if 'ai_analysis' in tech and 'error' not in tech.get('ai_analysis', {}):
                    summary['has_ai_analysis'] = True
        
        # 新闻分析摘要
        if 'news_analysis' in analysis_data and analysis_data['news_analysis']:
            news = analysis_data['news_analysis']
            if 'error' not in news:
                summary['news_count'] = news.get('news_count', 0)
                summary['analysis_count'] += 1
                
                # 检查是否有AI分析
                if 'ai_analysis' in news and 'error' not in news.get('ai_analysis', {}):
                    summary['has_ai_analysis'] = True
        
        # 筹码分析摘要
        if 'chip_analysis' in analysis_data and analysis_data['chip_analysis']:
            chip = analysis_data['chip_analysis']
            if 'error' not in chip:
                summary['profit_ratio'] = chip.get('profit_ratio', 0)
                summary['analysis_count'] += 1
                
                # 检查是否有AI分析
                if 'ai_analysis' in chip and 'error' not in chip.get('ai_analysis', {}):
                    summary['has_ai_analysis'] = True
        
        # 综合分析摘要
        if 'comprehensive_analysis' in analysis_data and analysis_data['comprehensive_analysis']:
            comp = analysis_data['comprehensive_analysis']
            if 'error' not in comp:
                summary['analysis_count'] += 1
                summary['has_ai_analysis'] = True
        
        return summary
    
    def batch_analyze(self, config: BatchAnalysisConfig) -> BatchAnalysisResult:
        """执行批量分析"""
        start_time = datetime.now()
        print(f"\n🚀 开始批量分析 {len(config.stock_codes)} 只股票")
        print(f"📋 分析类型: {', '.join(config.analysis_types)}")
        print(f"🔧 并发数: {config.max_workers}")
        print(f"💾 使用缓存: {config.use_cache}")
        print(f"🤖 AI分析: {config.include_ai_analysis}")
        
        # 创建输出目录
        os.makedirs(config.output_dir, exist_ok=True)
        
        # 初始化监控组件
        if self.enable_monitoring:
            self.monitor = BatchAnalysisMonitor(len(config.stock_codes))
            self.error_handler = ErrorHandler(self.monitor)
            self.progress_reporter = ProgressReporter(self.monitor)
            self.monitor.start_monitoring()
        
        results = []
        success_count = 0
        failed_count = 0
        
        # 使用线程池进行并发分析
        with ThreadPoolExecutor(max_workers=config.max_workers) as executor:
            # 提交所有任务
            future_to_stock = {
                executor.submit(self.analyze_single_stock, stock_code, config): stock_code 
                for stock_code in config.stock_codes
            }
            
            # 收集结果
            for future in as_completed(future_to_stock):
                stock_code = future_to_stock[future]
                try:
                    result = future.result()
                    results.append(result)
                    
                    if result.status == "success":
                        success_count += 1
                    else:
                        failed_count += 1
                    
                    # 定期报告进度
                    if self.progress_reporter and self.progress_reporter.should_report():
                        self.progress_reporter.report_progress()
                        
                except Exception as e:
                    print(f"❌ {stock_code} 分析任务异常: {str(e)}")
                    failed_count += 1
                    
                    # 使用错误处理器
                    if self.error_handler:
                        self.error_handler.handle_error(stock_code, e, "任务执行异常")
                    
                    results.append(StockAnalysisResult(
                        stock_code=stock_code,
                        stock_name="未知",
                        status="failed",
                        error_message=f"任务执行异常: {str(e)}"
                    ))
        
        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()
        
        # 停止监控
        if self.monitor:
            self.monitor.stop_monitoring()
            
            # 保存监控日志
            monitor_log_path = os.path.join(config.output_dir, "monitor_log.json")
            self.monitor.save_monitor_log(monitor_log_path)
        
        # 生成汇总统计
        summary_stats = self._generate_summary_stats(results)
        
        batch_result = BatchAnalysisResult(
            config=config,
            results=results,
            start_time=start_time.strftime('%Y-%m-%d %H:%M:%S'),
            end_time=end_time.strftime('%Y-%m-%d %H:%M:%S'),
            total_duration=total_duration,
            success_count=success_count,
            failed_count=failed_count,
            summary_stats=summary_stats
        )
        
        # 保存结果
        if config.save_individual_reports:
            self._save_individual_reports(batch_result)
        
        if config.save_summary_report:
            self._save_summary_report(batch_result)
        
        print(f"\n✅ 批量分析完成!")
        print(f"📊 总耗时: {total_duration:.2f}秒")
        print(f"✅ 成功: {success_count} 只")
        print(f"❌ 失败: {failed_count} 只")
        print(f"📁 结果目录: {config.output_dir}")
        
        # 显示错误摘要
        if self.monitor and failed_count > 0:
            error_summary = self.monitor.get_error_summary()
            print(f"\n❌ 错误摘要:")
            print(f"   总错误数: {error_summary['total_errors']}")
            if error_summary['common_errors']:
                print(f"   常见错误:")
                for error_msg, count in list(error_summary['common_errors'].items())[:3]:
                    print(f"     - {error_msg} ({count}次)")
        
        return batch_result
    
    def _generate_summary_stats(self, results: List[StockAnalysisResult]) -> Dict:
        """生成汇总统计信息"""
        stats = {
            'total_stocks': len(results),
            'success_rate': 0,
            'avg_analysis_time': 0,
            'industry_distribution': {},
            'price_ranges': {'low': 0, 'medium': 0, 'high': 0},
            'trend_distribution': {},
            'ai_analysis_coverage': 0
        }
        
        if not results:
            return stats
        
        success_count = sum(1 for r in results if r.status == "success")
        stats['success_rate'] = success_count / len(results) * 100
        
        # 统计行业分布
        for result in results:
            if result.summary and result.summary.get('industry'):
                industry = result.summary['industry']
                stats['industry_distribution'][industry] = stats['industry_distribution'].get(industry, 0) + 1
        
        # 统计价格区间
        for result in results:
            if result.summary and result.summary.get('current_price', 0) > 0:
                price = result.summary['current_price']
                if price < 20:
                    stats['price_ranges']['low'] += 1
                elif price < 100:
                    stats['price_ranges']['medium'] += 1
                else:
                    stats['price_ranges']['high'] += 1
        
        # 统计AI分析覆盖率
        ai_count = sum(1 for r in results if r.summary and r.summary.get('has_ai_analysis', False))
        stats['ai_analysis_coverage'] = ai_count / len(results) * 100
        
        return stats
    
    def _make_json_safe(self, obj):
        """将对象转换为JSON安全格式（处理DataFrame等不可序列化对象）"""
        import numpy as np
        import pandas as pd
        
        if isinstance(obj, dict):
            return {key: self._make_json_safe(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_safe(item) for item in obj]
        elif isinstance(obj, pd.Series):
            return obj.tolist()
        elif isinstance(obj, pd.DataFrame):
            return obj.to_dict('records')
        elif isinstance(obj, (np.integer, np.int64, np.int32)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif pd.isna(obj):
            return None
        elif hasattr(obj, 'isoformat'):
            return obj.isoformat()
        else:
            return obj
    
    def _save_individual_reports(self, batch_result: BatchAnalysisResult):
        """保存单只股票的分析报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        for result in batch_result.results:
            if result.analysis_data:
                # 保存JSON格式的详细数据
                filename = f"{result.stock_code}_{result.stock_name}_{timestamp}.json"
                filepath = os.path.join(batch_result.config.output_dir, filename)
                
                report_data = {
                    'stock_code': result.stock_code,
                    'stock_name': result.stock_name,
                    'analysis_time': result.analysis_time,
                    'status': result.status,
                    'summary': result.summary,
                    'analysis_data': result.analysis_data
                }
                
                try:
                    # 转换为JSON安全格式
                    safe_report_data = self._make_json_safe(report_data)
                    with open(filepath, 'w', encoding='utf-8') as f:
                        json.dump(safe_report_data, f, ensure_ascii=False, indent=2)
                    print(f"💾 已保存 {result.stock_code} 详细报告: {filename}")
                except Exception as e:
                    print(f"❌ 保存 {result.stock_code} 报告失败: {str(e)}")
    
    def _save_summary_report(self, batch_result: BatchAnalysisResult):
        """保存汇总报告"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 保存汇总CSV
        csv_filename = f"batch_analysis_summary_{timestamp}.csv"
        csv_filepath = os.path.join(batch_result.config.output_dir, csv_filename)
        
        summary_data = []
        for result in batch_result.results:
            row = {
                '股票代码': result.stock_code,
                '股票名称': result.stock_name,
                '分析状态': result.status,
                '当前价格': result.summary.get('current_price', 0) if result.summary else 0,
                '涨跌幅(%)': result.summary.get('change_percent', 0) if result.summary else 0,
                '行业': result.summary.get('industry', '') if result.summary else '',
                '技术趋势': result.summary.get('technical_trend', '') if result.summary else '',
                'RSI水平': result.summary.get('rsi_level', '') if result.summary else '',
                '新闻数量': result.summary.get('news_count', 0) if result.summary else 0,
                '盈利比例(%)': result.summary.get('profit_ratio', 0) if result.summary else 0,
                '分析完成数': result.summary.get('analysis_count', 0) if result.summary else 0,
                '包含AI分析': '是' if result.summary and result.summary.get('has_ai_analysis') else '否',
                '错误信息': result.error_message or '',
                '分析时间': result.analysis_time or ''
            }
            summary_data.append(row)
        
        try:
            df = pd.DataFrame(summary_data)
            df.to_csv(csv_filepath, index=False, encoding='utf-8-sig')
            print(f"📊 已保存汇总CSV: {csv_filename}")
        except Exception as e:
            print(f"❌ 保存汇总CSV失败: {str(e)}")
        
        # 保存详细汇总JSON
        json_filename = f"batch_analysis_detailed_{timestamp}.json"
        json_filepath = os.path.join(batch_result.config.output_dir, json_filename)
        
        detailed_report = {
            'batch_info': {
                'start_time': batch_result.start_time,
                'end_time': batch_result.end_time,
                'total_duration': batch_result.total_duration,
                'success_count': batch_result.success_count,
                'failed_count': batch_result.failed_count,
                'config': asdict(batch_result.config)
            },
            'summary_stats': batch_result.summary_stats,
            'results': [asdict(result) for result in batch_result.results]
        }
        
        try:
            # 转换为JSON安全格式
            safe_detailed_report = self._make_json_safe(detailed_report)
            with open(json_filepath, 'w', encoding='utf-8') as f:
                json.dump(safe_detailed_report, f, ensure_ascii=False, indent=2)
            print(f"📋 已保存详细汇总: {json_filename}")
        except Exception as e:
            print(f"❌ 保存详细汇总失败: {str(e)}")


# 便捷函数
def create_default_config(stock_codes: List[str], analysis_types: List[str] = None) -> BatchAnalysisConfig:
    """创建默认的批量分析配置"""
    if analysis_types is None:
        analysis_types = ['basic', 'technical', 'news', 'comprehensive']
    
    return BatchAnalysisConfig(
        stock_codes=stock_codes,
        analysis_types=analysis_types,
        use_cache=True,
        force_refresh=False,
        include_ai_analysis=True,
        max_workers=3,
        max_retry=2,
        output_dir=f"./batch_analysis_results/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    )


def quick_batch_analyze(stock_codes: List[str], analysis_types: List[str] = None) -> BatchAnalysisResult:
    """快速批量分析"""
    config = create_default_config(stock_codes, analysis_types)
    analyzer = BatchStockAnalyzer()
    return analyzer.batch_analyze(config)


if __name__ == "__main__":
    # 示例用法
    test_codes = ["000001", "600519", "300750"]
    result = quick_batch_analyze(test_codes, ['basic', 'technical'])
    print(f"分析完成，成功: {result.success_count}, 失败: {result.failed_count}")
