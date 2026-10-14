import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import warnings
import os
import json

warnings.filterwarnings("ignore")

# ════════════════════════════════════════════════════════════════════════════
# 網頁基本設定與自訂 CSS 美化
# ════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="bd の 超級指標(∠·ω< )⌒★ 量化雷達終端 V7.1",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(
    "<style>"
    ".baro-card { background: linear-gradient(145deg, rgba(30,34,45,0.96), rgba(18,21,28,0.96)); border: 1px solid rgba(255,255,255,0.08); border-radius: 12px; padding: 14px 15px; margin-bottom: 10px; box-shadow: 0 4px 16px rgba(0,0,0,0.3); color: #e0e3eb; }"
    ".baro-bull { border-left: 5px solid #00e676; }"
    ".baro-bear { border-left: 5px solid #ff5252; }"
    ".baro-warn { border-left: 5px solid #ffca28; }"
    ".baro-title { font-size: 1.08rem; font-weight: 800; display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }"
    ".baro-price { font-size: 0.92rem; font-family: monospace; color: #00e5ff; }"
    ".baro-badge { display: inline-block; padding: 3px 8px; border-radius: 6px; font-size: 0.80rem; font-weight: 700; margin-bottom: 6px; }"
    ".badge-bull { background: rgba(0, 230, 118, 0.18); color: #00e676; border: 1px solid rgba(0,230,118,0.4); }"
    ".badge-bear { background: rgba(255, 82, 82, 0.18); color: #ff5252; border: 1px solid rgba(255,82,82,0.4); }"
    ".badge-warn { background: rgba(255, 202, 40, 0.18); color: #ffca28; border: 1px solid rgba(255,202,40,0.4); }"
    ".baro-advice { font-size: 0.85rem; font-weight: 700; color: #ffffff; margin-bottom: 6px; }"
    ".baro-sub { font-size: 0.75rem; color: #9ba2b0; line-height: 1.48; }"
    ".metric-pill { background: rgba(255,255,255,0.07); padding: 1px 6px; border-radius: 4px; font-family: monospace; color: #ffd600; }"
    "</style>",
    unsafe_allow_html=True
)

st.title("🎯 bd の 超級指標(∠·ω< )⌒★ 量化雷達終端 V7.1")
st.caption("100% 鏡像同步 TradingView V3.8 指標：搭載 **24 態纏論×SMC 大盤風向標 (含近14K動能修正 & 近2K準備抄底警報)** × **OB 共振重疊** × **纏論中樞延伸/共振確認** × **自動風控 (SL/TP)**")

# ════════════════════════════════════════════════════════════════════════════
# 訊號清單與預設戰術組合定義
# ════════════════════════════════════════════════════════════════════════════
CONFIG_FILE = "scanner_config.json"
FAV_FILE = "favorites.txt"

ALL_SIG_TYPES = [
    # 結構回踩與共振確認 (核心右側訊號)
    "🌟【中樞共振 Buy】", "🌟【中樞共振 Sell】",
    "🟪【OB共振支撐】", "🟪【OB共振壓力】",
    "🟠【中樞 Buy】", "🟠【中樞 Sell】",
    "🟩【OB支撐確認】", "🟥【OB壓力確認】",
    # WaveTrend 動能與抄底逃頂
    "🟢【恐慌抄底】", "🟡【Market Bottom】", "🟣【極度超賣】", "🟪【超賣預警】",
    "⚠️【頂部預警】", "🟠【WT 死叉】", "🟡【超買預警】",
    # 反轉陷阱通道
    "🛡️【空頭陷阱】", "⚠️【多頭陷阱】",
    # SMC 結構突破與纏論買賣點
    "🟢【多頭 CHOCH】", "🟢【多頭 BOS】", "🔴【空頭 CHOCH】", "🔴【空頭 BOS】",
    "💠【纏論買點】", "💠【纏論賣點】"
]

PRESET_FILTERS = {
    "🔥 全部訊號 (預設全開)": ALL_SIG_TYPES,
    "💎 右側回踩做多 (中樞/共振/OB支撐 + Market Bottom)": [
        "🌟【中樞共振 Buy】", "🟪【OB共振支撐】", "🟠【中樞 Buy】", "🟩【OB支撐確認】", "🟡【Market Bottom】"
    ],
    "🌟 頂級共振狙擊 (僅看中樞共振 + OB共振)": [
        "🌟【中樞共振 Buy】", "🌟【中樞共振 Sell】", "🟪【OB共振支撐】", "🟪【OB共振壓力】"
    ],
    "🟢 左側恐慌抄底 (恐慌抄底 + 極度超賣 + 空頭陷阱 + 纏論買點)": [
        "🟢【恐慌抄底】", "🟣【極度超賣】", "🛡️【空頭陷阱】", "🟡【Market Bottom】", "💠【纏論買點】"
    ],
    "🔴 逃頂與做空警訊 (頂部預警 + WT死叉 + 壓力受阻 + 多頭陷阱)": [
        "🌟【中樞共振 Sell】", "🟪【OB共振壓力】", "🟠【中樞 Sell】", "🟥【OB壓力確認】",
        "⚠️【頂部預警】", "🟠【WT 死叉】", "⚠️【多頭陷阱】", "💠【纏論賣點】"
    ],
    "🛠️ 自訂勾選訊號": None
}

def load_config():
    config = {
        "favorites": "SPY, QQQ, SOXX, NVDA, TSLA, AAPL, MSFT, AMD, TSM, 2330.TW, 0050.TW, 00631L.TW, ^TWII, EWT, NQ=F, BTC-USD",
        "scan_mode": "1. 僅看技術指標 (預設)",
        "max_peg": 1.0,
        "max_pe": 0.0,
        "max_pb": 0.0,
        "scan_us_indices": False,
        "selected_tf_label": "4小時K (TV標準)",
        "recent_k": 2,
        "scan_days": 90,
        "strict_confirm": False,
        "show_swing_ob": False,
        "include_chan_bs": False,
        "ob_rr": 2.0,
        "target_signals": ALL_SIG_TYPES
    }

    if os.path.exists(FAV_FILE):
        try:
            with open(FAV_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content and not content.startswith("{"):
                    config["favorites"] = content
        except Exception:
            pass

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved_config = json.load(f)
                config.update(saved_config)
        except Exception:
            pass

    return config

def save_config(config_dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, ensure_ascii=False, indent=4)

# ════════════════════════════════════════════════════════════════════════════
# 數據獲取與 TradingView 4H 時框精準重採樣
# ════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def get_us_indices():
    def fetch_wiki(url):
        try:
            storage_options = {'User-Agent': 'Mozilla/5.0'}
            dfs = pd.read_html(url, storage_options=storage_options)
            for df in dfs:
                if 'Symbol' in df.columns:
                    return df['Symbol'].str.replace('.', '-', regex=False).tolist()
                if 'Ticker' in df.columns:
                    return df['Ticker'].str.replace('.', '-', regex=False).tolist()
        except Exception:
            pass
        return []

    sp500 = fetch_wiki("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    ndx   = fetch_wiki("https://en.wikipedia.org/wiki/Nasdaq-100")
    sox   = fetch_wiki("https://en.wikipedia.org/wiki/PHLX_Semiconductor_Sector")
    combined = list(dict.fromkeys([t for t in (sp500 + ndx + sox) if isinstance(t, str) and len(t) <= 7]))

    if len(combined) < 100:
        backup = ["SPY", "QQQ", "DIA", "IWM", "SOXX", "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AMD", "TSM", "AVGO", "NFLX", "BTC-USD"]
        return backup, [], [], False
    return combined, ndx, sox, True

def rma(series, length):
    return series.ewm(alpha=1.0 / length, adjust=False).mean()

def resample_to_tv_4h(df_1h, ticker=""):
    df = df_1h.copy()
    t_up = str(ticker).upper()

    # 1. 加密貨幣與 24H 期貨：採用標準 UTC 4小時切分 (00, 04, 08, 12, 16, 20)
    if "-USD" in t_up or "=F" in t_up:
        if df.index.tz is not None:
            df.index = df.index.tz_convert('UTC')
        else:
            df.index = pd.to_datetime(df.index).tz_localize('UTC')
        df_4h = df.resample('4h', closed='left', label='left').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna(subset=['Close'])
        return df_4h.sort_index()

    # 2. 台股與台灣加權指數：採用台北時區上下午盤切分
    if t_up.endswith(".TW") or t_up.endswith(".TWO") or t_up == "^TWII":
        if df.index.tz is not None:
            df.index = df.index.tz_convert('Asia/Taipei')
        else:
            df.index = pd.to_datetime(df.index).tz_localize('UTC').tz_convert('Asia/Taipei')
        date_group = df.index.date
        session_group = np.where(df.index.hour < 11, 0, 1)
        df_4h = df.groupby([date_group, session_group]).agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna(subset=['Close'])
        df_4h.index = [pd.Timestamp(f"{d} {'09:00' if s==0 else '11:00'}").tz_localize('Asia/Taipei') for d, s in df_4h.index]
        return df_4h.sort_index()

    # 3. 美股標準：採用紐約時區 09:30 與 13:30 兩根 4H K棒切分
    if df.index.tz is not None:
        df.index = df.index.tz_convert('America/New_York')
    else:
        df.index = pd.to_datetime(df.index).tz_localize('UTC').tz_convert('America/New_York')
    date_group = df.index.date
    session_group = np.where(df.index.hour < 13, 0, 1)
    df_4h = df.groupby([date_group, session_group]).agg({
        'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
    }).dropna(subset=['Close'])
    df_4h.index = [pd.Timestamp(f"{d} {'09:30' if s==0 else '13:30'}").tz_localize('America/New_York') for d, s in df_4h.index]
    return df_4h.sort_index()

def get_tv_link(ticker):
    t = ticker.replace("⭐ ", "").strip().upper()
    if t == "^TWII":
        return "https://www.tradingview.com/chart/?symbol=TWSE%3ATAIEX"
    if t.endswith(".TW"):
        code = t.replace(".TW", "")
        return f"https://www.tradingview.com/chart/?symbol=TWSE%3A{code}"
    if t.endswith(".TWO"):
        code = t.replace(".TWO", "")
        return f"https://www.tradingview.com/chart/?symbol=TPEX%3A{code}"
    if t == "BTC-USD":
        return "https://www.tradingview.com/chart/?symbol=BINANCE%3ABTCUSDT"
    if t.endswith("-USD"):
        coin = t.replace("-USD", "")
        return f"https://www.tradingview.com/chart/?symbol=BINANCE%3A{coin}USDT"
    return f"https://www.tradingview.com/chart/?symbol={t}"

def pct_str(target_px, base_px):
    if base_px == 0 or pd.isna(base_px) or pd.isna(target_px):
        return "0.00%"
    pct = ((target_px - base_px) / base_px) * 100.0
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.2f}%"

# ════════════════════════════════════════════════════════════════════════════
# 纏論核心引擎 (100% 鏡像移植 Pine Script 第二部分)
# ════════════════════════════════════════════════════════════════════════════
def run_chan_engine(high_v, low_v, open_v, close_v, hist_v, min_gap=4):
    n = len(close_v)
    if n < 8:
        return [], [], []

    # 1. K線包含關係處理 (mkArr)
    mk_arr = []
    direction = 1
    for i in range(n):
        hi, lo = float(high_v[i]), float(low_v[i])
        if len(mk_arr) == 0:
            mk_arr.append({'high': hi, 'low': lo, 'hIdx': i, 'lIdx': i})
        else:
            last = mk_arr[-1]
            incl = (hi <= last['high'] and lo >= last['low']) or (hi >= last['high'] and lo <= last['low'])
            if incl:
                if direction > 0:
                    if hi > last['high']:
                        last['high'] = hi
                        last['hIdx'] = i
                    if lo > last['low']:
                        last['low'] = lo
                        last['lIdx'] = i
                else:
                    if hi < last['high']:
                        last['high'] = hi
                        last['hIdx'] = i
                    if lo < last['low']:
                        last['low'] = lo
                        last['lIdx'] = i
            else:
                direction = 1 if hi > last['high'] else -1
                mk_arr.append({'high': hi, 'low': lo, 'hIdx': i, 'lIdx': i})

    # 2. 頂底分型識別 (frArr)
    fr_arr = []
    if len(mk_arr) >= 3:
        for k in range(1, len(mk_arr) - 1):
            a, c, d = mk_arr[k - 1], mk_arr[k], mk_arr[k + 1]
            if c['high'] > a['high'] and c['high'] > d['high'] and c['low'] > a['low'] and c['low'] > d['low']:
                fr_arr.append({'typ': 1, 'mIdx': k, 'price': c['high'], 'pos': c['hIdx']})
            elif c['low'] < a['low'] and c['low'] < d['low'] and c['high'] < a['high'] and c['high'] < d['high']:
                fr_arr.append({'typ': -1, 'mIdx': k, 'price': c['low'], 'pos': c['lIdx']})

    # 3. 分型過濾與成筆條件 (rsArr)
    rs_arr = []
    for cur in fr_arr:
        keep = True
        while len(rs_arr) > 0:
            last_f = rs_arr[-1]
            if last_f['typ'] == cur['typ']:
                better = (cur['price'] > last_f['price']) if cur['typ'] > 0 else (cur['price'] < last_f['price'])
                if better:
                    rs_arr.pop()
                    continue
                else:
                    keep = False
                    break
            if abs(cur['mIdx'] - last_f['mIdx']) >= min_gap:
                break
            else:
                keep = False
                break
        if keep:
            rs_arr.append(cur)

    # 4. 生成筆 (biArr, 保留最近 79 筆)
    bi_arr = []
    if len(rs_arr) >= 2:
        for i in range(len(rs_arr) - 1):
            a, b = rs_arr[i], rs_arr[i + 1]
            bi_arr.append({
                'b0': a['pos'], 'p0': a['price'],
                'b1': b['pos'], 'p1': b['price'],
                'up': b['price'] > a['price'],
                'hi': max(a['price'], b['price']),
                'lo': min(a['price'], b['price'])
            })
    if len(bi_arr) > 79:
        bi_arr = bi_arr[-79:]

    # 5. 生成纏論中樞 (zsArr, 保留最近 16 個)
    zs_arr = []
    nb = len(bi_arr)
    i2 = 0
    while i2 <= nb - 3:
        b1, b2, b3 = bi_arr[i2], bi_arr[i2 + 1], bi_arr[i2 + 2]
        zg = min(b1['hi'], b2['hi'])
        zd = max(b1['lo'], b2['lo'])
        if zd < zg and b3['lo'] < zg and b3['hi'] > zd:
            en = i2 + 2
            j = i2 + 3
            while j < nb:
                bj = bi_arr[j]
                if bj['lo'] < zg and bj['hi'] > zd:
                    en = j
                    j += 1
                else:
                    break
            zs_arr.append({'ZG': zg, 'ZD': zd, 'startBi': i2, 'endBi': en, 'dir': 1 if b1['up'] else -1})
            i2 = en + 1
        else:
            i2 += 1
    if len(zs_arr) > 16:
        zs_arr = zs_arr[-16:]

    # 6. 計算一二三買賣點 (sgArr)
    def f_area(idx_a, idx_b):
        s_idx = max(0, idx_a)
        e_idx = min(n - 1, idx_b)
        if e_idx < s_idx:
            return 0.0
        return float(np.sum(np.abs(hist_v[s_idx : e_idx + 1])))

    def f_leg(zs0, ze, up_dir):
        best_a = -1.0
        best_i = -1
        for idx_bi in range(zs0, ze + 1):
            if 0 <= idx_bi < len(bi_arr):
                b = bi_arr[idx_bi]
                if b['up'] == up_dir:
                    area = f_area(b['b0'], b['b1'])
                    if area > best_a:
                        best_a = area
                        best_i = idx_bi
        return best_a, best_i

    sg_arr = []
    if len(zs_arr) >= 2:
        for k in range(1, len(zs_arr)):
            A, Cz = zs_arr[k - 1], zs_arr[k]
            if Cz['ZG'] < A['ZD']:
                aA, iA = f_leg(A['startBi'], A['endBi'], False)
                aC, iC = f_leg(Cz['startBi'], Cz['endBi'], False)
                if iA >= 0 and iC >= 0 and aC < aA * 0.9:
                    bC = bi_arr[iC]
                    sg_arr.append({'pos': bC['b1'], 'price': bC['p1'], 'isLong': True, 'label': '1買', 'cls': 1, 'refP': Cz['ZD']})
                    if iC + 2 < len(bi_arr):
                        up1, back = bi_arr[iC + 1], bi_arr[iC + 2]
                        if up1['up'] and not back['up'] and up1['p1'] > Cz['ZG'] and back['p1'] > bC['p1']:
                            sg_arr.append({'pos': back['b1'], 'price': back['p1'], 'isLong': True, 'label': '2買', 'cls': 2, 'refP': bC['p1']})
            elif Cz['ZD'] > A['ZG']:
                aA, iA = f_leg(A['startBi'], A['endBi'], True)
                aC, iC = f_leg(Cz['startBi'], Cz['endBi'], True)
                if iA >= 0 and iC >= 0 and aC < aA * 0.9:
                    bC = bi_arr[iC]
                    sg_arr.append({'pos': bC['b1'], 'price': bC['p1'], 'isLong': False, 'label': '1賣', 'cls': 1, 'refP': Cz['ZG']})
                    if iC + 2 < len(bi_arr):
                        dn1, back = bi_arr[iC + 1], bi_arr[iC + 2]
                        if not dn1['up'] and back['up'] and dn1['p1'] < Cz['ZD'] and back['p1'] < bC['p1']:
                            sg_arr.append({'pos': back['b1'], 'price': back['p1'], 'isLong': False, 'label': '2賣', 'cls': 2, 'refP': bC['p1']})

    if len(zs_arr) >= 1:
        for z in zs_arr:
            if z['endBi'] + 1 < len(bi_arr):
                brk, hold = bi_arr[z['endBi']], bi_arr[z['endBi'] + 1]
                if brk['up'] and brk['p1'] > z['ZG'] and not hold['up'] and hold['p1'] > z['ZG']:
                    sg_arr.append({'pos': hold['b1'], 'price': hold['p1'], 'isLong': True, 'label': '3買', 'cls': 3, 'refP': z['ZG']})
                elif not brk['up'] and brk['p1'] < z['ZD'] and hold['up'] and hold['p1'] < z['ZD']:
                    sg_arr.append({'pos': hold['b1'], 'price': hold['p1'], 'isLong': False, 'label': '3賣', 'cls': 3, 'refP': z['ZD']})

    # 去重與排序 (保留同位置最高級別買賣點)
    if len(sg_arr) > 1:
        dd = []
        for sg in sg_arr:
            at = -1
            for j, d in enumerate(dd):
                if d['pos'] == sg['pos'] and d['price'] == sg['price'] and d['isLong'] == sg['isLong']:
                    at = j
                    break
            if at < 0:
                dd.append(sg)
            elif sg['cls'] > dd[at]['cls']:
                dd[at] = sg
        sg_arr = sorted(dd, key=lambda x: x['pos'])[-12:]

    return bi_arr, zs_arr, sg_arr

# ════════════════════════════════════════════════════════════════════════════
# 完整技術指標掃描引擎 (100% 鏡像 Pine Script V3.8)
# ════════════════════════════════════════════════════════════════════════════
def update_active_obs(src_obs, max_obs=5, show_overlap=True):
    """鏡像 Pine Script updateActiveOrderBlocks：回傳 (共振合併後的活躍OB清單, 被共振隱藏的原OB起點集合)"""
    act_obs = []
    overlapped_origins = set()
    sz = len(src_obs)
    if sz == 0:
        return act_obs, overlapped_origins

    parsed = src_obs[:min(max_obs, sz)]
    p_sz = len(parsed)
    is_overlapped = [False] * p_sz

    if show_overlap and p_sz >= 2:
        for i in range(p_sz - 1):
            obA = parsed[i]
            for j in range(i + 1, p_sz):
                obB = parsed[j]
                if obA['bias'] == obB['bias']:
                    inter_top = min(obA['top'], obB['top'])
                    inter_bot = max(obA['bot'], obB['bot'])
                    if inter_top > inter_bot:
                        is_overlapped[i] = True
                        is_overlapped[j] = True
                        overlapped_origins.add(obA['ob_idx'])
                        overlapped_origins.add(obB['ob_idx'])
                        overlap_start = max(obA['ob_idx'], obB['ob_idx'])
                        act_obs.append({
                            'top': inter_top,
                            'bot': inter_bot,
                            'ob_idx': overlap_start,
                            'gen_i': max(obA['gen_i'], obB['gen_i']),
                            'bias': obA['bias'],
                            'is_reso': True
                        })

    for i in range(p_sz):
        if not is_overlapped[i]:
            item = parsed[i].copy()
            item['is_reso'] = False
            act_obs.append(item)

    return act_obs, overlapped_origins


def scan_signals(df, recent_k=2, strict_confirm=False, show_swing_ob=False, include_chan_bs=False, ob_rr=2.0):
    if df is None or len(df) < 40:
        return None

    # 限制在最近 1000 根 K 棒 (對齊 Pine Script global_max_bars = 1000)
    if len(df) > 1000:
        df = df.iloc[-1000:].copy()

    close_s, high_s, low_s, open_s = df['Close'], df['High'], df['Low'], df['Open']
    vol_s = df['Volume'] if 'Volume' in df.columns else pd.Series(0.0, index=df.index)

    high_v = high_s.values.astype(float)
    low_v = low_s.values.astype(float)
    close_v = close_s.values.astype(float)
    open_v = open_s.values.astype(float)
    vol_v = vol_s.values.astype(float)
    n = len(df)

    # ── 1. WVF (模擬 VIX) ──
    h_close_22 = close_s.rolling(window=22).max()
    wvf = ((h_close_22 - low_s) / h_close_22) * 100.0
    wvf_avg = wvf.rolling(20).mean()
    wvf_std = wvf.rolling(20).std(ddof=0)
    wvf_ext = (wvf >= wvf_avg + 2.0 * wvf_std) | (wvf >= wvf.rolling(50).max() * 0.85)

    # ── 2. RSI 雷達 (10 ~ 20 多週期面積引擎) ──
    diff = close_s.diff().fillna(0)
    pos_diff = diff.clip(lower=0)
    overbuy_count = pd.Series(0.0, index=df.index)
    oversell_count = pd.Series(0.0, index=df.index)
    rsi_sum = pd.Series(0.0, index=df.index)

    for l in range(10, 21):
        den = rma(diff.abs(), l).replace(0, np.nan)
        rsi_i = (100.0 * (rma(pos_diff, l) / den)).fillna(50.0)
        rsi_sum += rsi_i
        overbuy_count += (rsi_i > 70.0).astype(float)
        oversell_count += (rsi_i < 30.0).astype(float)

    N_rsi = 11.0
    avg_rsi = rsi_sum / N_rsi
    per_over = (overbuy_count / N_rsi) * 100.0
    per_under = 100.0 - (oversell_count / N_rsi) * 100.0
    buy_rsi_ma, sell_rsi_ma = np.zeros(n), np.zeros(n)
    buy_rsi_ma[0], sell_rsi_ma[0] = avg_rsi.iloc[0], avg_rsi.iloc[0]
    ob_r, os_r, avg_v = (overbuy_count / N_rsi).values, (oversell_count / N_rsi).values, avg_rsi.values

    for i in range(1, n):
        buy_rsi_ma[i] = buy_rsi_ma[i - 1] + ob_r[i] * (avg_v[i] - buy_rsi_ma[i - 1])
        sell_rsi_ma[i] = sell_rsi_ma[i - 1] + os_r[i] * (avg_v[i] - sell_rsi_ma[i - 1])

    rsi_red_below = (oversell_count > 0.0) & (per_under <= sell_rsi_ma)
    rsi_green_above = (overbuy_count > 0.0) & (per_over >= buy_rsi_ma)
    rsi_strong_green = rsi_green_above & (per_over >= 60.0)

    # ── 3. WaveTrend (10, 21, 4) ──
    wt_ap = (high_s + low_s + close_s) / 3.0
    wt_esa = wt_ap.ewm(span=10, adjust=False).mean()
    wt_d = (wt_ap - wt_esa).abs().ewm(span=10, adjust=False).mean().replace(0, 0.0001)
    wt1 = ((wt_ap - wt_esa) / (0.015 * wt_d)).ewm(span=21, adjust=False).mean()
    wt2 = wt1.rolling(4).mean()

    # ── 4. 反轉陷阱通道 (EMA 55, ATR 55 * 4.0) ──
    rt_basis = close_s.ewm(span=55, adjust=False).mean()
    tr_s = pd.concat([
        high_s - low_s,
        (high_s - close_s.shift(1)).abs(),
        (low_s - close_s.shift(1)).abs()
    ], axis=1).max(axis=1)
    rt_vola = rma(tr_s, 55)
    rt_upper = rt_basis + 4.0 * rt_vola
    rt_lower = rt_basis - 4.0 * rt_vola

    # ── 5. ATR(14)、ATR(100)、ATR(200) 與 parsedHighs/Lows ──
    wt_atr_v = rma(tr_s, 14).values
    rt_atr100_v = rma(tr_s, 100).values
    atr200_v = rma(tr_s, 200).values

    high_vol = (high_v - low_v) >= (2.0 * atr200_v)
    parsed_high = np.where(high_vol, low_v, high_v)
    parsed_low = np.where(high_vol, high_v, low_v)

    # ── 6. MACD (12, 26, 9) 供纏論背馳計算 ──
    ema12 = close_s.ewm(span=12, adjust=False).mean()
    ema26 = close_s.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    sig_line = macd_line.ewm(span=9, adjust=False).mean()
    hist_v = (macd_line - sig_line).fillna(0.0).values

    # ── 狀態追蹤變數 ──
    os_ext_trig, os_warn_trig, ob_warn_trig, wt_dead_trig = False, False, False, False
    last_ext_os_sl = np.nan
    mb_fired_in_cycle, vix_in_red_cycle = False, False
    rt_last_sig, rt_blw_cnt, rt_abv_cnt = -1000, 0, 0

    last_buy_state, last_sell_state = False, False

    # SMC 內部結構 (size=5) 與 擺動結構 (size=50)
    int_leg = np.zeros(n, dtype=int)
    sw_leg = np.zeros(n, dtype=int)
    ih_val, ih_idx, ih_crossed = np.nan, 0, True
    il_val, il_idx, il_crossed = np.nan, 0, True
    sh_val, sh_idx, sh_crossed = np.nan, 0, True
    sl_val, sl_idx, sl_crossed = np.nan, 0, True

    internal_trend = 0
    swing_trend = 0
    last_smc_tag = "BOS"

    internal_obs = []   # 最新在 index 0 (對應 Pine Script unshift)
    swing_obs = []
    active_int_obs = []
    active_sw_obs = []

    ob_buy_events = []   # 儲存 {bar_i, sig_str, parent_ob_idx, sl, tp, risk_tag}
    ob_sell_events = []
    other_events = []    # 儲存 {bar_i, sig_str, sl, tp, risk_tag}

    last_wt_ph_idx, last_wt_ph_val, last_wt_ph_price = -1, -float('inf'), -float('inf')

    for i in range(2, n):
        t_str = df.index[i].strftime('%m/%d %H:%M')
        c_val = close_v[i]
        c_p = f"{c_val:.2f}"
        cur_atr = wt_atr_v[i] if not np.isnan(wt_atr_v[i]) else (high_v[i] - low_v[i])

        # ── A. 更新 SMC 內部結構樞軸 (size = 5) 與 擺動結構樞軸 (size = 50) ──
        if i >= 5:
            h_after5 = np.max(high_v[i - 4 : i + 1])
            l_after5 = np.min(low_v[i - 4 : i + 1])
            c_leg5 = int_leg[i - 1]
            if high_v[i - 5] > h_after5:
                c_leg5 = 0
            elif low_v[i - 5] < l_after5:
                c_leg5 = 1
            int_leg[i] = c_leg5

            if int_leg[i] == 1 and int_leg[i - 1] == 0:
                il_val, il_idx, il_crossed = low_v[i - 5], i - 5, False
            elif int_leg[i] == 0 and int_leg[i - 1] == 1:
                ih_val, ih_idx, ih_crossed = high_v[i - 5], i - 5, False
        else:
            int_leg[i] = int_leg[i - 1]

        if i >= 50:
            h_after50 = np.max(high_v[i - 49 : i + 1])
            l_after50 = np.min(low_v[i - 49 : i + 1])
            c_leg50 = sw_leg[i - 1]
            if high_v[i - 50] > h_after50:
                c_leg50 = 0
            elif low_v[i - 50] < l_after50:
                c_leg50 = 1
            sw_leg[i] = c_leg50

            if sw_leg[i] == 1 and sw_leg[i - 1] == 0:
                sl_val, sl_idx, sl_crossed = low_v[i - 50], i - 50, False
            elif sw_leg[i] == 0 and sw_leg[i - 1] == 1:
                sh_val, sh_idx, sh_crossed = high_v[i - 50], i - 50, False
        else:
            sw_leg[i] = sw_leg[i - 1]

        # ── B. 檢查內部結構突破 (displayStructure(true)) ──
        if not np.isnan(ih_val) and close_v[i] > ih_val and close_v[i - 1] <= ih_val and not ih_crossed and ih_val != sh_val:
            ih_crossed = True
            is_choch = (internal_trend == -1)
            internal_trend = 1
            last_smc_tag = "CHOCH" if is_choch else "BOS"
            other_events.append({
                'bar_i': i,
                'sig_str': f"🟢【多頭 {last_smc_tag}】({t_str} 破 {ih_val:.2f})",
                'sl': ih_val - cur_atr * 1.5,
                'tp': c_val + cur_atr * 3.0,
                'risk_tag': f"結構突破 ({last_smc_tag})"
            })
            # 對齊 Pine Script storeOrdeBlock(internalHigh, true, BULLISH)：從 ih_idx 到 i 找最低 parsed_low
            s_idx = max(0, ih_idx)
            s_slice = parsed_low[s_idx : i]
            if len(s_slice) > 0:
                p_idx = s_idx + int(np.argmin(s_slice))
                internal_obs.insert(0, {
                    'top': float(parsed_high[p_idx]),
                    'bot': float(parsed_low[p_idx]),
                    'ob_idx': p_idx,
                    'gen_i': i,
                    'bias': 1
                })
                if len(internal_obs) > 100:
                    internal_obs.pop()

        if not np.isnan(il_val) and close_v[i] < il_val and close_v[i - 1] >= il_val and not il_crossed and il_val != sl_val:
            il_crossed = True
            is_choch = (internal_trend == 1)
            internal_trend = -1
            last_smc_tag = "CHOCH" if is_choch else "BOS"
            other_events.append({
                'bar_i': i,
                'sig_str': f"🔴【空頭 {last_smc_tag}】({t_str} 破 {il_val:.2f})",
                'sl': il_val + cur_atr * 1.5,
                'tp': c_val - cur_atr * 3.0,
                'risk_tag': f"結構跌破 ({last_smc_tag})"
            })
            # 對齊 Pine Script storeOrdeBlock(internalLow, true, BEARISH)：從 il_idx 到 i 找最高 parsed_high
            s_idx = max(0, il_idx)
            s_slice = parsed_high[s_idx : i]
            if len(s_slice) > 0:
                p_idx = s_idx + int(np.argmax(s_slice))
                internal_obs.insert(0, {
                    'top': float(parsed_high[p_idx]),
                    'bot': float(parsed_low[p_idx]),
                    'ob_idx': p_idx,
                    'gen_i': i,
                    'bias': -1
                })
                if len(internal_obs) > 100:
                    internal_obs.pop()

        # ── B2. 檢查擺動結構突破 (displayStructure(false)) ──
        if not np.isnan(sh_val) and close_v[i] > sh_val and close_v[i - 1] <= sh_val and not sh_crossed:
            sh_crossed = True
            swing_trend = 1
            if show_swing_ob:
                s_idx = max(0, sh_idx)
                s_slice = parsed_low[s_idx : i]
                if len(s_slice) > 0:
                    p_idx = s_idx + int(np.argmin(s_slice))
                    swing_obs.insert(0, {
                        'top': float(parsed_high[p_idx]),
                        'bot': float(parsed_low[p_idx]),
                        'ob_idx': p_idx,
                        'gen_i': i,
                        'bias': 1
                    })
                    if len(swing_obs) > 100:
                        swing_obs.pop()

        if not np.isnan(sl_val) and close_v[i] < sl_val and close_v[i - 1] >= sl_val and not sl_crossed:
            sl_crossed = True
            swing_trend = -1
            if show_swing_ob:
                s_idx = max(0, sl_idx)
                s_slice = parsed_high[s_idx : i]
                if len(s_slice) > 0:
                    p_idx = s_idx + int(np.argmax(s_slice))
                    swing_obs.insert(0, {
                        'top': float(parsed_high[p_idx]),
                        'bot': float(parsed_low[p_idx]),
                        'ob_idx': p_idx,
                        'gen_i': i,
                        'bias': -1
                    })
                    if len(swing_obs) > 100:
                        swing_obs.pop()

        # ── C. 剃除已失效的 OB (deleteOrderBlocks - HIGHLOW 模式) ──
        internal_obs = [
            ob for ob in internal_obs
            if not ((ob['bias'] == -1 and high_v[i] > ob['top']) or (ob['bias'] == 1 and low_v[i] < ob['bot']))
        ]
        if show_swing_ob:
            swing_obs = [
                ob for ob in swing_obs
                if not ((ob['bias'] == -1 and high_v[i] > ob['top']) or (ob['bias'] == 1 and low_v[i] < ob['bot']))
            ]

        # ── D. 更新當前有效 OB 與共振重疊 OB (updateActiveOrderBlocks) ──
        active_int_obs, _ = update_active_obs(internal_obs, max_obs=5, show_overlap=True)
        if show_swing_ob:
            active_sw_obs, _ = update_active_obs(swing_obs, max_obs=5, show_overlap=True)

        # ── E. WaveTrend 與 RSI 雷達動能訊號 ──
        if wt1.iloc[i] > -60.0:
            os_ext_trig = False
            last_ext_os_sl = np.nan
        if wt1.iloc[i] > -53.0:
            os_warn_trig = False
        if wt1.iloc[i] <= 53.0:
            ob_warn_trig = False
        if wt1.iloc[i] <= 60.0:
            wt_dead_trig = False

        is_red_area = per_under.iloc[i] < 100.0
        was_red_area = per_under.iloc[i - 1] < 100.0
        if is_red_area and not was_red_area:
            vix_in_red_cycle = False
        if is_red_area and wvf_ext.iloc[i]:
            vix_in_red_cycle = True
        if is_red_area:
            mb_fired_in_cycle = False

        # WT 頂部背離 (Top warning)
        size_piv = 5
        if i >= size_piv * 2:
            wt_slice = wt1.iloc[i - size_piv * 2 : i + 1].values
            left_max = np.max(wt_slice[:size_piv])
            right_max = np.max(wt_slice[size_piv + 1 :])
            mid_val = wt_slice[size_piv]
            if mid_val >= left_max and mid_val > right_max:
                curr_wt_ph_val = mid_val
                curr_wt_ph_price = high_v[i - size_piv]
                if last_wt_ph_idx != -1:
                    bars_since = (i - size_piv) - last_wt_ph_idx
                    if 5 <= bars_since <= 60:
                        if curr_wt_ph_price > last_wt_ph_price and curr_wt_ph_val < last_wt_ph_val:
                            other_events.append({
                                'bar_i': i,
                                'sig_str': f"⚠️【頂部預警】({t_str} @ {c_p})",
                                'sl': c_val + cur_atr * 1.5,
                                'tp': c_val - cur_atr * 3.0,
                                'risk_tag': "WT頂背離 (SL 1.5 ATR)"
                            })
                last_wt_ph_idx = i - size_piv
                last_wt_ph_val = curr_wt_ph_val
                last_wt_ph_price = curr_wt_ph_price

        # 恐慌抄底 (4重共振)
        if (wt1.iloc[i] > wt2.iloc[i]) and (wt1.iloc[i - 1] <= wt2.iloc[i - 1]) and (wt1.iloc[i - 1] <= -60.0) and wvf_ext.iloc[i - 1] and rsi_red_below.iloc[i - 1]:
            other_events.append({
                'bar_i': i,
                'sig_str': f"🟢【恐慌抄底】({t_str} @ {c_p})",
                'sl': c_val - cur_atr * 1.5,
                'tp': c_val + cur_atr * 3.0,
                'risk_tag': "四重共振大底 (SL 1.5 ATR)"
            })

        # 極度超賣 (3重共振 + 破止損二次觸發)
        if (wt1.iloc[i] <= -60.0) and wvf_ext.iloc[i] and rsi_red_below.iloc[i]:
            if (not os_ext_trig) or (not np.isnan(last_ext_os_sl) and low_v[i] < last_ext_os_sl):
                os_ext_trig = True
                last_ext_os_sl = c_val - (cur_atr * 1.5)
                other_events.append({
                    'bar_i': i,
                    'sig_str': f"🟣【極度超賣】({t_str} @ {c_p})",
                    'sl': last_ext_os_sl,
                    'tp': c_val + cur_atr * 3.0,
                    'risk_tag': "極端信號 (1:2.0 R:R)"
                })

        # Market Bottom
        wt_golden_cross_mb = (wt1.iloc[i] > wt2.iloc[i]) and (wt1.iloc[i - 1] <= wt2.iloc[i - 1])
        red_is_zero_now = (per_under.iloc[i] == 100.0)
        red_was_present = per_under.iloc[max(0, i - 3) : i].min() < 100.0
        if wt_golden_cross_mb and red_is_zero_now and red_was_present and vix_in_red_cycle and not mb_fired_in_cycle:
            mb_fired_in_cycle = True
            other_events.append({
                'bar_i': i,
                'sig_str': f"🟡【Market Bottom】({t_str} @ {c_p})",
                'sl': c_val - cur_atr * 1.0,
                'tp': c_val + cur_atr * 2.25,
                'risk_tag': "MB底部確認 (1:2.25 R:R)"
            })

        # 超賣預警
        if (wt1.iloc[i] <= -53.0) and wvf_ext.iloc[i] and not os_warn_trig:
            os_warn_trig = True
            other_events.append({
                'bar_i': i,
                'sig_str': f"🟪【超賣預警】({t_str} @ {c_p})",
                'sl': c_val - cur_atr * 1.5,
                'tp': c_val + cur_atr * 2.25,
                'risk_tag': "預警信號 (1:1.5 R:R)"
            })

        # WT 死叉
        wt_dead_cross = (wt1.iloc[i] < wt2.iloc[i]) and (wt1.iloc[i - 1] >= wt2.iloc[i - 1])
        green_area_was_0 = (per_over.iloc[i] == 0.0) or (per_over.iloc[i - 1] == 0.0) or (per_over.iloc[i - 2] == 0.0)
        if wt_dead_cross and green_area_was_0 and (wt1.iloc[i - 1] > 60.0) and not wt_dead_trig:
            wt_dead_trig = True
            other_events.append({
                'bar_i': i,
                'sig_str': f"🟠【WT 死叉】({t_str} @ {c_p})",
                'sl': c_val + cur_atr * 1.5,
                'tp': c_val - cur_atr * 3.0,
                'risk_tag': "高檔死叉 (1:2.0 R:R)"
            })

        # 超買預警 (對齊 Pine Script: wt1_v > 53)
        if (wt1.iloc[i] > 53.0) and not ob_warn_trig:
            ob_warn_trig = True
            other_events.append({
                'bar_i': i,
                'sig_str': f"🟡【超買預警】({t_str} @ {c_p})",
                'sl': c_val + cur_atr * 1.5,
                'tp': c_val - cur_atr * 2.25,
                'risk_tag': "預警信號 (1:1.5 R:R)"
            })

        # ── F. 反轉陷阱通道 (修正計數器判斷順序與 Pine Script 100% 一致) ──
        raw_bull_trap = False
        if close_v[i] > rt_lower.iloc[i]:
            if low_v[i] < rt_lower.iloc[i] and close_v[i - 1] > rt_lower.iloc[i - 1] and rt_blw_cnt <= 10:
                raw_bull_trap = True
            elif close_v[i - 1] < rt_lower.iloc[i - 1] and rt_blw_cnt <= 10:
                raw_bull_trap = True

        if low_v[i] < rt_lower.iloc[i]:
            rt_blw_cnt += 1
        else:
            rt_blw_cnt = 0

        raw_bear_trap = False
        if close_v[i] < rt_upper.iloc[i]:
            if high_v[i] > rt_upper.iloc[i] and close_v[i - 1] < rt_upper.iloc[i - 1] and rt_abv_cnt <= 10:
                raw_bear_trap = True
            elif close_v[i - 1] > rt_upper.iloc[i - 1] and rt_abv_cnt <= 10:
                raw_bear_trap = True

        if high_v[i] > rt_upper.iloc[i]:
            rt_abv_cnt += 1
        else:
            rt_abv_cnt = 0

        can_fire_rt = (i - rt_last_sig) >= 10
        rt_bull_trap = raw_bull_trap and can_fire_rt and (oversell_count.iloc[i] > 0)
        rt_bear_trap = raw_bear_trap and can_fire_rt and (overbuy_count.iloc[i] > 0)

        if rt_bull_trap:
            rt_last_sig = i
            sl_rt = min(low_v[i], low_v[i - 1]) - (rt_atr100_v[i] * 1.5)
            other_events.append({
                'bar_i': i,
                'sig_str': f"🛡️【空頭陷阱】({t_str} @ {c_p})",
                'sl': sl_rt,
                'tp': float(rt_basis.iloc[i]),
                'risk_tag': "破底翻回歸中軌"
            })
        if rt_bear_trap:
            rt_last_sig = i
            sl_rt = max(high_v[i], high_v[i - 1]) + (rt_atr100_v[i] * 1.5)
            other_events.append({
                'bar_i': i,
                'sig_str': f"⚠️【多頭陷阱】({t_str} @ {c_p})",
                'sl': sl_rt,
                'tp': float(rt_basis.iloc[i]),
                'risk_tag': "假突破回歸中軌"
            })

        # ── G. SMC OB 與 OB 共振回踩確認 (對齊 Pine Script 第五部分) ──
        def check_retest_list(ob_list):
            b_trig, s_trig = False, False
            m_b_ob, m_s_ob = None, None
            for ob in ob_list:
                if i > ob['ob_idx']:
                    top, bot = ob['top'], ob['bot']
                    if ob['bias'] == 1:
                        is_touch = (low_v[i] <= top) or (close_v[i - 1] <= top and close_v[i - 1] >= bot)
                        is_conf = (close_v[i] > top)
                        is_trend = (close_v[i] > open_v[i]) if strict_confirm else True
                        if is_touch and is_conf and is_trend:
                            b_trig = True
                            m_b_ob = ob
                    elif ob['bias'] == -1:
                        is_touch = (high_v[i] >= bot) or (close_v[i - 1] >= bot and close_v[i - 1] <= top)
                        is_conf = (close_v[i] < bot)
                        is_trend = (close_v[i] < open_v[i]) if strict_confirm else True
                        if is_touch and is_conf and is_trend:
                            s_trig = True
                            m_s_ob = ob
            return b_trig, s_trig, m_b_ob, m_s_ob

        final_b, final_s = False, False
        match_b_ob, match_s_ob = None, None

        if show_swing_ob:
            sw_b, sw_s, sw_b_ob, sw_s_ob = check_retest_list(active_sw_obs)
            if sw_b:
                final_b, match_b_ob = True, sw_b_ob
            if sw_s:
                final_s, match_s_ob = True, sw_s_ob

        int_b, int_s, int_b_ob, int_s_ob = check_retest_list(active_int_obs)
        if int_b:
            final_b, match_b_ob = True, int_b_ob
        if int_s:
            final_s, match_s_ob = True, int_s_ob

        fire_buy = final_b and not last_buy_state
        fire_sell = final_s and not last_sell_state
        last_buy_state = final_b
        last_sell_state = final_s

        ob_buf = cur_atr * 0.05
        if fire_buy and match_b_ob is not None:
            sl_px = match_b_ob['bot'] - ob_buf
            risk = max(c_val - sl_px, 1e-4)
            tp_px = c_val + (risk * ob_rr)
            if match_b_ob.get('is_reso', False):
                sig_txt = f"🟪【OB共振支撐】({t_str} 守穩 {match_b_ob['top']:.2f})"
                r_tag = f"OB共振風控 (1:{ob_rr:.1f})"
            else:
                sig_txt = f"🟩【OB支撐確認】({t_str} 守穩 {match_b_ob['top']:.2f})"
                r_tag = f"OB結構風控 (1:{ob_rr:.1f})"
            ob_buy_events.append({
                'bar_i': i,
                'sig_str': sig_txt,
                'parent_ob_idx': match_b_ob['ob_idx'],
                'sl': sl_px,
                'tp': tp_px,
                'risk_tag': r_tag
            })

        if fire_sell and match_s_ob is not None:
            sl_px = match_s_ob['top'] + ob_buf
            risk = max(sl_px - c_val, 1e-4)
            tp_px = c_val - (risk * ob_rr)
            if match_s_ob.get('is_reso', False):
                sig_txt = f"🟪【OB共振壓力】({t_str} 受阻 {match_s_ob['bot']:.2f})"
                r_tag = f"OB共振風控 (1:{ob_rr:.1f})"
            else:
                sig_txt = f"🟥【OB壓力確認】({t_str} 受阻 {match_s_ob['bot']:.2f})"
                r_tag = f"OB結構風控 (1:{ob_rr:.1f})"
            ob_sell_events.append({
                'bar_i': i,
                'sig_str': sig_txt,
                'parent_ob_idx': match_s_ob['ob_idx'],
                'sl': sl_px,
                'tp': tp_px,
                'risk_tag': r_tag
            })

    # ════════════════════════════════════════════════════════════════════════
    # 7. 纏論與最近中樞延伸 OB / 中樞 × SMC 共振確認 (100% 鏡像 Pine Script 第二部分)
    # ════════════════════════════════════════════════════════════════════════
    bi_arr, zs_arr, sg_arr = run_chan_engine(high_v, low_v, open_v, close_v, hist_v, min_gap=4)

    zs_events = []
    active_zs_zone = None

    if len(zs_arr) > 0:
        last_z = zs_arr[-1]
        search_start = max(1, bi_arr[last_z['startBi']]['b0']) if len(bi_arr) > last_z['startBi'] else 1
        break_idx = -1
        break_bias = 0

        for k in range(search_start, n):
            if close_v[k] > last_z['ZG'] and close_v[k - 1] <= last_z['ZG']:
                break_idx = k
                break_bias = 1
            elif close_v[k] < last_z['ZD'] and close_v[k - 1] >= last_z['ZD']:
                break_idx = k
                break_bias = -1

        if break_idx > 0:
            ob_idx = break_idx - 1
            ob_hi = float(parsed_high[ob_idx])
            ob_lo = float(parsed_low[ob_idx])

            mitigated = False
            if break_idx + 1 <= n - 1:
                for m in range(break_idx + 1, n):
                    if break_bias == 1 and low_v[m] < ob_lo:
                        mitigated = True
                        break
                    if break_bias == -1 and high_v[m] > ob_hi:
                        mitigated = True
                        break

            if not mitigated:
                has_zs_reso = False
                final_zs_hi = ob_hi
                final_zs_lo = ob_lo
                final_zs_bix = ob_idx

                # 檢查中樞延伸 OB 是否與場上 SMC 內部/擺動/共振 OB 重疊
                max_i = min(5, len(internal_obs))
                for idx_o in range(max_i):
                    s_ob = internal_obs[idx_o]
                    if s_ob['bias'] == break_bias:
                        i_top = min(ob_hi, s_ob['top'])
                        i_bot = max(ob_lo, s_ob['bot'])
                        if i_top > i_bot:
                            has_zs_reso = True
                            final_zs_hi = min(final_zs_hi, i_top)
                            final_zs_lo = max(final_zs_lo, i_bot)
                            final_zs_bix = max(final_zs_bix, s_ob['ob_idx'])
                            # 從 active_int_obs 移除被中樞共振吸收的原 SMC OB
                            active_int_obs = [x for x in active_int_obs if x['ob_idx'] != s_ob['ob_idx']]

                # 檢查是否與已生成的紫色共振框也發生重疊
                for x in list(active_int_obs):
                    if x.get('is_reso', False) and x['bias'] == break_bias:
                        if min(ob_hi, x['top']) > max(ob_lo, x['bot']):
                            has_zs_reso = True
                            active_int_obs.remove(x)

                if show_swing_ob:
                    max_s = min(5, len(swing_obs))
                    for idx_o in range(max_s):
                        s_ob = swing_obs[idx_o]
                        if s_ob['bias'] == break_bias:
                            i_top = min(ob_hi, s_ob['top'])
                            i_bot = max(ob_lo, s_ob['bot'])
                            if i_top > i_bot:
                                has_zs_reso = True
                                final_zs_hi = min(final_zs_hi, i_top)
                                final_zs_lo = max(final_zs_lo, i_bot)
                                final_zs_bix = max(final_zs_bix, s_ob['ob_idx'])
                                active_sw_obs = [x for x in active_sw_obs if x['ob_idx'] != s_ob['ob_idx']]

                if final_zs_hi <= final_zs_lo:
                    final_zs_hi = ob_hi
                    final_zs_lo = ob_lo

                active_zs_zone = {
                    'top': final_zs_hi,
                    'bot': final_zs_lo,
                    'ob_idx': final_zs_bix,
                    'bias': break_bias,
                    'is_zs_reso': has_zs_reso,
                    'type_name': ("🌟 中樞×SMC共振支撐" if break_bias == 1 else "🌟 中樞×SMC共振壓力") if has_zs_reso else ("🟠 中樞延伸支撐" if break_bias == 1 else "🟠 中樞延伸壓力")
                }

                # 掃描中樞 OB / 中樞共振 OB 形成後的所有 K 棒回踩確認
                scan_start = max(break_idx + 1, final_zs_bix + 1)
                prev_zs_sig = False

                if scan_start <= n - 1:
                    for m in range(scan_start, n):
                        m_lo, m_hi, m_cl, m_op = low_v[m], high_v[m], close_v[m], open_v[m]
                        prev_cl = close_v[m - 1]
                        m_t_str = df.index[m].strftime('%m/%d %H:%M')
                        m_atr = wt_atr_v[m] if not np.isnan(wt_atr_v[m]) else (m_hi - m_lo)
                        ob_buf = m_atr * 0.05

                        if break_bias == 1:
                            is_touch = (m_lo <= final_zs_hi) or (prev_cl <= final_zs_hi and prev_cl >= final_zs_lo)
                            is_conf = (m_cl > final_zs_hi)
                            is_trend = (m_cl > m_op) if strict_confirm else True
                            cur_sig = is_touch and is_conf and is_trend
                            if cur_sig and not prev_zs_sig:
                                sl_px = final_zs_lo - ob_buf
                                risk = max(m_cl - sl_px, 1e-4)
                                tp_px = m_cl + (risk * ob_rr)
                                tag_name = "🌟【中樞共振 Buy】" if has_zs_reso else "🟠【中樞 Buy】"
                                zs_events.append({
                                    'bar_i': m,
                                    'sig_str': f"{tag_name}({m_t_str} 守穩 {final_zs_hi:.2f})",
                                    'sl': sl_px,
                                    'tp': tp_px,
                                    'risk_tag': f"中樞{'共振' if has_zs_reso else ''}風控 (1:{ob_rr:.1f})"
                                })
                            prev_zs_sig = cur_sig
                        else:
                            is_touch = (m_hi >= final_zs_lo) or (prev_cl >= final_zs_lo and prev_cl <= final_zs_hi)
                            is_conf = (m_cl < final_zs_lo)
                            is_trend = (m_cl < m_op) if strict_confirm else True
                            cur_sig = is_touch and is_conf and is_trend
                            if cur_sig and not prev_zs_sig:
                                sl_px = final_zs_hi + ob_buf
                                risk = max(sl_px - m_cl, 1e-4)
                                tp_px = m_cl - (risk * ob_rr)
                                tag_name = "🌟【中樞共振 Sell】" if has_zs_reso else "🟠【中樞 Sell】"
                                zs_events.append({
                                    'bar_i': m,
                                    'sig_str': f"{tag_name}({m_t_str} 受阻 {final_zs_lo:.2f})",
                                    'sl': sl_px,
                                    'tp': tp_px,
                                    'risk_tag': f"中樞{'共振' if has_zs_reso else ''}風控 (1:{ob_rr:.1f})"
                                })
                            prev_zs_sig = cur_sig

    # 纏論 1/2/3 買賣點事件收集
    if include_chan_bs and len(sg_arr) > 0:
        for sg in sg_arr:
            pos = sg['pos']
            if 0 <= pos < n:
                sg_t_str = df.index[pos].strftime('%m/%d %H:%M')
                sg_atr = wt_atr_v[pos] if not np.isnan(wt_atr_v[pos]) else (high_v[pos] - low_v[pos])
                if sg['isLong']:
                    sl_px = min(sg['price'], sg['refP']) - sg_atr * 0.5
                    tp_px = close_v[pos] + max(close_v[pos] - sl_px, sg_atr) * ob_rr
                    other_events.append({
                        'bar_i': pos,
                        'sig_str': f"💠【纏論買點】{sg['label']} ({sg_t_str} @ {sg['price']:.2f})",
                        'sl': sl_px,
                        'tp': tp_px,
                        'risk_tag': f"纏論{sg['label']}防守 {sg['refP']:.2f}"
                    })
                else:
                    sl_px = max(sg['price'], sg['refP']) + sg_atr * 0.5
                    tp_px = close_v[pos] - max(sl_px - close_v[pos], sg_atr) * ob_rr
                    other_events.append({
                        'bar_i': pos,
                        'sig_str': f"💠【纏論賣點】{sg['label']} ({sg_t_str} @ {sg['price']:.2f})",
                        'sl': sl_px,
                        'tp': tp_px,
                        'risk_tag': f"纏論{sg['label']}防守 {sg['refP']:.2f}"
                    })

    # ── 8. 垃圾回收：僅保留當前仍存活的有效 SMC OB 回踩標籤 (對齊 Pine Script f_is_ob_valid) ──
    valid_ob_indices = {ob['ob_idx'] for ob in active_int_obs} | {ob['ob_idx'] for ob in active_sw_obs}
    valid_buy_events = [ev for ev in ob_buy_events if ev['parent_ob_idx'] in valid_ob_indices]
    valid_sell_events = [ev for ev in ob_sell_events if ev['parent_ob_idx'] in valid_ob_indices]

    # ── 9. 彙整近 recent_k 根 K 棒內觸發的所有訊號與最新風控數據 ──
    all_valid_events = other_events + valid_buy_events + valid_sell_events + zs_events
    recent_events = [ev for ev in all_valid_events if ev['bar_i'] >= n - recent_k]
    recent_events.sort(key=lambda x: x['bar_i'])

    latest_signals = []
    latest_sl_str = "—"
    latest_tp_str = "—"
    latest_risk_tag = "—"

    last_close = float(close_v[-1])
    prev_close = float(close_v[-2]) if n >= 2 else last_close
    chg_pct = ((last_close - prev_close) / prev_close) * 100.0 if prev_close != 0 else 0.0

    for ev in recent_events:
        if ev['sig_str'] not in latest_signals:
            latest_signals.append(ev['sig_str'])
        if not pd.isna(ev.get('sl')) and not pd.isna(ev.get('tp')):
            latest_sl_str = f"{ev['sl']:.2f} ({pct_str(ev['sl'], last_close)})"
            latest_tp_str = f"{ev['tp']:.2f} ({pct_str(ev['tp'], last_close)})"
            latest_risk_tag = ev.get('risk_tag', '結構風控')

    # ── 10. 產生與 Pine Script 100% 同步的「市場狀態面板 (24態)」數值解讀 ──
    vol_avg20 = pd.Series(vol_v).rolling(20).mean().iloc[-1]
    use_prev_bar = (high_v[-1] == low_v[-1]) or (not pd.isna(vol_avg20) and vol_avg20 > 0 and vol_v[-1] < vol_avg20 * 0.15)
    p_idx = -2 if (use_prev_bar and n >= 2) else -1

    p_wt1 = float(wt1.iloc[p_idx])
    p_rsi = float(avg_rsi.iloc[p_idx])
    p_wvf = float(wvf.iloc[p_idx])
    p_wvf_ext = bool(wvf_ext.iloc[p_idx])
    p_drop = close_v[p_idx] < open_v[p_idx]
    p_vol = float(vol_v[p_idx])
    p_vol_avg = float(pd.Series(vol_v).rolling(20).mean().iloc[p_idx]) if n >= 20 else float(np.mean(vol_v))
    vol_ratio = (p_vol / p_vol_avg) if (p_vol_avg and p_vol_avg > 0) else 1.0
    vol_state = "🔥 爆量" if vol_ratio > 1.5 else ("❄️ 縮量" if vol_ratio < 0.7 else "⚪ 正常")

    # 纏論 6 買賣點 × 短線 SMC 4 態 = 24 態核心矩陣 (外加盤整 4 態保底)
    last_bs_cls = sg_arr[-1]['cls'] if len(sg_arr) > 0 else 0
    last_bs_is_long = sg_arr[-1]['isLong'] if len(sg_arr) > 0 else False
    smc_inter_bull = (internal_trend == 1)
    is_choch_now = (last_smc_tag == "CHOCH")

    if smc_inter_bull and not is_choch_now:
        smc_state_id, smc_tag_ui = 1, "🟢綠BOS"
    elif smc_inter_bull and is_choch_now:
        smc_state_id, smc_tag_ui = 2, "🟢綠CHOCH"
    elif not smc_inter_bull and is_choch_now:
        smc_state_id, smc_tag_ui = 3, "🔴紅CHOCH"
    else:
        smc_state_id, smc_tag_ui = 4, "🔴紅BOS"

    if last_bs_is_long:
        if last_bs_cls == 1:
            chan_tag = "一買"
            action_txt = "強勢洗盤，大跌大買" if smc_state_id == 1 else ("左側大底，雙多共振" if smc_state_id == 2 else ("破位初止跌，搶短慎行" if smc_state_id == 3 else "空頭底背離，留意反彈"))
        elif last_bs_cls == 2:
            chan_tag = "二買"
            action_txt = "順勢回踩，積極做多" if smc_state_id == 1 else ("右側底確認，分批建倉" if smc_state_id == 2 else ("跌深反抽，防空頭回馬槍" if smc_state_id == 3 else "跌勢暫緩，空單帶好防守"))
        else:
            chan_tag = "三買"
            action_txt = "狂暴主升浪，多單抱牢" if smc_state_id == 1 else ("底部突破，迎來初升浪" if smc_state_id == 2 else ("多空分歧 (誘多)，防騙線" if smc_state_id == 3 else "空頭強反撲，注意趨勢扭轉"))
    elif last_bs_cls != 0:
        if last_bs_cls == 1:
            chan_tag = "一賣"
            action_txt = "多頭頂背離，多單防守" if smc_state_id == 1 else ("反彈遇強壓，短線獲利了結" if smc_state_id == 2 else ("右側頂成型，逢高逃頂" if smc_state_id == 3 else "空頭順勢反彈，絕佳高空點"))
        elif last_bs_cls == 2:
            chan_tag = "二賣"
            action_txt = "高位震盪不過高，減碼觀望" if smc_state_id == 1 else ("反彈不過高，防二次探底" if smc_state_id == 2 else ("逃命波結束，做頭右肩確認" if smc_state_id == 3 else "順勢反抽不過高，順勢加空"))
        else:
            chan_tag = "三賣"
            action_txt = "多空分歧 (誘空)，防大調" if smc_state_id == 1 else ("探底強打壓，震盪洗盤中" if smc_state_id == 2 else ("頂部破位，開啟主跌浪" if smc_state_id == 3 else "狂暴主跌浪，空單抱牢"))
    else:
        chan_tag = "盤整"
        action_txt = "多頭高位震盪" if smc_state_id == 1 else ("多頭築底震盪" if smc_state_id == 2 else ("空頭做頭震盪" if smc_state_id == 3 else "空頭低位磨底"))

    chan_smc_panel_txt = f"【{smc_tag_ui} + {chan_tag}】{action_txt}"

    # RSI 狀態文字
    if bool(rsi_strong_green.iloc[p_idx]):
        rsi_status = "🔥 綠區軋空"
    elif p_rsi >= 70:
        rsi_status = "🔥 極度超買"
    elif bool(rsi_red_below.iloc[p_idx]):
        rsi_status = "❄️ 紅區破底"
    elif p_rsi <= 30:
        rsi_status = "❄️ 極度超賣"
    elif p_rsi >= 60:
        rsi_status = "🟢 偏強多頭"
    elif p_rsi <= 40:
        rsi_status = "🔵 偏弱空頭"
    else:
        rsi_status = "⚪ 中性整理"

    wvf_status = "🟢 恐慌拋售" if (p_wvf_ext and p_drop) else ("🟠 劇烈推升" if p_wvf_ext else "⚪ 常態波動")

    # ── 11. 計算距離當前價格最近的活躍支撐與壓力區間 (供潛伏雷達使用) ──
    all_zones = []
    if active_zs_zone is not None:
        all_zones.append(active_zs_zone)
    for ob in active_int_obs:
        z_name = ("🟪 OB共振支撐" if ob['bias'] == 1 else "🟪 OB共振壓力") if ob.get('is_reso') else ("🟩 內部OB支撐" if ob['bias'] == 1 else "🟥 內部OB壓力")
        all_zones.append({'top': ob['top'], 'bot': ob['bot'], 'bias': ob['bias'], 'type_name': z_name})
    if show_swing_ob:
        for ob in active_sw_obs:
            z_name = ("🟪 擺動共振支撐" if ob['bias'] == 1 else "🟪 擺動共振壓力") if ob.get('is_reso') else ("🟩 擺動OB支撐" if ob['bias'] == 1 else "🟥 擺動OB壓力")
            all_zones.append({'top': ob['top'], 'bot': ob['bot'], 'bias': ob['bias'], 'type_name': z_name})

    nearest_sup_str = "無"
    nearest_res_str = "無"
    nearest_sup_dist = 999.0
    nearest_res_dist = 999.0

    bull_zones = [z for z in all_zones if z['bias'] == 1]
    bear_zones = [z for z in all_zones if z['bias'] == -1]

    if bull_zones:
        bull_zones.sort(key=lambda z: abs(last_close - z['top']))
        bz = bull_zones[0]
        nearest_sup_dist = ((last_close - bz['top']) / last_close) * 100.0
        in_zone = " (⚡踩入框內!)" if (bz['bot'] <= last_close <= bz['top']) else f" ({nearest_sup_dist:+.2f}%)"
        nearest_sup_str = f"{bz['type_name']} [{bz['bot']:.2f}~{bz['top']:.2f}]{in_zone}"

    if bear_zones:
        bear_zones.sort(key=lambda z: abs(z['bot'] - last_close))
        rz = bear_zones[0]
        nearest_res_dist = ((rz['bot'] - last_close) / last_close) * 100.0
        in_zone = " (⚡進入框內!)" if (rz['bot'] <= last_close <= rz['top']) else f" ({nearest_res_dist:+.2f}%)"
        nearest_res_str = f"{rz['type_name']} [{rz['bot']:.2f}~{rz['top']:.2f}]{in_zone}"

    # ── 12. 提取「最近 2 根 K 棒 (bar_i >= n - 2)」剛觸發的即時訊號，供風向標「準備抄底/逃頂」使用 ──
    k2_events = [ev['sig_str'] for ev in all_valid_events if ev['bar_i'] >= n - 2]
    k2_events = list(dict.fromkeys(k2_events))

    return {
        "最新收盤價": last_close,
        "漲跌幅": chg_pct,
        "當前成交量": float(vol_v[-1]),
        "量比": vol_ratio,
        "量能狀態": vol_state,
        "WT快線": p_wt1,
        "平均RSI": p_rsi,
        "RSI狀態": rsi_status,
        "WVF恐慌值": p_wvf,
        "WVF狀態": wvf_status,
        "纏論SMC解讀": chan_smc_panel_txt,
        "SMC_State_ID": smc_state_id,
        "SMC_Tag_UI": smc_tag_ui,
        "Chan_Tag": chan_tag,
        "Chan_Action_Base": action_txt,
        "Chan_Is_Long": last_bs_is_long,
        "Chan_Cls": last_bs_cls,
        "K2_Signals": k2_events,
        "觸發指標通知": " ｜ ".join(latest_signals) if latest_signals else "",
        "訊號數量": len(latest_signals),
        "建議止損(SL)": latest_sl_str,
        "目標止盈(TP)": latest_tp_str,
        "風控依據": latest_risk_tag,
        "最近支撐區": nearest_sup_str,
        "最近壓力區": nearest_res_str,
        "支撐距離Pct": abs(nearest_sup_dist),
        "壓力距離Pct": abs(nearest_res_dist),
        "SMC_Trend": internal_trend,
        "SMC_Tag": last_smc_tag
    }

def format_vol(val):
    if val == 0 or pd.isna(val):
        return "N/A"
    if val >= 1e9:
        return f"{val / 1e9:.2f}B"
    if val >= 1e6:
        return f"{val / 1e6:.2f}M"
    if val >= 1e3:
        return f"{val / 1e3:.1f}K"
    return f"{val:.0f}"

# ════════════════════════════════════════════════════════════════════════════
# 網頁側邊欄設定
# ════════════════════════════════════════════════════════════════════════════
user_config = load_config()

st.sidebar.header("⚙️ 量化雷達控制台")

st.sidebar.subheader("📌 自選監控清單")
fav_input = st.sidebar.text_area(
    "請輸入股票/加密貨幣代號 (逗號分隔)：",
    value=user_config["favorites"],
    height=120,
    help="台股請加 .TW (如 2330.TW、00631L.TW)。大盤 ^TWII，美股期貨 NQ=F，加密貨幣 BTC-USD。"
)

st.sidebar.subheader("🎯 訊號與時間參數")
tf_options = {"15分K": "15m", "1小時K": "1h", "4小時K (TV標準)": "4h", "日K": "1d"}
tf_opts_keys = list(tf_options.keys())
tf_idx = tf_opts_keys.index(user_config["selected_tf_label"]) if user_config["selected_tf_label"] in tf_opts_keys else 2
selected_tf_label = st.sidebar.selectbox("⏳ 選擇時間框架", tf_opts_keys, index=tf_idx)
selected_tf = tf_options[selected_tf_label]

col_s1, col_s2 = st.sidebar.columns(2)
with col_s1:
    recent_k = st.number_input("掃描近 N 根K棒", min_value=1, max_value=15, value=int(user_config.get("recent_k", 2)))
with col_s2:
    ob_rr = st.number_input("OB/中樞盈虧比", min_value=0.5, max_value=10.0, step=0.5, value=float(user_config.get("ob_rr", 2.0)))

max_days = 60 if selected_tf in ["15m"] else (730 if selected_tf in ["1h", "4h"] else 1000)
default_days = max(20, min(int(user_config.get("scan_days", 90)), max_days))
scan_days = st.sidebar.slider("載入歷史天數 (建議 ≥60 天以完整建立中樞與OB)", min_value=20, max_value=max_days, value=default_days)

with st.sidebar.expander("🛠️ 指標細節對齊設定 (鏡像 Pine Script)", expanded=True):
    strict_confirm = st.checkbox("嚴格收線確認 (Buy需收紅/Sell需收綠)", value=bool(user_config.get("strict_confirm", False)), help="Pine Script V3.8 預設為不勾選 (False)，只要收盤站上 OB 上緣即確認")
    show_swing_ob = st.checkbox("回踩包含擺動 OB (Swing OB)", value=bool(user_config.get("show_swing_ob", False)), help="Pine Script 預設僅啟用內部 OB (Internal OB)")
    include_chan_bs = st.checkbox("額外掃描纏論 1/2/3 買賣點", value=bool(user_config.get("include_chan_bs", False)))
    scan_us_indices = st.checkbox("🌍 擴充掃描美股三大指數成分股 (~500檔)", value=bool(user_config.get("scan_us_indices", False)))

st.sidebar.subheader("⚡ 戰術濾網與訊號過濾")

# 初始化 Session State，確保手動打叉 (×) 後絕對不會被預設清單蓋掉
if "ms_target_signals" not in st.session_state:
    saved_sigs = [s for s in user_config.get("target_signals", ALL_SIG_TYPES) if s in ALL_SIG_TYPES]
    st.session_state.ms_target_signals = saved_sigs

def on_preset_change():
    choice = st.session_state.preset_selector
    if PRESET_FILTERS.get(choice) is not None:
        st.session_state.ms_target_signals = list(PRESET_FILTERS[choice])

st.sidebar.selectbox(
    "快速套用戰術濾網 (切換後可直接下方微調打叉)：",
    ["🛠️ 自訂勾選訊號 (記憶模式)"] + [k for k in PRESET_FILTERS.keys() if k != "🛠️ 自訂勾選訊號"],
    index=0,
    key="preset_selector",
    on_change=on_preset_change
)

c_sel1, c_sel2 = st.sidebar.columns(2)
with c_sel1:
    if st.button("✅ 全選所有訊號", use_container_width=True):
        st.session_state.ms_target_signals = list(ALL_SIG_TYPES)
        st.rerun()
with c_sel2:
    if st.button("🗑️ 清空所有訊號", use_container_width=True):
        st.session_state.ms_target_signals = []
        st.rerun()

target_signals = st.sidebar.multiselect(
    "保留含有以下訊號的標的 (可自由打叉 × 移除)：",
    options=ALL_SIG_TYPES,
    key="ms_target_signals"
)

with st.sidebar.expander("📊 基本面估值過濾 (選配)", expanded=False):
    scan_options = [
        "1. 僅看技術指標 (預設)",
        "2. 聯集 (技術觸發 OR 基本面達標)",
        "3. 交集 (技術觸發 AND 基本面達標)",
        "4. 僅看基本面 (無視技術指標)"
    ]
    s_idx = scan_options.index(user_config["scan_mode"]) if user_config["scan_mode"] in scan_options else 0
    scan_mode = st.radio("選擇掃描模式：", scan_options, index=s_idx)
    max_peg = st.number_input("市賺率 (PEG) 低於", min_value=0.0, value=float(user_config["max_peg"]), step=0.1)
    max_pe = st.number_input("本益比 (P/E) 低於", min_value=0.0, value=float(user_config["max_pe"]), step=1.0)
    max_pb = st.number_input("股價淨值比 (P/B) 低於", min_value=0.0, value=float(user_config["max_pb"]), step=0.1)

st.sidebar.markdown("---")
col_b1, col_b2 = st.sidebar.columns(2)
with col_b1:
    if st.button("💾 儲存設定", use_container_width=True):
        new_cfg = {
            "favorites": fav_input,
            "scan_mode": scan_mode,
            "max_peg": max_peg,
            "max_pe": max_pe,
            "max_pb": max_pb,
            "scan_us_indices": scan_us_indices,
            "selected_tf_label": selected_tf_label,
            "recent_k": recent_k,
            "scan_days": scan_days,
            "strict_confirm": strict_confirm,
            "show_swing_ob": show_swing_ob,
            "include_chan_bs": include_chan_bs,
            "ob_rr": ob_rr,
            "target_signals": target_signals
        }
        save_config(new_cfg)
        st.sidebar.success("✅ 設定已記憶！")
        time.sleep(0.4)
        st.rerun()

with col_b2:
    scan_btn = st.button("🚀 啟動掃描", type="primary", use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# 主程式執行區
# ════════════════════════════════════════════════════════════════════════════
if scan_btn:
    favorites = [t.strip().upper() for t in fav_input.split(",") if t.strip()]
    all_tickers = favorites.copy()

    if scan_us_indices:
        with st.spinner("🔄 正在取得美股三大指數 (S&P 500 / Nasdaq 100 / 費半) 成分股清單..."):
            us_stocks, _, _, success = get_us_indices()
            if success:
                st.toast(f"✅ 成功載入 {len(us_stocks)} 檔美股指數成分股！")
            else:
                st.warning("⚠️ 維基百科連線受限，已自動載入核心權值股備用清單。")
            all_tickers.extend(us_stocks)

    all_tickers = list(dict.fromkeys(all_tickers))
    if not all_tickers:
        st.error("❌ 監控清單是空的，請先輸入股票代號！")
        st.stop()

    fetch_interval = "1h" if selected_tf == "4h" else selected_tf

    # ────────────────────────────────────────────────────────────────────────
    # 第一區：大盤 24 態纏論×SMC 結構矩陣 ＋ 近14K動能修正 ＋ 近2K準備抄底雷達
    # ────────────────────────────────────────────────────────────────────────
    st.subheader(f"🚥 大盤 24 態結構風向標 × 近 2K 閃電抄底雷達 ({selected_tf_label})")

    barometer_tickers = ["QQQ", "SOXX", "SPY", "^TWII", "BTC-USD"]
    bull_kws_map = {
        "中樞共振 Buy": "中樞共振Buy", "OB共振支撐": "OB共振支撐", "中樞 Buy": "中樞Buy", "OB支撐確認": "OB支撐",
        "恐慌抄底": "恐慌抄底", "極度超賣": "極度超賣", "Market Bottom": "Market Bottom",
        "超賣預警": "超賣預警", "空頭陷阱": "空頭陷阱", "多頭 CHOCH": "多頭CHOCH", "多頭 BOS": "多頭BOS", "纏論買點": "纏論買點"
    }
    bear_kws_map = {
        "中樞共振 Sell": "中樞共振Sell", "OB共振壓力": "OB共振壓力", "中樞 Sell": "中樞Sell", "OB壓力確認": "OB壓力",
        "頂部預警": "頂部預警", "WT 死叉": "WT死叉", "超買預警": "超買預警",
        "多頭陷阱": "多頭陷阱", "空頭 CHOCH": "空頭CHOCH", "空頭 BOS": "空頭BOS", "纏論賣點": "纏論賣點"
    }

    # 近 2K 抄底 / 右側買進關鍵字 vs 逃頂 / 做空關鍵字
    bottom_dip_kws = ["恐慌抄底", "極度超賣", "Market Bottom", "空頭陷阱", "中樞共振 Buy", "OB共振支撐", "中樞 Buy", "OB支撐確認", "纏論買點"]
    top_escape_kws = ["頂部預警", "WT 死叉", "多頭陷阱", "中樞共振 Sell", "OB共振壓力", "中樞 Sell", "OB壓力確認", "纏論賣點"]

    with st.spinner("🔄 正在運算大盤 24 態纏論×SMC 矩陣與近 2K 閃電抄底訊號..."):
        b_data = yf.download(barometer_tickers, period=f"{scan_days}d", interval=fetch_interval, group_by='ticker', progress=False, threads=True)
        b_cols = st.columns(len(barometer_tickers))

        for idx, b_tick in enumerate(barometer_tickers):
            with b_cols[idx]:
                try:
                    df_b = b_data[b_tick] if len(barometer_tickers) > 1 else b_data
                    df_b = df_b.dropna(subset=['Close'])
                    if len(df_b) > 40:
                        df_proc_b = resample_to_tv_4h(df_b, b_tick) if selected_tf == "4h" else df_b.copy()
                        b_res = scan_signals(df_proc_b, recent_k=14, strict_confirm=strict_confirm, show_swing_ob=show_swing_ob, include_chan_bs=True, ob_rr=ob_rr)

                        bull_count, bear_count = 0, 0
                        bull_detail, bear_detail = {}, {}
                        sigs = []

                        if b_res and b_res["觸發指標通知"]:
                            sigs = b_res["觸發指標通知"].split(" ｜ ")
                            for s in sigs:
                                found = False
                                for k, name in bull_kws_map.items():
                                    if k in s:
                                        bull_count += 1
                                        bull_detail[name] = bull_detail.get(name, 0) + 1
                                        found = True
                                        break
                                if not found:
                                    for k, name in bear_kws_map.items():
                                        if k in s:
                                            bear_count += 1
                                            bear_detail[name] = bear_detail.get(name, 0) + 1
                                            break

                        # ── 1. 取出 24 態結構基底 (SMC 4態 × 纏論 6買賣點) ──
                        smc_id = b_res["SMC_State_ID"]       # 1:綠BOS, 2:綠CHOCH, 3:紅CHOCH, 4:紅BOS
                        smc_ui = b_res["SMC_Tag_UI"]
                        chan_tag = b_res["Chan_Tag"]         # 一買/二買/三買/一賣/二賣/三賣/盤整
                        base_advice = b_res["Chan_Action_Base"]
                        chan_long = b_res["Chan_Is_Long"]
                        chan_cls = b_res["Chan_Cls"]

                        # 判定結構基底偏多或偏空
                        struct_is_bull = (smc_id in [1, 2] and (chan_long or chan_cls == 0)) or (smc_id in [3, 4] and chan_long and chan_cls in [1, 2])
                        struct_is_bear = (smc_id in [3, 4] and (not chan_long)) or (smc_id in [1, 2] and (not chan_long and chan_cls != 0))

                        # ── 2. 結合「近 14K 多空計分」進行動態戰術修正 ──
                        if bear_count > bull_count:
                            mom_14k_str = f"近14K空偏多 (空{bear_count}>多{bull_count})"
                            if struct_is_bull:
                                tactical_tag = "⚠️ 謹慎做多 (等回踩)"
                                style_cls = "warn"
                            else:
                                tactical_tag = "🔴 順勢做空 / 空單抱牢"
                                style_cls = "bear"
                        elif bull_count > bear_count:
                            mom_14k_str = f"近14K多偏空 (多{bull_count}>空{bear_count})"
                            if struct_is_bull:
                                tactical_tag = "🔥 積極做多 / 順勢抱牢"
                                style_cls = "bull"
                            else:
                                tactical_tag = "⚠️ 謹慎做空 (防反抽)"
                                style_cls = "warn"
                        else:
                            mom_14k_str = f"近14K多空均衡 ({bull_count}:{bear_count})"
                            tactical_tag = "🟢 偏多震盪" if struct_is_bull else ("🔴 偏空震盪" if struct_is_bear else "⚪ 區間觀望")
                            style_cls = "bull" if struct_is_bull else ("bear" if struct_is_bear else "warn")

                        # ── 3. 檢查「近 2K 即時閃電訊號」：直接提示「準備抄底」或「準備逃頂」 ──
                        k2_sigs = b_res.get("K2_Signals", [])
                        k2_bull_hits = [s.split("(")[0] for s in k2_sigs if any(k in s for k in bottom_dip_kws)]
                        k2_bear_hits = [s.split("(")[0] for s in k2_sigs if any(k in s for k in top_escape_kws)]

                        k2_banner_html = ""
                        if k2_bull_hits:
                            hit_names = " + ".join(k2_bull_hits[:2])
                            dip_word = "⚡ 準備抄底！" if (smc_id in [3, 4] or any("抄底" in x or "超賣" in x or "Bottom" in x or "陷阱" in x for x in k2_bull_hits)) else "⚡ 右側回踩買點！"
                            k2_banner_html = f'<div style="background:rgba(0,230,118,0.22);border:1px solid #00e676;border-radius:6px;padding:5px 8px;margin-bottom:7px;font-size:0.80rem;color:#00e676;font-weight:700;">{dip_word} 近2K觸發：{hit_names}</div>'
                            style_cls = "bull"
                        elif k2_bear_hits:
                            hit_names = " + ".join(k2_bear_hits[:2])
                            k2_banner_html = f'<div style="background:rgba(255,82,82,0.22);border:1px solid #ff5252;border-radius:6px;padding:5px 8px;margin-bottom:7px;font-size:0.80rem;color:#ff5252;font-weight:700;">🚨 準備逃頂/防守！ 近2K觸發：{hit_names}</div>'
                            if style_cls == "bull":
                                style_cls = "warn"

                        px_val = b_res["最新收盤價"]
                        chg_val = b_res["漲跌幅"]
                        chg_col = "#00e676" if chg_val >= 0 else "#ff5252"

                        card_html = (
                            f'<div class="baro-card baro-{style_cls}">'
                            f'<div class="baro-title"><span>{b_tick}</span>'
                            f'<span class="baro-price">{px_val:.2f} <span style="color:{chg_col};font-size:0.82rem;">({chg_val:+.2f}%)</span></span></div>'
                            f'{k2_banner_html}'
                            f'<span class="baro-badge badge-{style_cls}">【{smc_ui} + {chan_tag}】{tactical_tag}</span>'
                            f'<div class="baro-advice">24態劇本：{base_advice}</div>'
                            f'<div class="baro-sub">'
                            f'• 14K動能: <b>{mom_14k_str}</b><br>'
                            f'• 指標: WT <span class="metric-pill">{b_res["WT快線"]:.1f}</span> ｜ RSI <span class="metric-pill">{b_res["平均RSI"]:.1f}</span> ({b_res["RSI狀態"]})<br>'
                            f'• 支撐: {b_res["最近支撐區"]}<br>'
                            f'• 壓力: {b_res["最近壓力區"]}'
                            f'</div></div>'
                        )
                        st.markdown(card_html, unsafe_allow_html=True)

                        with st.expander("🕒 近 14K 訊號計分與時間軸"):
                            if bull_detail:
                                st.caption("🟢 **多方計分：** " + "、".join([f"{k}({v})" for k, v in bull_detail.items()]))
                            if bear_detail:
                                st.caption("🔴 **空方計分：** " + "、".join([f"{k}({v})" for k, v in bear_detail.items()]))
                            for s in sigs:
                                st.caption(f"• {s}")
                except Exception:
                    st.markdown(f"**{b_tick}** - 暫無數據")

    st.markdown("---")

    # ────────────────────────────────────────────────────────────────────────
    # 第二區：批量個股掃描執行
    # ────────────────────────────────────────────────────────────────────────
    progress_bar = st.progress(0)
    status_text = st.empty()

    chunk_size = 80
    all_scanned_rows = []
    successful_tickers = set()
    start_time = time.time()
    use_fund = not scan_mode.startswith("1")

    for i in range(0, len(all_tickers), chunk_size):
        batch = all_tickers[i : i + chunk_size]
        status_text.text(f"⏳ 正在下載與分析 K 線結構 (含 SMC 共振與纏論中樞): {i} / {len(all_tickers)} ...")

        try:
            data = yf.download(batch, period=f"{scan_days}d", interval=fetch_interval, group_by='ticker', progress=False, threads=True)
            for t in batch:
                try:
                    df_t = data[t] if len(batch) > 1 else data
                    df_t = df_t.dropna(subset=['Close'])

                    if len(df_t) > 40:
                        successful_tickers.add(t)
                        try:
                            avg_vol = float(df_t.groupby(df_t.index.date)['Volume'].sum().mean())
                        except Exception:
                            avg_vol = 0.0

                        df_proc = resample_to_tv_4h(df_t, t) if selected_tf == "4h" else df_t.copy()
                        res_tech = scan_signals(
                            df_proc,
                            recent_k=recent_k,
                            strict_confirm=strict_confirm,
                            show_swing_ob=show_swing_ob,
                            include_chan_bs=include_chan_bs,
                            ob_rr=ob_rr
                        )
                        if res_tech is None:
                            continue

                        pass_tech = res_tech["觸發指標通知"] != ""
                        pass_fund = False
                        pe_val, peg_val, pb_val = 0.0, 0.0, 0.0

                        if use_fund:
                            try:
                                info = yf.Ticker(t).info
                                pe_val = float(info.get('trailingPE') or 0)
                                peg_val = float(info.get('pegRatio') or 0)
                                pb_val = float(info.get('priceToBook') or 0)

                                cond_pe = (0 < pe_val <= max_pe) if max_pe > 0 else True
                                cond_peg = (0 < peg_val <= max_peg) if max_peg > 0 else True
                                cond_pb = (0 < pb_val <= max_pb) if max_pb > 0 else True
                                pass_fund = True if (max_pe == 0 and max_peg == 0 and max_pb == 0) else (cond_pe and cond_peg and cond_pb)
                            except Exception:
                                pass_fund = False

                        is_fav = t in favorites
                        display_t = f"⭐ {t}" if is_fav else t

                        smc_str = f"🟢 多頭 {res_tech['SMC_Tag']}" if res_tech["SMC_Trend"] == 1 else (
                            f"🔴 空頭 {res_tech['SMC_Tag']}" if res_tech["SMC_Trend"] == -1 else "⚪ 震盪整理"
                        )

                        row_dict = {
                            "Raw_Ticker": t,
                            "Priority": 1 if is_fav else 0,
                            "標的代號": display_t,
                            "TV看圖": get_tv_link(t),
                            "最新收盤價": round(res_tech["最新收盤價"], 2),
                            "漲跌幅(%)": round(res_tech["漲跌幅"], 2),
                            "SMC 結構": smc_str,
                            "纏論/SMC 面板解讀": res_tech["纏論SMC解讀"],
                            "觸發指標通知": res_tech["觸發指標通知"] if pass_tech else "無技術訊號",
                            "訊號數": res_tech["訊號數量"],
                            "建議止損 (SL)": res_tech["建議止損(SL)"],
                            "目標止盈 (TP)": res_tech["目標止盈(TP)"],
                            "風控依據": res_tech["風控依據"],
                            "最近支撐區 (OB/共振/中樞)": res_tech["最近支撐區"],
                            "最近壓力區 (OB/共振/中樞)": res_tech["最近壓力區"],
                            "支撐距離(%)": round(res_tech["支撐距離Pct"], 2),
                            "壓力距離(%)": round(res_tech["壓力距離Pct"], 2),
                            "WT快線": round(res_tech["WT快線"], 1),
                            "平均RSI": round(res_tech["平均RSI"], 1),
                            "RSI狀態": res_tech["RSI狀態"],
                            "WVF恐慌": round(res_tech["WVF恐慌值"], 2),
                            "WVF狀態": res_tech["WVF狀態"],
                            "量比(x)": round(res_tech["量比"], 2),
                            "量能狀態": res_tech["量能狀態"],
                            "日均量": format_vol(avg_vol),
                            "Raw_Volume": avg_vol,
                            "Pass_Tech": pass_tech,
                            "Pass_Fund": pass_fund
                        }

                        if use_fund:
                            row_dict["PEG"] = f"{peg_val:.2f}" if peg_val > 0 else "N/A"
                            row_dict["P/E"] = f"{pe_val:.2f}" if pe_val > 0 else "N/A"
                            row_dict["P/B"] = f"{pb_val:.2f}" if pb_val > 0 else "N/A"

                        all_scanned_rows.append(row_dict)
                except Exception:
                    continue
        except Exception:
            continue

        progress_bar.progress(min((i + chunk_size) / len(all_tickers), 1.0))

    elapsed = int(time.time() - start_time)
    status_text.empty()
    progress_bar.empty()

    failed_tickers = [t for t in all_tickers if t not in successful_tickers]
    if failed_tickers:
        st.caption(f"⚠️ 無法取得足夠長度的標的 ({len(failed_tickers)} 檔)：`{', '.join(failed_tickers[:20])}`")

    # ── 過濾符合觸發條件的個股 ──
    triggered_rows = []
    for r in all_scanned_rows:
        if scan_mode.startswith("1"):
            should_add = r["Pass_Tech"]
        elif scan_mode.startswith("2"):
            should_add = r["Pass_Tech"] or r["Pass_Fund"]
        elif scan_mode.startswith("3"):
            should_add = r["Pass_Tech"] and r["Pass_Fund"]
        else:
            should_add = r["Pass_Fund"]

        if not should_add:
            continue

        # 若僅看基本面 (模式4) 且無技術訊號則放行；否則嚴格依照多選框內保留的訊號過濾
        if r["觸發指標通知"] == "無技術訊號":
            if not scan_mode.startswith("1"):
                triggered_rows.append(r)
        elif len(target_signals) > 0:
            sigs = r["觸發指標通知"].split(" ｜ ")
            if any(any(target in s for target in target_signals) for s in sigs):
                triggered_rows.append(r)

    # ── 頂部統計指標列 ──
    reso_hits = sum(1 for r in triggered_rows if ("共振" in r["觸發指標通知"] or "中樞" in r["觸發指標通知"]))
    bull_hits = sum(1 for r in triggered_rows if any(k in r["觸發指標通知"] for k in ["Buy", "支撐", "抄底", "Bottom", "空頭陷阱", "纏論買點"]))
    bear_hits = sum(1 for r in triggered_rows if any(k in r["觸發指標通知"] for k in ["Sell", "壓力", "頂部", "死叉", "多頭陷阱", "纏論賣點"]))

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📡 成功掃描標的總數", f"{len(successful_tickers)} 檔", f"耗時 {elapsed} 秒")
    m2.metric("🎯 符合條件觸發標的", f"{len(triggered_rows)} 檔", f"近 {recent_k} 根 {selected_tf_label}")
    m3.metric("🌟 中樞 / OB 共振確認", f"{reso_hits} 檔", "高勝率結構點位")
    m4.metric("⚖️ 多空觸發比例", f"多 {bull_hits} : 空 {bear_hits}", "依觸發訊號統計")

    # ────────────────────────────────────────────────────────────────────────
    # 第三區：三大功能分頁籤展示
    # ────────────────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs([
        f"🎯 觸發訊號雷達表 ({len(triggered_rows)})",
        f"📦 支撐/壓力潛伏距離雷達 ({len(all_scanned_rows)})",
        f"📊 全標的市場狀態總覽 ({len(all_scanned_rows)})"
    ])

    col_cfg = {
        "TV看圖": st.column_config.LinkColumn("TV 圖表", display_text="🔗 開啟圖表", width="small"),
        "最新收盤價": st.column_config.NumberColumn("收盤價", format="%.2f"),
        "漲跌幅(%)": st.column_config.NumberColumn("漲跌%", format="%+.2f%%"),
        "量比(x)": st.column_config.ProgressColumn("量比 (vs 20MA)", format="%.2fx", min_value=0.0, max_value=3.0),
        "支撐距離(%)": st.column_config.NumberColumn("距支撐%", format="%.2f%%"),
        "壓力距離(%)": st.column_config.NumberColumn("距壓力%", format="%.2f%%"),
    }

    with tab1:
        if triggered_rows:
            df_report = pd.DataFrame(triggered_rows)
            df_report = df_report.sort_values(by=['Priority', '訊號數', 'Raw_Volume'], ascending=[False, False, False])

            cols_tab1 = [
                "標的代號", "TV看圖", "最新收盤價", "漲跌幅(%)", "SMC 結構",
                "觸發指標通知", "建議止損 (SL)", "目標止盈 (TP)", "風控依據",
                "最近支撐區 (OB/共振/中樞)", "量比(x)", "日均量"
            ]
            if use_fund:
                cols_tab1.extend(["PEG", "P/E", "P/B"])

            st.dataframe(
                df_report[cols_tab1],
                column_config=col_cfg,
                use_container_width=True,
                hide_index=True,
                height=580
            )

            csv_data = df_report[cols_tab1].to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 匯出觸發訊號清單 (CSV)",
                data=csv_data,
                file_name=f"bd_scanner_signals_{selected_tf}_{time.strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("🎯 目前沒有標的同時符合「觸發條件」與「訊號過濾器」。可嘗試將左側『掃描近 N 根K棒』調大或切換至『全部訊號』。")

    with tab2:
        st.markdown("💡 **實戰用法：** 此表依 **「距離下方支撐區 (OB / 共振 / 中樞) 的百分比」** 由近到遠排序，方便找出 **正在踩入框內 (`⚡踩入框內!`)** 或即將回踩支撐的潛伏標的。")
        if all_scanned_rows:
            df_zones = pd.DataFrame(all_scanned_rows)
            df_zones = df_zones.sort_values(by=['Priority', '支撐距離(%)'], ascending=[False, True])
            cols_tab2 = [
                "標的代號", "TV看圖", "最新收盤價", "漲跌幅(%)", "SMC 結構",
                "最近支撐區 (OB/共振/中樞)", "支撐距離(%)",
                "最近壓力區 (OB/共振/中樞)", "壓力距離(%)",
                "WT快線", "平均RSI", "觸發指標通知"
            ]
            st.dataframe(
                df_zones[cols_tab2],
                column_config=col_cfg,
                use_container_width=True,
                hide_index=True,
                height=580
            )

    with tab3:
        st.markdown("💡 **實戰用法：** 100% 對應 TradingView 圖表右上角的 **《市場狀態指標面板》**，一次檢視所有自選股的 **纏論×SMC 24 態操作建議、WaveTrend、RSI 面積狀態與 WVF 恐慌度**。")
        if all_scanned_rows:
            df_panel = pd.DataFrame(all_scanned_rows)
            df_panel = df_panel.sort_values(by=['Priority', 'Raw_Volume'], ascending=[False, False])
            cols_tab3 = [
                "標的代號", "TV看圖", "最新收盤價", "漲跌幅(%)",
                "纏論/SMC 面板解讀", "WT快線", "平均RSI", "RSI狀態",
                "WVF恐慌", "WVF狀態", "量比(x)", "量能狀態", "日均量"
            ]
            st.dataframe(
                df_panel[cols_tab3],
                column_config=col_cfg,
                use_container_width=True,
                hide_index=True,
                height=580
            )
