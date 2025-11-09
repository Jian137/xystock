"""
批量股票分析页面组件
提供批量分析多只股票的UI界面
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
import sys

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from stock.batch_analysis import BatchStockAnalyzer, BatchAnalysisConfig, create_default_config
from ui.config import STOCK_CODE_EXAMPLES


def display_batch_analysis_page():
    """显示批量分析页面"""
    st.header("📊 批量股票分析")
    st.markdown("---")
    
    # 页面说明
    st.info("""
    💡 **功能说明**: 支持同时分析多只股票，包括基本面、技术面、新闻面、筹码面等维度的分析。
    可以选择是否启用AI智能分析，支持并发处理以提高效率。
    """)
    
    # 创建标签页
    tab1, tab2, tab3, tab4 = st.tabs(["⚙️ 配置分析", "📈 执行分析", "📊 查看结果", "📁 历史记录"])
    
    with tab1:
        display_analysis_config()
    
    with tab2:
        display_analysis_execution()
    
    with tab3:
        display_analysis_results()
    
    with tab4:
        display_analysis_history()


def display_analysis_config():
    """显示分析配置界面"""
    st.subheader("📋 分析配置")
    
    # 股票列表配置
    st.markdown("#### 🎯 股票列表")
    
    # 配置方式选择
    config_method = st.radio(
        "选择配置方式:",
        ["手动输入", "从示例选择", "从文件导入"],
        horizontal=True
    )
    
    stock_codes = []
    
    if config_method == "手动输入":
        stock_input = st.text_area(
            "请输入股票代码 (每行一个):",
            placeholder="000001\n600519\n300750\n601318\n002594",
            height=150,
            help="每行输入一个股票代码，支持A股、港股、ETF等"
        )
        
        if stock_input:
            stock_codes = [code.strip() for code in stock_input.split('\n') if code.strip()]
    
    elif config_method == "从示例选择":
        # 显示示例股票
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**A股示例:**")
            a_stocks = STOCK_CODE_EXAMPLES.get("A股", [])
            for stock in a_stocks:
                if st.checkbox(f"{stock}", key=f"a_{stock}"):
                    stock_codes.append(stock)
        
        with col2:
            st.markdown("**港股示例:**")
            hk_stocks = STOCK_CODE_EXAMPLES.get("港股", [])
            for stock in hk_stocks:
                if st.checkbox(f"{stock}", key=f"hk_{stock}"):
                    stock_codes.append(stock)
        
        with col3:
            st.markdown("**ETF示例:**")
            etf_stocks = STOCK_CODE_EXAMPLES.get("ETF", [])
            for stock in etf_stocks:
                if st.checkbox(f"{stock}", key=f"etf_{stock}"):
                    stock_codes.append(stock)
    
    else:  # 从文件导入
        uploaded_file = st.file_uploader(
            "上传股票代码文件",
            type=['txt', 'csv'],
            help="支持txt文件(每行一个代码)或csv文件(包含code列)"
        )
        
        if uploaded_file:
            try:
                if uploaded_file.name.endswith('.csv'):
                    df = pd.read_csv(uploaded_file)
                    if 'code' in df.columns:
                        stock_codes = df['code'].astype(str).tolist()
                    else:
                        st.error("CSV文件必须包含'code'列")
                else:
                    content = uploaded_file.read().decode('utf-8')
                    stock_codes = [code.strip() for code in content.split('\n') if code.strip()]
            except Exception as e:
                st.error(f"文件解析失败: {str(e)}")
    
    # 显示已选择的股票
    if stock_codes:
        st.success(f"✅ 已选择 {len(stock_codes)} 只股票")
        with st.expander("查看股票列表"):
            df_codes = pd.DataFrame({'股票代码': stock_codes})
            st.dataframe(df_codes, use_container_width=True)
    
    st.markdown("---")
    
    # 分析类型配置
    st.markdown("#### 🔍 分析类型")
    
    col1, col2 = st.columns(2)
    
    with col1:
        analysis_types = []
        if st.checkbox("📊 基本面分析", value=True, help="获取股票基本信息、财务数据等"):
            analysis_types.append("basic")
        if st.checkbox("📈 技术面分析", value=True, help="K线数据、技术指标、趋势分析等"):
            analysis_types.append("technical")
    
    with col2:
        if st.checkbox("📰 新闻面分析", value=False, help="相关新闻资讯分析"):
            analysis_types.append("news")
        if st.checkbox("🎯 筹码面分析", value=False, help="筹码分布、成本分析等"):
            analysis_types.append("chip")
    
    if st.checkbox("🤖 综合分析", value=True, help="AI智能综合分析，整合多维度信息"):
        analysis_types.append("comprehensive")
    
    st.markdown("---")
    
    # 高级配置
    st.markdown("#### ⚙️ 高级配置")
    
    col1, col2 = st.columns(2)
    
    with col1:
        use_cache = st.checkbox("💾 使用缓存数据", value=True, help="使用缓存数据可以加快分析速度")
        force_refresh = st.checkbox("🔄 强制刷新", value=False, help="忽略缓存，强制获取最新数据")
        include_ai_analysis = st.checkbox("🤖 启用AI分析", value=True, help="使用AI进行智能分析")
    
    with col2:
        max_workers = st.slider("并发线程数", min_value=1, max_value=10, value=3, help="同时分析的股票数量")
        max_retry = st.slider("最大重试次数", min_value=1, max_value=5, value=2, help="分析失败时的重试次数")
    
    # 用户观点配置
    if include_ai_analysis:
        st.markdown("#### 💭 用户观点 (可选)")
        user_opinion = st.text_area(
            "补充观点:",
            placeholder="请输入您对这些股票的观点、看法或关注的重点...",
            help="输入您的投资观点，AI将结合多维度分析给出综合建议",
            height=100
        )
        
        user_position = st.selectbox(
            "当前持仓状态:",
            options=["不确定", "空仓", "低仓位", "中仓位", "重仓", "满仓"],
            index=0,
            help="请选择您当前的大致持仓状态"
        )
    else:
        user_opinion = ""
        user_position = "不确定"
    
    # 保存配置到session state
    if st.button("💾 保存配置", type="primary"):
        if not stock_codes:
            st.error("请至少选择一只股票")
        elif not analysis_types:
            st.error("请至少选择一种分析类型")
        else:
            config = BatchAnalysisConfig(
                stock_codes=stock_codes,
                analysis_types=analysis_types,
                use_cache=use_cache,
                force_refresh=force_refresh,
                include_ai_analysis=include_ai_analysis,
                max_workers=max_workers,
                max_retry=max_retry,
                user_opinion=user_opinion,
                user_position=user_position,
                output_dir=f"./batch_analysis_results/{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                save_individual_reports=True,
                save_summary_report=True
            )
            
            st.session_state.batch_analysis_config = config
            st.success("✅ 配置已保存！请切换到'执行分析'标签页开始分析")
            st.rerun()


def display_analysis_execution():
    """显示分析执行界面"""
    st.subheader("🚀 执行分析")
    
    # 检查是否有保存的配置
    if 'batch_analysis_config' not in st.session_state:
        st.warning("⚠️ 请先在'配置分析'标签页中配置并保存分析参数")
        return
    
    config = st.session_state.batch_analysis_config
    
    # 显示配置摘要
    st.markdown("#### 📋 当前配置")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("股票数量", len(config.stock_codes))
        st.metric("分析类型", len(config.analysis_types))
    
    with col2:
        st.metric("并发线程", config.max_workers)
        st.metric("AI分析", "启用" if config.include_ai_analysis else "禁用")
    
    with col3:
        st.metric("使用缓存", "是" if config.use_cache else "否")
        st.metric("强制刷新", "是" if config.force_refresh else "否")
    
    # 显示股票列表
    with st.expander("查看股票列表"):
        df_codes = pd.DataFrame({'股票代码': config.stock_codes})
        st.dataframe(df_codes, use_container_width=True)
    
    # 显示分析类型
    with st.expander("查看分析类型"):
        type_names = {
            'basic': '📊 基本面分析',
            'technical': '📈 技术面分析', 
            'news': '📰 新闻面分析',
            'chip': '🎯 筹码面分析',
            'comprehensive': '🤖 综合分析'
        }
        selected_types = [type_names.get(t, t) for t in config.analysis_types]
        st.write("、".join(selected_types))
    
    st.markdown("---")
    
    # 执行分析按钮
    if st.button("🚀 开始批量分析", type="primary", use_container_width=True):
        if 'batch_analysis_running' not in st.session_state:
            st.session_state.batch_analysis_running = False
        
        if not st.session_state.batch_analysis_running:
            st.session_state.batch_analysis_running = True
            st.session_state.batch_analysis_result = None
            
            # 创建进度条和状态显示
            progress_bar = st.progress(0)
            status_text = st.empty()
            results_container = st.empty()
            
            try:
                # 执行批量分析
                analyzer = BatchStockAnalyzer()
                
                # 模拟进度更新（实际进度在analyzer内部处理）
                status_text.text("🔄 正在初始化分析器...")
                progress_bar.progress(0.1)
                
                status_text.text("📊 开始批量分析...")
                progress_bar.progress(0.2)
                
                # 执行分析
                result = analyzer.batch_analyze(config)
                
                # 保存结果
                st.session_state.batch_analysis_result = result
                st.session_state.batch_analysis_running = False
                
                # 更新进度
                progress_bar.progress(1.0)
                status_text.text("✅ 批量分析完成！")
                
                # 显示结果摘要
                with results_container.container():
                    st.success("🎉 批量分析完成！")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("总耗时", f"{result.total_duration:.1f}秒")
                    with col2:
                        st.metric("成功数量", result.success_count)
                    with col3:
                        st.metric("失败数量", result.failed_count)
                    with col4:
                        success_rate = (result.success_count / len(result.results)) * 100 if result.results else 0
                        st.metric("成功率", f"{success_rate:.1f}%")
                    
                    st.info(f"📁 结果已保存到: {config.output_dir}")
                
                st.rerun()
                
            except Exception as e:
                st.session_state.batch_analysis_running = False
                st.error(f"❌ 批量分析失败: {str(e)}")
                progress_bar.progress(0)
                status_text.text("❌ 分析失败")
        else:
            st.warning("⚠️ 分析正在进行中，请稍候...")


def display_analysis_results():
    """显示分析结果"""
    st.subheader("📊 分析结果")
    
    if 'batch_analysis_result' not in st.session_state:
        st.info("💡 请先执行批量分析，结果将在此处显示")
        return
    
    result = st.session_state.batch_analysis_result
    
    # 结果概览
    st.markdown("#### 📈 结果概览")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("分析股票数", len(result.results))
    with col2:
        st.metric("成功数量", result.success_count)
    with col3:
        st.metric("失败数量", result.failed_count)
    with col4:
        success_rate = (result.success_count / len(result.results)) * 100 if result.results else 0
        st.metric("成功率", f"{success_rate:.1f}%")
    
    # 时间信息
    col1, col2 = st.columns(2)
    with col1:
        st.metric("开始时间", result.start_time)
    with col2:
        st.metric("结束时间", result.end_time)
    
    st.metric("总耗时", f"{result.total_duration:.2f}秒")
    
    st.markdown("---")
    
    # 详细结果表格
    st.markdown("#### 📋 详细结果")
    
    # 准备表格数据
    table_data = []
    for stock_result in result.results:
        row = {
            '股票代码': stock_result.stock_code,
            '股票名称': stock_result.stock_name,
            '分析状态': stock_result.status,
            '当前价格': stock_result.summary.get('current_price', 0) if stock_result.summary else 0,
            '涨跌幅(%)': stock_result.summary.get('change_percent', 0) if stock_result.summary else 0,
            '行业': stock_result.summary.get('industry', '') if stock_result.summary else '',
            '技术趋势': stock_result.summary.get('technical_trend', '') if stock_result.summary else '',
            'RSI水平': stock_result.summary.get('rsi_level', '') if stock_result.summary else '',
            '新闻数量': stock_result.summary.get('news_count', 0) if stock_result.summary else 0,
            '分析完成数': stock_result.summary.get('analysis_count', 0) if stock_result.summary else 0,
            '包含AI分析': '是' if stock_result.summary and stock_result.summary.get('has_ai_analysis') else '否',
            '错误信息': stock_result.error_message or '',
            '分析时间': stock_result.analysis_time or ''
        }
        table_data.append(row)
    
    if table_data:
        df_results = pd.DataFrame(table_data)
        
        # 添加筛选功能
        col1, col2 = st.columns(2)
        with col1:
            status_filter = st.selectbox("按状态筛选:", ["全部", "success", "failed", "partial"])
        with col2:
            industry_filter = st.selectbox("按行业筛选:", ["全部"] + list(df_results['行业'].unique()))
        
        # 应用筛选
        filtered_df = df_results.copy()
        if status_filter != "全部":
            filtered_df = filtered_df[filtered_df['分析状态'] == status_filter]
        if industry_filter != "全部":
            filtered_df = filtered_df[filtered_df['行业'] == industry_filter]
        
        st.dataframe(filtered_df, use_container_width=True)
        
        # 下载按钮
        csv_data = filtered_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 下载结果CSV",
            data=csv_data,
            file_name=f"batch_analysis_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    st.markdown("---")
    
    # 统计图表
    st.markdown("#### 📊 统计分析")
    
    if result.summary_stats:
        col1, col2 = st.columns(2)
        
        with col1:
            # 行业分布
            if result.summary_stats.get('industry_distribution'):
                st.markdown("**行业分布:**")
                industry_data = result.summary_stats['industry_distribution']
                df_industry = pd.DataFrame(list(industry_data.items()), columns=['行业', '数量'])
                st.bar_chart(df_industry.set_index('行业'))
        
        with col2:
            # 价格区间分布
            if result.summary_stats.get('price_ranges'):
                st.markdown("**价格区间分布:**")
                price_data = result.summary_stats['price_ranges']
                df_price = pd.DataFrame(list(price_data.items()), columns=['价格区间', '数量'])
                st.bar_chart(df_price.set_index('价格区间'))
    
    # 查看详细报告
    st.markdown("#### 📄 详细报告")
    
    if st.button("📁 打开结果目录"):
        result_dir = result.config.output_dir
        if os.path.exists(result_dir):
            st.info(f"结果目录: {result_dir}")
            # 列出文件
            files = os.listdir(result_dir)
            if files:
                st.write("包含文件:")
                for file in files:
                    st.write(f"- {file}")
        else:
            st.error("结果目录不存在")


def display_analysis_history():
    """显示分析历史记录"""
    st.subheader("📁 历史记录")
    
    # 查找历史分析结果目录
    base_dir = "./batch_analysis_results"
    if not os.path.exists(base_dir):
        st.info("📂 暂无历史分析记录")
        return
    
    # 获取所有历史目录
    history_dirs = []
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path):
            history_dirs.append(item)
    
    if not history_dirs:
        st.info("📂 暂无历史分析记录")
        return
    
    # 按时间排序
    history_dirs.sort(reverse=True)
    
    st.markdown(f"#### 📋 历史分析记录 (共 {len(history_dirs)} 条)")
    
    # 显示历史记录列表
    for i, dir_name in enumerate(history_dirs[:10]):  # 只显示最近10条
        dir_path = os.path.join(base_dir, dir_name)
        
        col1, col2, col3 = st.columns([3, 2, 1])
        
        with col1:
            st.write(f"**{i+1}. {dir_name}**")
        
        with col2:
            # 尝试读取汇总文件
            summary_files = [f for f in os.listdir(dir_path) if f.startswith('batch_analysis_summary_')]
            if summary_files:
                st.write("📊 有汇总报告")
            else:
                st.write("📄 无汇总报告")
        
        with col3:
            if st.button("查看", key=f"view_{i}"):
                # 显示该次分析的详细信息
                display_history_detail(dir_path, dir_name)


def display_history_detail(dir_path: str, dir_name: str):
    """显示历史分析详情"""
    st.markdown(f"#### 📊 {dir_name} 分析详情")
    
    # 查找汇总文件
    summary_files = [f for f in os.listdir(dir_path) if f.startswith('batch_analysis_summary_')]
    detailed_files = [f for f in os.listdir(dir_path) if f.startswith('batch_analysis_detailed_')]
    
    if summary_files:
        summary_file = os.path.join(dir_path, summary_files[0])
        try:
            df = pd.read_csv(summary_file)
            st.dataframe(df, use_container_width=True)
            
            # 下载按钮
            csv_data = df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 下载历史结果",
                data=csv_data,
                file_name=f"historical_{dir_name}.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error(f"读取汇总文件失败: {str(e)}")
    
    if detailed_files:
        detailed_file = os.path.join(dir_path, detailed_files[0])
        try:
            with open(detailed_file, 'r', encoding='utf-8') as f:
                detailed_data = json.load(f)
            
            # 显示批次信息
            batch_info = detailed_data.get('batch_info', {})
            if batch_info:
                st.markdown("**批次信息:**")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("成功数量", batch_info.get('success_count', 0))
                with col2:
                    st.metric("失败数量", batch_info.get('failed_count', 0))
                with col3:
                    st.metric("总耗时", f"{batch_info.get('total_duration', 0):.1f}秒")
                with col4:
                    success_count = batch_info.get('success_count', 0)
                    total_count = success_count + batch_info.get('failed_count', 0)
                    success_rate = (success_count / total_count * 100) if total_count > 0 else 0
                    st.metric("成功率", f"{success_rate:.1f}%")
        except Exception as e:
            st.error(f"读取详细文件失败: {str(e)}")
    
    # 列出所有文件
    st.markdown("**包含文件:**")
    files = os.listdir(dir_path)
    for file in files:
        file_path = os.path.join(dir_path, file)
        file_size = os.path.getsize(file_path)
        st.write(f"- {file} ({file_size} bytes)")


if __name__ == "__main__":
    display_batch_analysis_page()
