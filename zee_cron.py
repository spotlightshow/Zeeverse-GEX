import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

BASE_URL = "https://api.zee-verse.com"
WATCH_LIST = {
    "2100920016": "Snorker",
    "2100920004": "Glooper",
    "2101020001": "Energy Potion"
}
TOKEN = "你的_ACCESS_TOKEN" # 建议挂载为 GitHub Secrets（见下文安全提示）

def get_headers():
    return {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}

def fetch_8h_data(item_id):
    url = f"{BASE_URL}/v2/offchain-gex/items/{item_id}/candles?interval=1h"
    try:
        response = requests.get(url, headers=get_headers())
        if response.status_code != 200: return None
        
        df = pd.DataFrame(response.json())
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        for col in ['open', 'high', 'low', 'close', 'volumeVee']:
            df[col] = df[col].astype(float) / 1e18 # 18位小数转换

        df_8h = df.head(8) # 截取 8 小时
        if df_8h.empty: return None

        return {
            "open": df_8h['open'].iloc[-1],
            "close": df_8h['close'].iloc[0],
            "high": df_8h['high'].max(),
            "low": df_8h['low'].min(),
            "volume": df_8h['volumeVee'].sum(),
            "change_pct": ((df_8h['close'].iloc[0] - df_8h['open'].iloc[-1]) / df_8h['open'].iloc[-1]) * 100
        }
    except:
        return None

def generate_dashboard():
    names, prices, changes, colors = [], [], [], []

    for item_id, item_name in WATCH_LIST.items():
        stats = fetch_8h_data(item_id)
        if stats:
            names.append(item_name)
            prices.append(stats['close'])
            changes.append(stats['change_pct'])
            colors.append('#ff4d4f' if stats['change_pct'] >= 0 else '#52c41a') # 红涨绿跌

    if not names: return

    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.bar(names, changes, color=colors, width=0.4)
    
    for bar, price, change in zip(bars, prices, changes):
        yval = bar.get_height()
        text_y = yval + 0.5 if yval >= 0 else yval - 1.5
        ax.text(bar.get_x() + bar.get_width()/2, text_y, f"{price:.2f} VEE\n({change:+.2f}%)", ha='center', va='center')

    ax.axhline(0, color='black', linewidth=0.8)
    ax.set_title(f"Zeeverse 8H GEX Board ({datetime.now().strftime('%Y-%m-%d %H:%M')})")
    plt.tight_layout()
    plt.savefig("latest_dashboard.png") # 每次覆盖最新一张图，方便推流

if __name__ == "__main__":
    generate_dashboard()
