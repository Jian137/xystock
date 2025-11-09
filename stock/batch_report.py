"""
批量分析报告生成模块
为批量分析结果生成各种格式的报告
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from utils.report_utils import generate_pdf_report, generate_docx_report, generate_markdown_file, generate_html_report
from version import get_full_version


def generate_batch_analysis_report(batch_result_dir: str, format_type: str = "pdf") -> bytes:
    """
    生成批量分析报告
    
    Args:
        batch_result_dir: 批量分析结果目录
        format_type: 报告格式 (pdf, docx, html, markdown)
    
    Returns:
        报告内容的字节数据
    """
    try:
        # 读取批量分析结果
        batch_data = _load_batch_analysis_data(batch_result_dir)
        if not batch_data:
            error_msg = "无法加载批量分析数据"
            return _generate_error_report(error_msg, format_type)
        
        # 生成Markdown内容
        md_content = _generate_markdown_content(batch_data)
        
        # 转换为指定格式
        if format_type == "pdf":
            return generate_pdf_report(md_content)
        elif format_type == "docx":
            return generate_docx_report(md_content)
        elif format_type == "html":
            return generate_html_report(md_content)
        elif format_type == "markdown":
            return generate_markdown_file(md_content)
        else:
            raise ValueError(f"不支持的格式: {format_type}")
            
    except Exception as e:
        error_msg = f"生成批量分析报告失败: {str(e)}"
        return _generate_error_report(error_msg, format_type)


def generate_individual_stock_reports(batch_result_dir: str, format_type: str = "pdf") -> Dict[str, bytes]:
    """
    为每只股票生成独立的完整分析报告
    
    Args:
        batch_result_dir: 批量分析结果目录
        format_type: 报告格式 (pdf, docx, html, markdown)
    
    Returns:
        字典，键为股票代码，值为报告内容的字节数据
    """
    try:
        # 读取批量分析结果
        batch_data = _load_batch_analysis_data(batch_result_dir)
        if not batch_data:
            raise Exception("无法加载批量分析数据")
        
        detailed = batch_data['detailed']
        results = detailed['results']
        
        individual_reports = {}
        
        for result in results:
            if result['status'] == 'success':
                stock_code = result['stock_code']
                stock_name = result['stock_name']
                
                # 生成单只股票的完整报告
                md_content = _generate_individual_stock_markdown(result, detailed['batch_info'])
                
                # 转换为指定格式
                if format_type == "pdf":
                    report_content = generate_pdf_report(md_content)
                elif format_type == "docx":
                    report_content = generate_docx_report(md_content)
                elif format_type == "html":
                    report_content = generate_html_report(md_content)
                elif format_type == "markdown":
                    report_content = generate_markdown_file(md_content)
                else:
                    raise ValueError(f"不支持的格式: {format_type}")
                
                individual_reports[stock_code] = report_content
                print(f"✅ 已生成 {stock_name}({stock_code}) 的{format_type.upper()}报告")
        
        return individual_reports
        
    except Exception as e:
        error_msg = f"生成个股报告失败: {str(e)}"
        print(f"❌ {error_msg}")
        return {}


def export_all_individual_reports(batch_result_dir: str, format_type: str = "pdf", output_dir: str = None) -> List[str]:
    """
    导出所有个股的独立报告到文件
    
    Args:
        batch_result_dir: 批量分析结果目录
        format_type: 报告格式 (pdf, docx, html, markdown)
        output_dir: 输出目录，如果为None则使用batch_result_dir
    
    Returns:
        生成的文件路径列表
    """
    if output_dir is None:
        output_dir = batch_result_dir
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    # 生成所有个股报告
    individual_reports = generate_individual_stock_reports(batch_result_dir, format_type)
    
    generated_files = []
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    for stock_code, report_content in individual_reports.items():
        # 获取股票名称
        batch_data = _load_batch_analysis_data(batch_result_dir)
        stock_name = ""
        for result in batch_data['detailed']['results']:
            if result['stock_code'] == stock_code:
                stock_name = result['stock_name']
                break
        
        # 生成文件名
        safe_stock_name = stock_name.replace(' ', '_').replace('*', '').replace('/', '_')
        filename = f"{stock_code}_{safe_stock_name}_完整分析报告_{timestamp}.{format_type}"
        filepath = os.path.join(output_dir, filename)
        
        # 保存文件
        with open(filepath, 'wb') as f:
            f.write(report_content)
        
        generated_files.append(filepath)
        print(f"📄 已保存: {filename}")
    
    return generated_files


def _load_batch_analysis_data(batch_result_dir: str) -> Optional[Dict]:
    """加载批量分析数据"""
    try:
        # 查找详细汇总文件
        files = os.listdir(batch_result_dir)
        detailed_file = None
        summary_file = None
        
        for file in files:
            if file.startswith("batch_analysis_detailed_") and file.endswith(".json"):
                detailed_file = file
            elif file.startswith("batch_analysis_summary_") and file.endswith(".csv"):
                summary_file = file
        
        if not detailed_file:
            return None
        
        # 读取详细数据
        detailed_path = os.path.join(batch_result_dir, detailed_file)
        with open(detailed_path, 'r', encoding='utf-8') as f:
            detailed_data = json.load(f)
        
        # 读取汇总数据
        summary_data = None
        if summary_file:
            summary_path = os.path.join(batch_result_dir, summary_file)
            summary_data = pd.read_csv(summary_path, encoding='utf-8-sig')
        
        return {
            'detailed': detailed_data,
            'summary': summary_data,
            'result_dir': batch_result_dir
        }
        
    except Exception as e:
        print(f"加载批量分析数据失败: {e}")
        return None


def _generate_individual_stock_markdown(result: Dict, batch_info: Dict) -> str:
    """生成单只股票的完整分析报告Markdown内容"""
    stock_code = result['stock_code']
    stock_name = result['stock_name']
    analysis_data = result.get('analysis_data', {})
    summary = result.get('summary', {})
    
    # 获取版本信息
    version_info = get_full_version()
    
    # 开始生成内容
    content = f"""# {stock_name}({stock_code}) 完整分析报告

## 📊 分析概览

**股票代码**: {stock_code}  
**股票名称**: {stock_name}  
**分析时间**: {result['analysis_time']}  
**分析状态**: {result['status']}  
**当前价格**: {summary.get('current_price', 'N/A')}  
**涨跌幅**: {summary.get('change_percent', 'N/A')}%  
**技术趋势**: {summary.get('technical_trend', 'N/A')}  
**RSI水平**: {summary.get('rsi_level', 'N/A')}  
**新闻数量**: {summary.get('news_count', 0)}  
**盈利比例**: {summary.get('profit_ratio', 0)}%  
**分析完成数**: {summary.get('analysis_count', 0)}  
**包含AI分析**: {'是' if summary.get('has_ai_analysis', False) else '否'}  

**系统版本**: {version_info}

---

"""
    
    # 1. 基本信息部分
    content += """# 📋 基本信息

"""
    
    basic_info = analysis_data.get('basic_info', {})
    if basic_info and 'error' not in basic_info:
        content += "## 公司基本信息\n\n"
        
        # 基本信息表格
        content += "| 项目 | 数值 |\n"
        content += "|------|------|\n"
        
        basic_fields = [
            ('股票代码', '股票代码'),
            ('股票名称', '股票名称'),
            ('当前价格', 'current_price'),
            ('涨跌幅', 'change_percent'),
            ('成交量', 'volume'),
            ('成交额', 'amount'),
            ('最高价', 'high'),
            ('最低价', 'low'),
            ('开盘价', 'open'),
            ('所处行业', '所处行业'),
            ('市盈率', '市盈率'),
            ('市净率', '市净率'),
            ('总市值', '总市值'),
            ('流通市值', '流通市值'),
            ('净资产收益率(ROE)', '净资产收益率(ROE)'),
            ('毛利率', '毛利率'),
            ('销售净利率', '销售净利率'),
            ('资产负债率', '资产负债率'),
            ('基本每股收益', '基本每股收益'),
            ('每股净资产', '每股净资产')
        ]
        
        for display_name, field_name in basic_fields:
            value = basic_info.get(field_name, 'N/A')
            if isinstance(value, float):
                if field_name in ['current_price', 'high', 'low', 'open']:
                    value = f"{value:.2f}"
                elif field_name in ['change_percent']:
                    value = f"{value:.2f}%"
                elif field_name in ['volume']:
                    value = f"{int(value):,}"
                elif field_name in ['amount']:
                    value = f"{value:,.0f}"
                elif field_name in ['总市值', '流通市值']:
                    value = f"{value:,.0f}"
            content += f"| {display_name} | {value} |\n"
        
        content += "\n"
        
        # 分红信息
        if '近年分红详情' in basic_info:
            content += "## 分红信息\n\n"
            content += "| 年份 | 分红类型 | 送股比例 | 转增比例 | 派息比例 |\n"
            content += "|------|----------|----------|----------|----------|\n"
            
            for dividend in basic_info['近年分红详情']:
                content += f"| {dividend.get('年份', 'N/A')} | {dividend.get('分红类型', 'N/A')} | {dividend.get('送股比例', 0)} | {dividend.get('转增比例', 0)} | {dividend.get('派息比例', 0)} |\n"
            
            content += "\n"
        
        # AI基本面分析
        if 'fundamental_ai' in analysis_data:
            ai_result = analysis_data['fundamental_ai']
            if ai_result.get('analysis_result'):
                content += "## 🤖 AI基本面分析\n\n"
                content += f"{ai_result['analysis_result']}\n\n"
                content += f"*分析生成时间: {ai_result.get('timestamp', 'N/A')}*\n\n"
        
        # AI公司分析
        if 'company_ai' in analysis_data:
            ai_result = analysis_data['company_ai']
            if ai_result.get('analysis_result'):
                content += "## 🏢 AI公司分析\n\n"
                content += f"{ai_result['analysis_result']}\n\n"
                content += f"*分析生成时间: {ai_result.get('timestamp', 'N/A')}*\n\n"
    else:
        content += "基本信息获取失败或数据不完整。\n\n"
    
    content += "---\n\n"
    
    # 2. 行情走势部分
    content += """# 📈 行情走势

"""
    
    technical_info = analysis_data.get('technical_analysis', {})
    if technical_info and 'error' not in technical_info:
        content += "## 技术指标分析\n\n"
        
        # 技术指标表格
        indicators = technical_info.get('indicators', {})
        if indicators:
            content += "| 指标名称 | 数值 |\n"
            content += "|----------|------|\n"
            
            indicator_fields = [
                ('MA5', 'ma_5'),
                ('MA10', 'ma_10'),
                ('MA20', 'ma_20'),
                ('MA60', 'ma_60'),
                ('EMA12', 'ema_12'),
                ('EMA26', 'ema_26'),
                ('MACD', 'macd'),
                ('MACD信号线', 'macd_signal'),
                ('MACD柱状图', 'macd_histogram'),
                ('KDJ-K', 'kdj_k'),
                ('KDJ-D', 'kdj_d'),
                ('KDJ-J', 'kdj_j'),
                ('RSI14', 'rsi_14'),
                ('布林上轨', 'boll_upper'),
                ('布林中轨', 'boll_middle'),
                ('布林下轨', 'boll_lower'),
                ('威廉指标', 'wr_14'),
                ('CCI指标', 'cci_14')
            ]
            
            for display_name, field_name in indicator_fields:
                value = indicators.get(field_name)
                if value is not None:
                    if isinstance(value, float):
                        value = f"{value:.4f}"
                else:
                    value = 'N/A'
                content += f"| {display_name} | {value} |\n"
            
            content += "\n"
        
        # 趋势分析
        if indicators.get('ma_trend'):
            content += f"**移动平均线趋势**: {indicators['ma_trend']}\n\n"
        if indicators.get('macd_trend'):
            content += f"**MACD趋势**: {indicators['macd_trend']}\n\n"
        
        # 风险指标
        risk_metrics = technical_info.get('risk_metrics', {})
        if risk_metrics:
            content += "## 风险指标\n\n"
            content += "| 风险指标 | 数值 |\n"
            content += "|----------|------|\n"
            
            risk_fields = [
                ('年化波动率', 'annualized_volatility'),
                ('最大回撤', 'max_drawdown'),
                ('夏普比率', 'sharpe_ratio'),
                ('VaR(95%)', 'var_95'),
                ('CVaR(95%)', 'cvar_95')
            ]
            
            for display_name, field_name in risk_fields:
                value = risk_metrics.get(field_name)
                if value is not None:
                    if isinstance(value, float):
                        value = f"{value:.4f}"
                else:
                    value = 'N/A'
                content += f"| {display_name} | {value} |\n"
            
            content += "\n"
        
        # AI技术分析
        if 'technical_ai' in analysis_data:
            ai_result = analysis_data['technical_ai']
            if ai_result.get('analysis_result'):
                content += "## 🤖 AI技术分析\n\n"
                content += f"{ai_result['analysis_result']}\n\n"
                content += f"*分析生成时间: {ai_result.get('timestamp', 'N/A')}*\n\n"
    else:
        content += "技术分析数据获取失败或数据不完整。\n\n"
    
    content += "---\n\n"
    
    # 3. 新闻资讯部分
    content += """# 📰 新闻资讯

"""
    
    news_info = analysis_data.get('news_analysis', {})
    if news_info and 'error' not in news_info and news_info.get('news_data'):
        news_data = news_info['news_data']
        content += f"**新闻总数**: {len(news_data)}条\n\n"
        
        if news_data:
            content += "## 最新新闻\n\n"
            for i, news in enumerate(news_data[:10], 1):  # 显示最新10条
                content += f"### {i}. {news.get('title', '无标题')}\n\n"
                content += f"**发布时间**: {news.get('time', 'N/A')}\n\n"
                content += f"**内容摘要**: {news.get('content', '无内容')}\n\n"
                content += f"**来源**: {news.get('source', 'N/A')}\n\n"
                content += "---\n\n"
        
        # AI新闻分析
        if news_info.get('ai_analysis'):
            ai_result = news_info['ai_analysis']
            if ai_result.get('report'):
                content += "## 🤖 AI新闻分析\n\n"
                content += f"{ai_result['report']}\n\n"
                content += f"*分析生成时间: {ai_result.get('timestamp', 'N/A')}*\n\n"
    else:
        content += "新闻资讯数据获取失败或暂无相关新闻。\n\n"
    
    content += "---\n\n"
    
    # 4. 筹码分析部分
    content += """# 🎯 筹码分析

"""
    
    chip_info = analysis_data.get('chip_analysis', {})
    if chip_info and 'error' not in chip_info:
        content += "## 筹码分布数据\n\n"
        
        # 筹码数据表格
        content += "| 指标名称 | 数值 |\n"
        content += "|----------|------|\n"
        
        chip_fields = [
            ('最新日期', 'latest_date'),
            ('获利比例', 'profit_ratio'),
            ('平均成本', 'avg_cost'),
            ('90成本-低', 'cost_90_low'),
            ('90成本-高', 'cost_90_high'),
            ('90集中度', 'concentration_90'),
            ('70成本-低', 'cost_70_low'),
            ('70成本-高', 'cost_70_high'),
            ('70集中度', 'concentration_70'),
            ('支撑位', 'support_level'),
            ('阻力位', 'resistance_level'),
            ('成本中心', 'cost_center')
        ]
        
        for display_name, field_name in chip_fields:
            value = chip_info.get(field_name)
            if value is not None:
                if isinstance(value, float):
                    if field_name in ['profit_ratio', 'concentration_90', 'concentration_70']:
                        value = f"{value:.2f}%"
                    else:
                        value = f"{value:.2f}"
            else:
                value = 'N/A'
            content += f"| {display_name} | {value} |\n"
        
        content += "\n"
        
        # 筹码分析指标
        analysis = chip_info.get('analysis', {})
        if analysis:
            content += "## 筹码分析指标\n\n"
            content += f"**获利状态**: {analysis.get('profit_status', 'N/A')}\n\n"
            content += f"**集中度状态**: {analysis.get('concentration_status', 'N/A')}\n\n"
            content += f"**风险等级**: {analysis.get('risk_level', 'N/A')}\n\n"
        
        # AI筹码分析
        if 'chip_ai' in analysis_data:
            ai_result = analysis_data['chip_ai']
            if ai_result.get('analysis_result'):
                content += "## 🤖 AI筹码分析\n\n"
                content += f"{ai_result['analysis_result']}\n\n"
                content += f"*分析生成时间: {ai_result.get('timestamp', 'N/A')}*\n\n"
    else:
        content += "筹码分析数据获取失败或该股票不支持筹码分析。\n\n"
    
    content += "---\n\n"
    
    # 5. 综合分析部分
    content += """# 🎯 综合分析

"""
    
    comprehensive_ai = analysis_data.get('comprehensive_analysis', {})
    if comprehensive_ai and comprehensive_ai.get('report'):
        content += "## 🤖 AI综合分析\n\n"
        content += f"{comprehensive_ai['report']}\n\n"
        content += f"*分析生成时间: {comprehensive_ai.get('timestamp', 'N/A')}*\n\n"
        
        # 分析信息
        analysis_info = comprehensive_ai.get('analysis_info', {})
        if analysis_info:
            content += "## 分析信息\n\n"
            content += f"**数据来源数量**: {analysis_info.get('data_sources_count', 0)}个\n\n"
            content += f"**分析时间**: {analysis_info.get('analysis_time', 'N/A')}\n\n"
    else:
        content += "综合分析数据获取失败或未进行AI综合分析。\n\n"
    
    # 添加报告结尾
    content += f"""---

## 📊 报告总结

本报告基于 {batch_info['start_time']} 的批量分析结果生成，包含了 {stock_name}({stock_code}) 的完整分析数据。

**分析维度**:
- ✅ 基本信息分析
- ✅ 行情走势分析  
- ✅ 新闻资讯分析
- ✅ 筹码分析
- ✅ 综合分析

**数据来源**: XY Stock 股票分析系统  
**报告生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**系统版本**: {version_info}

---

*本报告仅供参考，不构成投资建议。投资有风险，入市需谨慎。*
"""
    
    return content


def _generate_markdown_content(batch_data: Dict) -> str:
    """生成Markdown格式的报告内容"""
    detailed = batch_data['detailed']
    summary = batch_data['summary']
    result_dir = batch_data['result_dir']
    
    # 获取版本信息
    version_info = get_full_version()
    
    # 基本信息
    batch_info = detailed['batch_info']
    results = detailed['results']
    summary_stats = detailed['summary_stats']
    
    # 开始生成内容
    content = f"""# 批量股票分析报告

## 📊 分析概览

**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**分析时间**: {batch_info['start_time']} - {batch_info['end_time']}  
**总耗时**: {batch_info['total_duration']:.2f}秒  
**分析股票数**: {len(results)}  
**成功数量**: {batch_info['success_count']}  
**失败数量**: {batch_info['failed_count']}  
**成功率**: {(batch_info['success_count'] / len(results) * 100):.1f}%  

**系统版本**: {version_info}

---

## 📈 分析配置

- **分析类型**: {', '.join(batch_info['config']['analysis_types'])}
- **使用缓存**: {'是' if batch_info['config']['use_cache'] else '否'}
- **AI分析**: {'启用' if batch_info['config']['include_ai_analysis'] else '禁用'}
- **并发数**: {batch_info['config']['max_workers']}
- **最大重试**: {batch_info['config']['max_retry']}

---

## 📋 股票分析结果

"""
    
    # 添加汇总表格
    if summary is not None:
        content += "### 结果汇总表\n\n"
        content += "| 股票代码 | 股票名称 | 分析状态 | 当前价格 | 涨跌幅(%) | 技术趋势 | RSI水平 | 新闻数量 | 盈利比例(%) | 分析完成数 | 包含AI分析 |\n"
        content += "|---------|---------|---------|---------|---------|---------|---------|---------|---------|---------|---------|\n"
        
        for _, row in summary.iterrows():
            content += f"| {row['股票代码']} | {row['股票名称']} | {row['分析状态']} | {row['当前价格']} | {row['涨跌幅(%)']} | {row['技术趋势']} | {row['RSI水平']} | {row['新闻数量']} | {row['盈利比例(%)']} | {row['分析完成数']} | {'是' if row['包含AI分析'] else '否'} |\n"
        
        content += "\n"
    
    # 添加统计信息
    if summary_stats:
        content += "## 📊 统计分析\n\n"
        
        # 行业分布
        if summary_stats.get('industry_distribution'):
            content += "### 行业分布\n\n"
            industry_data = summary_stats['industry_distribution']
            for industry, count in industry_data.items():
                content += f"- **{industry}**: {count}只\n"
            content += "\n"
        
        # 价格区间分布
        if summary_stats.get('price_ranges'):
            content += "### 价格区间分布\n\n"
            price_data = summary_stats['price_ranges']
            for price_range, count in price_data.items():
                content += f"- **{price_range}**: {count}只\n"
            content += "\n"
        
        # 技术趋势分布
        if summary_stats.get('trend_distribution'):
            content += "### 技术趋势分布\n\n"
            trend_data = summary_stats['trend_distribution']
            for trend, count in trend_data.items():
                content += f"- **{trend}**: {count}只\n"
            content += "\n"
    
    # 添加详细分析结果
    content += "## 📄 详细分析结果\n\n"
    
    for i, result in enumerate(results, 1):
        if result['status'] == 'success':
            content += f"### {i}. {result['stock_name']} ({result['stock_code']})\n\n"
            
            # 基本信息
            summary_data = result.get('summary', {})
            if summary_data:
                content += f"**当前价格**: {summary_data.get('current_price', 'N/A')}  \n"
                content += f"**涨跌幅**: {summary_data.get('change_percent', 'N/A')}%  \n"
                content += f"**技术趋势**: {summary_data.get('technical_trend', 'N/A')}  \n"
                content += f"**RSI水平**: {summary_data.get('rsi_level', 'N/A')}  \n"
                content += f"**新闻数量**: {summary_data.get('news_count', 0)}  \n"
                content += f"**盈利比例**: {summary_data.get('profit_ratio', 0)}%  \n"
                content += f"**分析完成数**: {summary_data.get('analysis_count', 0)}  \n"
                content += f"**包含AI分析**: {'是' if summary_data.get('has_ai_analysis', False) else '否'}  \n\n"
            
            # 如果有AI分析结果，添加简要摘要
            analysis_data = result.get('analysis_data', {})
            if analysis_data.get('comprehensive_ai'):
                ai_result = analysis_data['comprehensive_ai']
                if ai_result.get('analysis_result'):
                    content += f"**AI分析摘要**: {ai_result['analysis_result'][:200]}...\n\n"
            
            content += "---\n\n"
        else:
            content += f"### {i}. {result['stock_name']} ({result['stock_code']}) - 分析失败\n\n"
            content += f"**错误信息**: {result.get('error_message', '未知错误')}\n\n"
            content += "---\n\n"
    
    # 添加文件信息
    content += "## 📁 相关文件\n\n"
    content += f"**结果目录**: `{result_dir}`\n\n"
    
    files = os.listdir(result_dir)
    content += "**包含文件**:\n"
    for file in sorted(files):
        content += f"- {file}\n"
    
    content += f"\n---\n\n*报告由 XY Stock 系统自动生成于 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*"
    
    return content


def _generate_error_report(error_msg: str, format_type: str) -> bytes:
    """生成错误报告"""
    error_content = f"# 批量分析报告生成失败\n\n**错误信息**: {error_msg}\n\n*请检查数据文件是否完整*"
    
    if format_type == "pdf":
        return generate_pdf_report(error_content)
    elif format_type == "docx":
        return generate_docx_report(error_content)
    elif format_type == "html":
        return generate_html_report(error_content)
    elif format_type == "markdown":
        return generate_markdown_file(error_content)
    else:
        return error_content.encode('utf-8')


# 便捷函数
def generate_batch_report_from_dir(result_dir: str, format_type: str = "pdf") -> bytes:
    """从结果目录生成批量分析报告"""
    return generate_batch_analysis_report(result_dir, format_type)


def generate_batch_reports(batch_result_dir: str, format_type: str = "markdown", report_type: str = "individual") -> List[str]:
    """
    生成批量分析报告（便捷函数）
    
    Args:
        batch_result_dir: 批量分析结果目录
        format_type: 报告格式 (pdf, docx, html, markdown)
        report_type: 报告类型 ('individual'=个股报告, 'summary'=汇总报告, 'both'=两者)
    
    Returns:
        生成的文件路径列表
    """
    generated_files = []
    
    try:
        if report_type in ['individual', 'both']:
            # 生成个股报告
            files = export_all_individual_reports(batch_result_dir, format_type)
            generated_files.extend(files)
        
        if report_type in ['summary', 'both']:
            # 生成汇总报告
            report_content = generate_batch_analysis_report(batch_result_dir, format_type)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"batch_analysis_report_{timestamp}.{format_type}"
            filepath = os.path.join(batch_result_dir, filename)
            
            with open(filepath, 'wb') as f:
                f.write(report_content)
            
            generated_files.append(filepath)
            print(f"✅ 批量分析汇总报告已生成: {filename}")
        
        return generated_files
        
    except Exception as e:
        print(f"❌ 生成报告失败: {e}")
        return []


if __name__ == "__main__":
    # 测试功能
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python batch_report.py <结果目录> [格式] [模式]")
        print("格式: pdf, docx, html, markdown")
        print("模式: batch(批量报告) 或 individual(个股报告，默认)")
        print("")
        print("示例:")
        print("  python batch_report.py batch_analysis_results/20251016_194726 pdf")
        print("  python batch_report.py batch_analysis_results/20251016_194726 pdf individual")
        print("  python batch_report.py batch_analysis_results/20251016_194726 docx batch")
        sys.exit(1)
    
    result_dir = sys.argv[1]
    format_type = sys.argv[2] if len(sys.argv) > 2 else "pdf"
    mode = sys.argv[3] if len(sys.argv) > 3 else "individual"
    
    if not os.path.exists(result_dir):
        print(f"错误: 目录不存在 {result_dir}")
        sys.exit(1)
    
    try:
        if mode == "batch":
            # 生成批量汇总报告
            report_content = generate_batch_analysis_report(result_dir, format_type)
            
            # 保存到文件
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"batch_analysis_report_{timestamp}.{format_type}"
            
            with open(filename, 'wb') as f:
                f.write(report_content)
            
            print(f"✅ 批量分析汇总报告已生成: {filename}")
            
        else:
            # 生成个股独立报告
            print(f"🚀 开始生成个股独立报告...")
            print(f"📁 结果目录: {result_dir}")
            print(f"📄 格式: {format_type.upper()}")
            print("=" * 50)
            
            generated_files = export_all_individual_reports(result_dir, format_type)
            
            print("=" * 50)
            print(f"✅ 个股报告生成完成!")
            print(f"📊 共生成 {len(generated_files)} 个报告文件")
            print("")
            print("📁 生成的文件:")
            for filepath in generated_files:
                print(f"  - {os.path.basename(filepath)}")
        
    except Exception as e:
        print(f"❌ 生成报告失败: {e}")
        sys.exit(1)
