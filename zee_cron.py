import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

BASE_URL = "https://api.zee-verse.com"
WATCH_LIST = {
    "2100920016": "Snorker",
    "2100920004": "Glooper",
    "2101020001": "Energy Potion"
}

# 从 GitHub Actions 环境变量中读取账号密码
EMAIL = os.getenv("ZEE_EMAIL")
PASSWORD = os.getenv("ZEE_PASSWORD")

def get_automated_token():
    """自动化登录并获取最新的 Token"""
    if not EMAIL or not PASSWORD:
        print("❌ 错误: 未在 GitHub Secrets 中配置 ZEE_EMAIL 或 ZEE_PASSWORD")
        return None
        
    url = f"{BASE_URL}/v2/account/login"
    payload = {"email": EMAIL, "password": PASSWORD}
    
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 200:
            token = response.json().get("accessToken")
            print("✅ 自动化登录成功，已获取最新 Token！")
            return token
        else:
            print(f"❌ 登录失败，状态码: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ 登录时发生异常: {e}")
        return None

def fetch_8h_data(item_id, token):
    """获取最近 8 小时的数据并聚合"""
    url = f"{BASE_URL}/v2/offchain-gex/items/{item_id}/candles?interval=1h"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200: 
            print(f"❌ 抓取道具 {item_id} 失败，状态码: {response.status_code}")
            return None
        
        df = pd.DataFrame(response.json())
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        for col in ['open', 'high', 'low', 'close', 'volumeVee']:
            df[col] = df[col].astype(float) / 1e18 # 标准 18 位 decimals 换算

        df_8h = df.head(8) # 获取最近 8 小时
        if df_8h.empty: return None

        return {
            "open": df_8h['open'].iloc[-1],
            "close": df_8h['close'].iloc[0],
            "high": df_8h['high'].max(),
            "low": df_8h['low'].min(),
            "volume": df_8h['volumeVee'].sum(),
            "change_pct": ((df_8h['close'].iloc[0] - df_8h['open'].iloc[-1]) / df_8h['open'].iloc[-1]) * 100
        }
    except Exception as e:
        print(f"❌ 数据获取异常: {e}")
        return None

def generate_dashboard():
    # 1. 先去登录拿 Token
    token = get_automated_token()
    if not token:
        print("❌ 无法获取 Token，程序终止。")
        return

    names, prices, changes, colors = [], [], [], []

    # 2. 循环获取数据
    for item_id, item_name in WATCH_LIST.items():
        stats = fetch_8h_data(item_id, token)
        if stats:
            names.append(item_name)
            prices.append(stats['close'])
            changes.append(stats['change_pct'])
            colors.append('#ff4d4f' if stats['change_pct'] >= 0 else '#52c41a') # 红涨绿跌

    if not names:
        print("⚠️ 没有成功抓取到任何数据！")
        return

    # 3. 绘图
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(names, changes, color=colors, width=0.4)
    
    for bar, price, change in zip(bars, prices, changes):
        yval = bar.get_height()
        text_y = yval + 0.5 if yval >= 0 else yval - 1.5
        ax.text(bar.get_x() + bar.get_width()/2, text_y, f"{price:.2f} VEE\n({change:+.2f}%)", ha='center', va='center', fontweight='bold')

    ax.axhline(0, color='black', linewidth=0.8)
    ax.set_title(f"Zeeverse 8H GEX Board ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    ax.set_ylabel("Change %")
    plt.tight_layout()
    plt.savefig("latest_dashboard.png")
    print("🎉 看板生成完毕！图片已保存。")

if __name__ == "__main__":
    generate_dashboard()
