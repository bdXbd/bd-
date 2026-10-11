import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import time
import warnings
import os

warnings.filterwarnings("ignore")

# ─── 網頁基本設定 ───
# 這裡加上了 V4.2 版本號，用來確認有沒有更新成功
st.set_page_config(page_title="SMC 狙擊雷達 V4.2", page_icon="🎯", layout="wide")
st.title("🎯 4H 全市場 SMC 狙擊雷達 V4.2")
st.markdown("精準捕捉 **OB 訂單塊回踩** 與 **WaveTrend 恐慌轉折**。支援美股、台股與加密貨幣。")

# ─── 記憶功能：讀取與儲存收藏名單 ───
FAV_FILE = "favorites.txt"
DEFAULT_FAVS = "SPY, QQQ, NVDA, TSLA, 2330.TW, 0050.TW, BTC-USD, BZ=F, ^TWII, NQ=F"

def load_favorites():
    if os.path.exists(FAV_FILE):
        with open(FAV_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content: return content
    return DEFAULT_FAVS

def save_favorites(fav_str):
    with open(FAV_FILE, "w", encoding="utf-8") as f:
        f.write(fav_str)

# ─── 核心運算函數 ───
@st.cache_data(ttl=3600)
def get_us_indices():
    def fetch_wiki(url):
        try:
            storage_options = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            dfs = pd.read_html(url, storage_options=storage_options)
            for df in dfs:
                if 'Symbol' in df.columns: return df['Symbol'].str.replace('.', '-', regex=False).tolist()
                if 'Ticker' in df.columns: return df['Ticker'].str.replace('.', '-', regex=False).tolist()
        except Exception:
            pass
        return []
    
    sp500 = fetch_wiki("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    ndx   = fetch_wiki("https://en.wikipedia.org/wiki/Nasdaq-100")
    sox   = fetch_wiki("https://en.wikipedia.org/wiki/PHLX_Semiconductor_Sector")
    
    combined = list(dict.fromkeys([t for t in (sp500 + ndx + sox) if isinstance(t, str) and len(t) <= 7]))
    
    if len(combined) < 100:
        backup = [
            "SPY", "QQQ", "DIA", "IWM", "SOXX", "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", 
            "AMD", "WDC", "MU", "AVGO", "SMCI", "INTC", "QCOM", "TSM", "ASML", "ARM", "NVO",
            "PLTR", "MSTR", "COIN", "MARA", "DJT", "SPCE", "RDDT", "HOOD", "SNOW",
            "CEG", "VST", "NEE", "IONQ", "RKLB", "ASTS", "BTC-USD", "ETH-USD", "SOL-USD"
        ]
        return backup, False 
    return combined, True 

def rma(series, length): return series.ewm(alpha=1.0/length, adjust=False).mean()

def resample_to_tv_4h(df_1h):
    df = df_1h.copy()
    if df.index.tz is not None: df.index = df.index.tz_convert('America/New_York')
    else: df.index = pd.to_datetime(df.index).tz_localize('UTC').tz_convert('America/New_York')
    date_group = df.index.date
    session_group = np.where(df.index.hour < 13, 0, 1)
    df_4h = df.groupby([date_group, session_group]).agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'}).dropna()
    df_4h.index = [pd.Timestamp(f"{d} {'09:30' if s==0 else '13:30'}").tz_localize('America/New_York') for d, s in df_4h.index]
    return df_4h.sort_index()

def scan_4h_signals(df, recent_k):
    if df is None or len(df) < 40: return None
    close, high, low, open_p = df['Close'], df['High'], df['Low'], df['Open']
    n = len(df)

    h_close_22 = close.rolling(window=22).max()
    wvf = ((h_close_22 - low) / h_close_22) * 100.0
    wvf_avg, wvf_std = wvf.rolling(20).mean(), wvf.rolling(20).std(ddof=0)
    wvf_ext = (wvf >= wvf_avg + 2.0 * wvf_std) | (wvf >= wvf.rolling(50).max() * 0.85)

    diff = close.diff().fillna(0)
    pos_diff, neg_diff =
