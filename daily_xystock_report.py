import os
import time
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd
from tqdm import tqdm
from xystock import stock

# ======================
# 配置区域
# ======================

# 股票代码（可换成从文件读取）
STOCK_LIST = [
    "600519",  # 贵州茅台
    "000001",  # 平安银行
    "300750",  # 宁德时代
    "601318",  # 中国平安
    "002594",  # 比亚迪
]

BASE_DIR = "./analysis_results"
MAX_RETRY = 3
MAX_WORKERS = 5  # 并发线程数


# ======================
# 工具函数
# ======================

def get_today_dir():
    """生成今日报告目录"""
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    save_dir = os.path.join(BASE_DIR, today_str)
    os.makedirs(save_dir, exist_ok=True)
    return save_dir


def analyze_stock(code, save_dir):
    """分析单只股票并保存报告"""
    s = stock.Stock()
    for attempt in range(1, MAX_RETRY + 1):
        try:
            s.load(code)
            s.run()
            save_path = os.path.join(save_dir, f"{code}.html")
            s.save(save_path)
            return {"code": code, "status": "success", "path": save_path}
        except Exception as e:
            if attempt < MAX_RETRY:
                time.sleep(1)
                continue
            return {"code": code, "status": "failed", "error": str(e)}


def batch_analyze():
    """批量分析所有股票"""
    save_dir = get_today_dir()
    print(f"\n📅 今日目录：{save_dir}")
    print(f"📊 开始并行分析 {len(STOCK_LIST)} 只股票（{MAX_WORKERS} 个线程）...\n")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(analyze_stock, code, save_dir): code for code in STOCK_LIST}
        for future in tqdm(as_completed(futures), total=len(futures), desc="分析进度", unit="stock"):
            results.append(future.result())

    # 汇总结果
    summary_path = os.path.join(save_dir, "summary.csv")
    df = pd.DataFrame(results)
    df.to_csv(summary_path, index=False, encoding="utf-8-sig")

    print("\n✅ 批量分析完成！结果汇总：\n")
    for r in results:
        if r["status"] == "success":
            print(f"✔️ {r['code']} 分析完成 -> {r['path']}")
        else:
            print(f"❌ {r['code']} 失败：{r['error']}")

    print(f"\n📁 今日报告目录: {save_dir}")
    print(f"📈 汇总结果文件: {summary_path}\n")
    return summary_path


if __name__ == "__main__":
    batch_analyze()
