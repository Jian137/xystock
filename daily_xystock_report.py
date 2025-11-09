"""
XY Stock 批量分析脚本
使用新的批量分析模块进行股票分析
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

from stock.batch_analysis import BatchStockAnalyzer, BatchAnalysisConfig, create_default_config
from stock.batch_report import generate_batch_reports
from utils.email_sender import create_email_sender_from_config
from config_manager import ConfigManager


# ======================
# 配置区域
# ======================

# 股票代码列表
STOCK_LIST = [
    "600519",  # 贵州茅台
    "000001",  # 平安银行
    # "300750",  # 宁德时代
    # "601318",  # 中国平安
    # "002594",  # 比亚迪
    # "000002",  # 万科A
    # "600036",  # 招商银行
    # "000858",  # 五粮液
    # "002415",  # 海康威视
    # "600276",  # 恒瑞医药
]

# 分析类型配置
ANALYSIS_TYPES = ['basic', 'technical', 'news', 'comprehensive']

# 其他配置
MAX_WORKERS = 3  # 并发线程数
USE_CACHE = True  # 是否使用缓存
INCLUDE_AI_ANALYSIS = True  # 是否包含AI分析

# 报告生成配置
DEFAULT_REPORT_FORMAT = 'markdown'  # 默认报告格式: markdown, pdf, docx, html
GENERATE_REPORTS = True  # 是否自动生成报告


def batch_analyze():
    """批量分析所有股票"""
    print(f"\n🚀 XY Stock 批量分析开始")
    print(f"📅 分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📊 股票数量: {len(STOCK_LIST)}")
    print(f"🔍 分析类型: {', '.join(ANALYSIS_TYPES)}")
    print(f"🔧 并发数: {MAX_WORKERS}")
    print(f"💾 使用缓存: {USE_CACHE}")
    print(f"🤖 AI分析: {INCLUDE_AI_ANALYSIS}")
    print("=" * 50)
    
    # 创建分析配置
    config = BatchAnalysisConfig(
        stock_codes=STOCK_LIST,
        analysis_types=ANALYSIS_TYPES,
        use_cache=USE_CACHE,
        force_refresh=False,
        include_ai_analysis=INCLUDE_AI_ANALYSIS,
        max_workers=MAX_WORKERS,
        max_retry=2,
        user_opinion="",
        user_position="不确定",
        output_dir=f"./batch_analysis_results/{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        save_individual_reports=True,
        save_summary_report=True
    )
    
    # 执行批量分析
    analyzer = BatchStockAnalyzer()
    result = analyzer.batch_analyze(config)
    
    # 显示结果摘要
    print("\n" + "=" * 50)
    print("📊 分析结果摘要:")
    print(f"✅ 成功: {result.success_count} 只")
    print(f"❌ 失败: {result.failed_count} 只")
    print(f"⏱️  总耗时: {result.total_duration:.2f}秒")
    print(f"📁 结果目录: {config.output_dir}")
    
    # 显示失败股票
    if result.failed_count > 0:
        print("\n❌ 失败的股票:")
        for stock_result in result.results:
            if stock_result.status == "failed":
                print(f"  - {stock_result.stock_code} ({stock_result.stock_name}): {stock_result.error_message}")
    
    # 显示成功股票摘要
    if result.success_count > 0:
        print("\n✅ 成功分析的股票:")
        for stock_result in result.results:
            if stock_result.status in ["success", "partial"]:
                summary = stock_result.summary or {}
                price = summary.get('current_price', 0)
                change = summary.get('change_percent', 0)
                industry = summary.get('industry', '')
                print(f"  - {stock_result.stock_code} ({stock_result.stock_name}): 价格 {price}, 涨跌 {change:+.2f}%, 行业 {industry}")
    
    print(f"\n📈 详细结果请查看: {config.output_dir}")
    
    # 自动生成报告
    report_files = []
    if GENERATE_REPORTS and result.success_count > 0:
        print(f"\n📄 开始生成 {DEFAULT_REPORT_FORMAT.upper()} 格式报告...")
        try:
            report_result = generate_batch_reports(
                config.output_dir, 
                DEFAULT_REPORT_FORMAT, 
                'individual'
            )
            if report_result:
                print(f"✅ 报告生成成功！")
                print(f"📁 报告位置: {config.output_dir}")
                report_files = report_result
            else:
                print(f"❌ 报告生成失败")
        except Exception as e:
            print(f"❌ 报告生成过程中出现错误: {e}")
    
    # 发送邮件
    try:
        config_manager = ConfigManager()
        email_config = config_manager.get_section('EMAIL')
        
        if email_config and email_config.get('ENABLED', False):
            print(f"\n📧 开始发送邮件...")
            email_sender = create_email_sender_from_config(config_manager)
            
            if email_sender:
                recipient_emails = email_config.get('RECIPIENT_EMAILS', [])
                if recipient_emails:
                    # 生成邮件摘要
                    summary_text = f"""
XY Stock 股票分析报告

分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
股票数量: {len(STOCK_LIST)}
分析类型: {', '.join(ANALYSIS_TYPES)}

分析结果摘要:
- 成功: {result.success_count} 只
- 失败: {result.failed_count} 只
- 总耗时: {result.total_duration:.2f}秒

结果目录: {config.output_dir}

成功分析的股票:
"""
                    for stock_result in result.results:
                        if stock_result.status in ["success", "partial"]:
                            summary = stock_result.summary or {}
                            price = summary.get('current_price', 0)
                            change = summary.get('change_percent', 0)
                            industry = summary.get('industry', '')
                            summary_text += f"- {stock_result.stock_code} ({stock_result.stock_name}): 价格 {price}, 涨跌 {change:+.2f}%, 行业 {industry}\n"
                    
                    # 准备附件文件列表（相对于结果目录）
                    attachment_files = [os.path.basename(f) for f in report_files] if report_files else []
                    
                    # 发送邮件
                    success = email_sender.send_analysis_report(
                        recipient_emails=recipient_emails,
                        analysis_result_dir=config.output_dir,
                        report_files=attachment_files,
                        summary_text=summary_text
                    )
                    
                    if success:
                        print(f"✅ 邮件发送成功！收件人: {', '.join(recipient_emails)}")
                    else:
                        print(f"❌ 邮件发送失败")
                else:
                    print(f"⚠️  未配置收件人邮箱，跳过邮件发送")
            else:
                print(f"⚠️  邮件发送器初始化失败，跳过邮件发送")
        else:
            print(f"ℹ️  邮件功能未启用，跳过邮件发送")
    except Exception as e:
        print(f"⚠️  邮件发送过程中出现错误: {e}")
    
    return result


def quick_analyze(stock_codes=None, analysis_types=None):
    """快速分析指定股票"""
    if stock_codes is None:
        stock_codes = STOCK_LIST[:5]  # 默认分析前5只
    
    if analysis_types is None:
        analysis_types = ['basic', 'technical']
    
    print(f"\n⚡ 快速分析模式")
    print(f"📊 股票: {', '.join(stock_codes)}")
    print(f"🔍 分析类型: {', '.join(analysis_types)}")
    
    config = create_default_config(stock_codes, analysis_types)
    analyzer = BatchStockAnalyzer()
    result = analyzer.batch_analyze(config)
    
    print(f"\n✅ 快速分析完成: 成功 {result.success_count}, 失败 {result.failed_count}")
    return result


def generate_reports_from_existing(analysis_dir, report_format='markdown', report_type='individual'):
    """从现有的分析结果生成报告"""
    print(f"\n📄 从现有分析结果生成报告")
    print(f"📁 分析目录: {analysis_dir}")
    print(f"📋 报告格式: {report_format.upper()}")
    print(f"📊 报告类型: {report_type}")
    print("=" * 50)
    
    if not os.path.exists(analysis_dir):
        print(f"❌ 错误: 分析目录不存在: {analysis_dir}")
        return False
    
    try:
        result = generate_batch_reports(analysis_dir, report_format, report_type)
        if result:
            print(f"✅ 报告生成成功！")
            print(f"📁 报告位置: {analysis_dir}")
            return True
        else:
            print(f"❌ 报告生成失败")
            return False
    except Exception as e:
        print(f"❌ 报告生成过程中出现错误: {e}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='XY Stock 批量分析工具')
    parser.add_argument('--mode', choices=['full', 'quick', 'report'], default='full', 
                       help='运行模式: full=完整分析, quick=快速分析, report=仅生成报告')
    parser.add_argument('--stocks', nargs='+', help='指定要分析的股票代码')
    parser.add_argument('--types', nargs='+', 
                       choices=['basic', 'technical', 'news', 'chip', 'comprehensive'],
                       help='指定分析类型')
    parser.add_argument('--analysis-dir', help='指定分析结果目录（用于report模式）')
    parser.add_argument('--format', choices=['markdown', 'pdf', 'docx', 'html'], 
                       default=DEFAULT_REPORT_FORMAT, help='报告格式')
    parser.add_argument('--report-type', choices=['individual', 'summary', 'both'], 
                       default='individual', help='报告类型')
    parser.add_argument('--no-reports', action='store_true', help='不自动生成报告')
    
    args = parser.parse_args()
    
    # 临时禁用报告生成
    if args.no_reports:
        # 修改全局变量以禁用报告生成
        import sys
        module = sys.modules[__name__]
        module.GENERATE_REPORTS = False
    
    if args.mode == 'report':
        if not args.analysis_dir:
            print("❌ 错误: report模式需要指定 --analysis-dir 参数")
            sys.exit(1)
        generate_reports_from_existing(args.analysis_dir, args.format, args.report_type)
    elif args.mode == 'quick':
        quick_analyze(args.stocks, args.types)
    else:
        batch_analyze()
