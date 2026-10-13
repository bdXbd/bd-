import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import warnings
import os
import json
import time

warnings.filterwarnings("ignore")

# ─── 網頁基本設定 ───
st.set_page_config(page_title="bd の 超級指標(∠·ω<)⌒★ 股票篩選器 V6.5", page_icon="🎯", layout="wide")
st.title("🎯 bd の 超級指標(∠·ω<)⌒★ 股票篩選器 V6.5")
st.markdown("精準捕捉 **OB 訂單塊有效反彈**、**MB 恐慌修復起漲**，並搭載 **SMC 12 象限大盤解析與全域記憶功能**。")

# ─── 記憶功能升級 (全域設定檔) ───
CONFIG_FILE = "scanner_config.json"
FAV_FILE = "favorites.txt"

ALL_SIG_TYPES = [
    "🟢【多頭 CHOCH】", "🟢【多頭 BOS】", "🔴【空頭 CHOCH】", "🔴【空頭 BOS】",
    "🟢【恐慌抄底】", "🟣【極度超賣】", "🟡【Market Bottom】",
    "🟪【超賣預警】", "⚠️【頂部預警】", "🟠【WT 死叉】", "🟡【超買預警】",
    "🛡️【空頭陷阱】", "⚠️【多頭陷阱】", "🟩【OB支撐確認】", "🟥【OB壓力確認】"
]

def load_config():
    config = {
        "favorites": "SPY, QQQ, NVDA, TSLA, 2330.TW, 0050.TW, BZ=F, ^TWII, EWT, NQ=F, BTC-USD",
        "scan_mode": "1. 僅看技術指標 (預設)",
        "max_peg": 1.0,
        "max_pe": 0.0,
        "max_pb": 0.0,
        "scan_us_indices": False,
        "selected_tf_label": "4小時K (TV標準)",
        "recent_k": 2,
        "scan_days": 60,
        "target_signals": ALL_SIG_TYPES
    }
    
    if os.path.exists(FAV_FILE):
        try:
            with open(FAV_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content and not content.startswith("{"): 
                    config["favorites"] = content
        except: pass

    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved_config = json.load(f)
                config.update(saved_config)
        except: pass
        
    return config

def save_config(config_dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, ensure_ascii=False, indent=4)

# ─── 核心運算函數 ───
@st.cache_data(ttl=3600)
def get_us_indices():
    def fetch_wiki(url):
        try:
            storage_options = {'User-Agent': 'Mozilla/5.0'}
            dfs = pd.read_html(url, storage_options=storage_options)
            for df in dfs:
                if 'Symbol' in df.columns: return df['Symbol'].str.replace('.', '-', regex=False).tolist()
                if 'Ticker' in df.columns: return df['Ticker'].str.replace('.', '-', regex=False).tolist()
        except: pass
        return []
    
    sp500 = fetch_wiki("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies")
    ndx   = fetch_wiki("https://en.wikipedia.org/wiki/Nasdaq-100")
    sox   = fetch_wiki("https://en.wikipedia.org/wiki/PHLX_Semiconductor_Sector")
    combined = list(dict.fromkeys([t for t in (sp500 + ndx + sox) if isinstance(t, str) and len(t) <= 7]))
    
    if len(combined) < 100:
        backup = ["SPY", "QQQ", "DIA", "IWM", "SOXX", "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AMD", "TSM", "BTC-USD"]
        return backup, [], [], False 
    return combined, ndx, sox, True 

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

def scan_signals(df, recent_k):
    if df is None or len(df) < 40: return None
    close, high, low, open_p = df['Close'], df['High'], df['Low'], df['Open']
    n = len(df)

    h_close_22 = close.rolling(window=22).max()
    wvf = ((h_close_22 - low) / h_close_22) * 100.0
    wvf_avg, wvf_std = wvf.rolling(20).mean(), wvf.rolling(20).std(ddof=0)
    wvf_ext = (wvf >= wvf_avg + 2.0 * wvf_std) | (wvf >= wvf.rolling(50).max() * 0.85)

    diff = close.diff().fillna(0)
    pos_diff = diff.clip(lower=0)
    neg_diff = (-diff).clip(lower=0)
    
    overbuy_count = pd.Series(0.0, index=df.index)
    oversell_count = pd.Series(0.0, index=df.index)
    rsi_sum = pd.Series(0.0, index=df.index)

    for l in range(10, 21):
        den = rma(diff.abs(), l).replace(0, np.nan)
        rsi_i = (100.0 * (rma(pos_diff, l) / den)).fillna(50.0)
        rsi_sum += rsi_i
        overbuy_count += (rsi_i > 70.0).astype(float)
        oversell_count += (rsi_i < 30.0).astype(float)

    N = 11
    avg_rsi = rsi_sum / N
    per_over, per_under = (overbuy_count / N) * 100.0, 100.0 - (oversell_count / N) * 100.0
    buy_rsi_ma, sell_rsi_ma = np.zeros(n), np.zeros(n)
    buy_rsi_ma[0], sell_rsi_ma[0] = avg_rsi.iloc[0], avg_rsi.iloc[0]
    ob_r, os_r, avg_v = (overbuy_count / N).values, (oversell_count / N).values, avg_rsi.values

    for i in range(1, n):
        buy_rsi_ma[i] = buy_rsi_ma[i-1] + ob_r[i] * (avg_v[i] - buy_rsi_ma[i-1])
        sell_rsi_ma[i] = sell_rsi_ma[i-1] + os_r[i] * (avg_v[i] - sell_rsi_ma[i-1])

    rsi_red_below = (oversell_count > 0.0) & (per_under <= sell_rsi_ma)
    
    wt_ap = (high + low + close) / 3.0
    wt_esa = wt_ap.ewm(span=10, adjust=False).mean()
    wt_d = (wt_ap - wt_esa).abs().ewm(span=10, adjust=False).mean().replace(0, 0.0001)
    wt1 = ((wt_ap - wt_esa) / (0.015 * wt_d)).ewm(span=21, adjust=False).mean()
    wt2 = wt1.rolling(4).mean()

    rt_basis = close.ewm(span=55, adjust=False).mean()
    rt_vola = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1).ewm(span=55, adjust=False).mean()
    rt_upper, rt_lower = rt_basis + 4.0 * rt_vola, rt_basis - 4.0 * rt_vola

    os_ext_trig, os_warn_trig, ob_warn_trig, wt_dead_trig = False, False, False, False
    mb_fired_in_cycle = False
    vix_in_red_cycle = False
    rt_last_sig, rt_blw_cnt, rt_abv_cnt = -1000, 0, 0
    bull_obs, bear_obs, latest_signals = [], [], []
    last_ph, last_pl, ph_idx, pl_idx = float('inf'), -float('inf'), -1, -1

    last_wt_ph_idx = -1
    last_wt_ph_val = -float('inf')
    last_wt_ph_price = -float('inf')
    
    internal_trend = 0
    last_smc_tag = "BOS"

    for i in range(2, n):
        if low.iloc[i] < rt_lower.iloc[i]: rt_blw_cnt += 1
        else: rt_blw_cnt = 0
        if high.iloc[i] > rt_upper.iloc[i]: rt_abv_cnt += 1
        else: rt_abv_cnt = 0

        is_red_area = per_under.iloc[i] < 100.0
        was_red_area = per_under.iloc[i-1] < 100.0 if i > 0 else False
        
        if is_red_area and not was_red_area:
            vix_in_red_cycle = False
            
        if is_red_area and wvf_ext.iloc[i]:
            vix_in_red_cycle = True

        if is_red_area: 
            mb_fired_in_cycle = False
            
        if wt1.iloc[i] > -60.0: os_ext_trig = False
        if wt1.iloc[i] > -53.0: os_warn_trig = False
        if wt1.iloc[i] <= 53.0: ob_warn_trig = False
        if wt1.iloc[i] <= 60.0: wt_dead_trig = False

        curr_sigs = []
        t_str = df.index[i].strftime('%m/%d %H:%M') 
        c_p = f"{close.iloc[i]:.2f}"                

        size = 5
        if i >= size * 2:
            if max([high.iloc[j] for j in range(i - size*2, i + 1)]) == high.iloc[i - size]:
                last_ph, ph_idx = high.iloc[i - size], i - size
            if min([low.iloc[j] for j in range(i - size*2, i + 1)]) == low.iloc[i - size]:
                last_pl, pl_idx = low.iloc[i - size], i - size

            if close.iloc[i] > last_ph and ph_idx != -1:
                is_choch = (internal_trend == -1)
                internal_trend = 1
                last_smc_tag = "CHOCH" if is_choch else "BOS"
                if i >= n - recent_k:
                    curr_sigs.append(f"🟢【多頭 {last_smc_tag}】({t_str} 破 {last_ph:.2f})")
                
                start_idx = max(0, pl_idx)
                ob_idx, min_l = start_idx, low.iloc[start_idx]
                for j in range(start_idx, i + 1):
                    if low.iloc[j] < min_l: min_l, ob_idx = low.iloc[j], j
                bull_obs.append({'top': high.iloc[ob_idx], 'bot': low.iloc[ob_idx]})
                last_ph = float('inf')

            if close.iloc[i] < last_pl and pl_idx != -1:
                is_choch = (internal_trend == 1)
                internal_trend = -1
                last_smc_tag = "CHOCH" if is_choch else "BOS"
                if i >= n - recent_k:
                    curr_sigs.append(f"🔴【空頭 {last_smc_tag}】({t_str} 破 {last_pl:.2f})")
                
                start_idx = max(0, ph_idx)
                ob_idx, max_h = start_idx, high.iloc[start_idx]
                for j in range(start_idx, i + 1):
                    if high.iloc[j] > max_h: max_h, ob_idx = high.iloc[j], j
                bear_obs.append({'top': high.iloc[ob_idx], 'bot': low.iloc[ob_idx]})
                last_pl = -float('inf')

            wt_slice = wt1.iloc[i - size*2 : i + 1].values
            left_max = np.max(wt_slice[:size])
            right_max = np.max(wt_slice[size+1:])
            mid_val = wt_slice[size]
            
            if mid_val >= left_max and mid_val > right_max:
                curr_wt_ph_val = mid_val
                curr_wt_ph_price = high.iloc[i - size]
                if last_wt_ph_idx != -1:
                    bars_since = (i - size) - last_wt_ph_idx
                    if 5 <= bars_since <= 60:
                        if curr_wt_ph_price > last_wt_ph_price and curr_wt_ph_val < last_wt_ph_val:
                            curr_sigs.append(f"⚠️【頂部預警】({t_str} @ {c_p})")
                last_wt_ph_idx = i - size
                last_wt_ph_val = curr_wt_ph_val
                last_wt_ph_price = curr_wt_ph_price

        # 即時清理失效的 OB (跌破支撐 / 突破壓力)
        bull_obs = [ob for ob in bull_obs if close.iloc[i] >= ob['bot']][-5:]
        bear_obs = [ob for ob in bear_obs if close.iloc[i] <= ob['top']][-5:]

        if (wt1.iloc[i] > wt2.iloc[i]) and (wt1.iloc[i-1] <= wt2.iloc[i-1]) and (wt1.iloc[i-1] <= -60.0) and wvf_ext.iloc[i-1] and rsi_red_below.iloc[i-1]: 
            curr_sigs.append(f"🟢【恐慌抄底】({t_str} @ {c_p})")
            
        if (wt1.iloc[i] <= -60.0) and wvf_ext.iloc[i] and rsi_red_below.iloc[i] and not os_ext_trig:
            curr_sigs.append(f"🟣【極度超賣】({t_str} @ {c_p})")
            os_ext_trig = True
            
        wt_golden_cross_mb = (wt1.iloc[i] > wt2.iloc[i]) and (wt1.iloc[i-1] <= wt2.iloc[i-1])
        red_is_zero_now = (per_under.iloc[i] == 100.0)
        red_was_present = per_under.iloc[max(0, i-3):i].min() < 100.0
        
        if wt_golden_cross_mb and red_is_zero_now and red_was_present and vix_in_red_cycle and not mb_fired_in_cycle:
            curr_sigs.append(f"🟡【Market Bottom】({t_str} @ {c_p})")
            mb_fired_in_cycle = True
            
        if (wt1.iloc[i] <= -53.0) and wvf_ext.iloc[i] and not os_warn_trig:
            curr_sigs.append(f"🟪【超賣預警】({t_str} @ {c_p})")
            os_warn_trig = True
            
        wt_dead_cross = (wt1.iloc[i] < wt2.iloc[i]) and (wt1.iloc[i-1] >= wt2.iloc[i-1])
        green_area_was_0 = (per_over.iloc[i] == 0.0) or (per_over.iloc[i-1] == 0.0) or (per_over.iloc[i-2] == 0.0)
        if wt_dead_cross and green_area_was_0 and (wt1.iloc[i-1] > 60.0) and not wt_dead_trig:
            curr_sigs.append(f"🟠【WT 死叉】({t_str} @ {c_p})")
            wt_dead_trig = True
            
        if (wt1.iloc[i] >= 53.0) and not ob_warn_trig:
            curr_sigs.append(f"🟡【超買預警】({t_str} @ {c_p})")
            ob_warn_trig = True

        can_fire_rt = (i - rt_last_sig) >= 10
        if (close.iloc[i] > rt_lower.iloc[i]) and ((low.iloc[i] < rt_lower.iloc[i] and close.iloc[i-1] > rt_lower.iloc[i] and rt_blw_cnt <= 10) or (close.iloc[i-1] < rt_lower.iloc[i] and rt_blw_cnt <= 10)) and can_fire_rt and (oversell_count.iloc[i] > 0):
            curr_sigs.append(f"🛡️【空頭陷阱】({t_str} @ {c_p})")
            rt_last_sig = i
        if (close.iloc[i] < rt_upper.iloc[i]) and ((high.iloc[i] > rt_upper.iloc[i] and close.iloc[i-1] < rt_upper.iloc[i] and rt_abv_cnt <= 10) or (close.iloc[i-1] > rt_upper.iloc[i] and rt_abv_cnt <= 10)) and can_fire_rt and (overbuy_count.iloc[i] > 0):
            curr_sigs.append(f"⚠️【多頭陷阱】({t_str} @ {c_p})")
            rt_last_sig = i

        if i >= n - recent_k:
            # 【Python 版邏輯升級】完美同步 TradingView 版的「即時反應 + 綠紅K嚴格確認」
            for ob in bull_obs:
                is_touching = (low.iloc[i] <= ob['top']) or (close.iloc[i-1] <= ob['top'] and close.iloc[i-1] >= ob['bot'])
                is_confirmed = (close.iloc[i] > ob['top'])
                is_trend_confirmed = (close.iloc[i] > open_p.iloc[i]) # 嚴格要求收綠K
                if is_touching and is_confirmed and is_trend_confirmed:
                    curr_sigs.append(f"🟩【OB支撐確認】({t_str} 守穩 {ob['top']:.2f})")
            
            for ob in bear_obs:
                is_touching = (high.iloc[i] >= ob['bot']) or (close.iloc[i-1] >= ob['bot'] and close.iloc[i-1] <= ob['top'])
                is_confirmed = (close.iloc[i] < ob['bot'])
                is_trend_confirmed = (close.iloc[i] < open_p.iloc[i]) # 嚴格要求收紅K
                if is_touching and is_confirmed and is_trend_confirmed:
                    curr_sigs.append(f"🟥【OB壓力確認】({t_str} 受阻 {ob['bot']:.2f})")
            
            for sig in curr_sigs:
                if sig not in latest_signals: latest_signals.append(sig)

    return {
        "標的代號": df.name if hasattr(df, 'name') else "", 
        "觸發指標通知": " ｜ ".join(latest_signals) if latest_signals else "",
        "SMC_Trend": internal_trend,
        "SMC_Tag": last_smc_tag
    }

def format_vol(val):
    if val == 0 or pd.isna(val): return "N/A"
    if val >= 1e9: return f"{val/1e9:.2f} B"
    if val >= 1e6: return f"{val/1e6:.2f} M"
    if val >= 1e3: return f"{val/1e3:.2f} K"
    return f"{val:.0f}"

# ─── 網頁側邊欄設定 (載入記憶) ───
user_config = load_config()

st.sidebar.header("⚙️ 雷達掃描設定")

st.sidebar.subheader("📌 收藏標的清單")
fav_input = st.sidebar.text_area(
    "請輸入股票代號 (用半形逗號分隔)：",
    value=user_config["favorites"],
    height=150,
    help="台股請加 .TW (如 2330.TW)。大盤 ^TWII，台期貨替身 EWT。"
)

st.sidebar.divider()

with st.sidebar.expander("📊 掃描模式與基本面過濾", expanded=True):
    scan_options = [
        "1. 僅看技術指標 (預設)", 
        "2. 聯集 (技術觸發 OR 基本面達標)", 
        "3. 交集 (技術觸發 AND 基本面達標)", 
        "4. 僅看基本面 (無視技術指標)"
    ]
    s_idx = scan_options.index(user_config["scan_mode"]) if user_config["scan_mode"] in scan_options else 0
    scan_mode = st.radio("選擇掃描模式：", scan_options, index=s_idx)
    
    st.markdown("---")
    max_peg = st.number_input("市賺率 (PEG) 低於", min_value=0.0, value=float(user_config["max_peg"]), step=0.1, help="設 0 為不限制")
    max_pe = st.number_input("本益比 (P/E) 低於", min_value=0.0, value=float(user_config["max_pe"]), step=1.0, help="設 0 為不限制")
    max_pb = st.number_input("股價淨值比 (P/B) 低於", min_value=0.0, value=float(user_config["max_pb"]), step=0.1, help="設 0 為不限制")

st.sidebar.divider()

st.sidebar.subheader("🌍 全市場掃描擴充")
scan_us_indices = st.sidebar.checkbox("同步掃描美股三大指數 (SPY,QQQ,SOXX)", value=bool(user_config["scan_us_indices"]))

st.sidebar.subheader("🎯 訊號與時間參數")
tf_options = {"15分K": "15m", "1小時K": "1h", "4小時K (TV標準)": "4h", "日K": "1d"}
tf_opts_keys = list(tf_options.keys())
tf_idx = tf_opts_keys.index(user_config["selected_tf_label"]) if user_config["selected_tf_label"] in tf_opts_keys else 2
selected_tf_label = st.sidebar.selectbox("⏳ 選擇時間框架", tf_opts_keys, index=tf_idx)
selected_tf = tf_options[selected_tf_label]

recent_k = st.sidebar.number_input("個股掃描近 N 根 K線", min_value=1, max_value=10, value=int(user_config["recent_k"]))

max_days = 60 if selected_tf in ["15m"] else (730 if selected_tf in ["1h", "4h"] else 1000)
default_days = max(10, min(int(user_config["scan_days"]), max_days))
scan_days = st.sidebar.slider("載入歷史天數", min_value=10, max_value=max_days, value=default_days)

st.sidebar.subheader("🔍 指標過濾器")
valid_targets = [s for s in user_config["target_signals"] if s in ALL_SIG_TYPES]
target_signals = st.sidebar.multiselect("保留含有以下訊號的標的 (若清空則顯示全部)", ALL_SIG_TYPES, default=valid_targets)

# ─── 儲存設定按鈕 ───
st.sidebar.markdown("---")
if st.sidebar.button("💾 儲存所有設定檔", use_container_width=True):
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
        "target_signals": target_signals
    }
    save_config(new_cfg)
    st.sidebar.success("✅ 所有設定參數已成功記憶！")
    time.sleep(0.6)
    st.rerun()

scan_btn = st.sidebar.button("🚀 立即啟動掃描", use_container_width=True)

# ─── 主程式掃描執行 ───
if scan_btn:
    favorites = [t.strip().upper() for t in fav_input.split(",") if t.strip()]
    all_tickers = favorites.copy()
    
    _, ndx_list, sox_list, _ = get_us_indices() 
    
    if scan_us_indices:
        with st.spinner("🔄 正在取得美股三大指數成分股清單..."):
            us_stocks, _, _, success = get_us_indices()
            if success:
                st.success("✅ 成功從維基百科取得美股清單！")
            else:
                st.warning("⚠️ 雲端主機被維基百科阻擋爬蟲，已切換至備用清單！")
            all_tickers.extend(us_stocks)
    
    all_tickers = list(dict.fromkeys(all_tickers)) 
    
    if not all_tickers:
        st.error("❌ 收藏清單是空的！")
        st.stop()

    fetch_interval = "1h" if selected_tf == "4h" else selected_tf

    # ─── 大盤 12 象限動能矩陣分析 ───
    st.markdown("---")
    st.subheader("🚥 大盤環境與板塊操作建議 (SMC 結構 × 動能 12 象限)")
    
    barometer_tickers = ["QQQ", "SOXX", "SPY", "^TWII", "BTC-USD"]
    
    board_desc_map = {
        "SPY": "美股全市場個股",
        "QQQ": "科技板塊個股",
        "SOXX": "半導體及硬體個股",
        "^TWII": "台股大盤及相關個股",
        "BTC-USD": "加密貨幣板塊"
    }
    
    bull_kws_map = {"恐慌抄底": "恐慌抄底", "極度超賣": "極度超賣", "Market Bottom": "Market Bottom", "超賣預警": "超賣預警", "空頭陷阱": "空頭陷阱", "支撐確認": "OB支撐", "多頭 CHOCH": "多頭 CHOCH", "多頭 BOS": "多頭 BOS"}
    bear_kws_map = {"頂部預警": "頂部預警", "WT 死叉": "WT死叉", "超買預警": "超買預警", "多頭陷阱": "多頭陷阱", "壓力確認": "OB壓力", "空頭 CHOCH": "空頭 CHOCH", "空頭 BOS": "空頭 BOS"}
    
    advices_matrix = {
        ("🟢多頭BOS", "多"): ("🔥 主升浪爆發", "雙多共振，逢低做多，多單抱牢"),
        ("🟢多頭BOS", "空"): ("⚠️ 多頭遇壓", "主升浪遇阻 / 動能背離，防守或減碼"),
        ("🟢多頭BOS", "平"): ("🟢 高位震盪", "多頭趨勢延續，蓄勢待發"),
        ("🟢多頭CHOCH", "多"): ("🔥 右側起漲", "結構扭轉且動能共振，積極建倉"),
        ("🟢多頭CHOCH", "空"): ("⚠️ 反彈遇阻", "初升浪遇阻，防二次探底"),
        ("🟢多頭CHOCH", "平"): ("🟢 底部築底", "結構已轉多，留意突破方向"),
        ("🔴空頭CHOCH", "多"): ("⚠️ 跌深反抽", "留意空頭回馬槍 (誘多)，搶短慎行"),
        ("🔴空頭CHOCH", "空"): ("🔴 頂部確立", "右側做頭確認，逢高逃頂 / 順勢建空"),
        ("🔴空頭CHOCH", "平"): ("🔴 頂部震盪", "高位結構破壞，防守觀望為主"),
        ("🔴空頭BOS", "多"): ("⚠️ 探底背離", "主跌段動能竭盡，摸底需嚴設停損"),
        ("🔴空頭BOS", "空"): ("🔴 主跌浪崩盤", "雙空共振，空單抱牢 / 順勢高空"),
        ("🔴空頭BOS", "平"): ("🔴 低位磨底", "跌勢中繼整理，尚未明確見底"),
    }
    
    with st.spinner("🔄 正在計算 12 象限矩陣..."):
        b_data = yf.download(barometer_tickers, period=f"{scan_days}d", interval=fetch_interval, group_by='ticker', progress=False, threads=True)
        b_cols = st.columns(len(barometer_tickers))
        
        for idx, b_tick in enumerate(barometer_tickers):
            try:
                df_b = b_data[b_tick] if len(barometer_tickers) > 1 else b_data
                df_b = df_b.dropna(subset=['Close'])
                if len(df_b) > 40:
                    df_b.name = b_tick
                    if selected_tf == "4h":
                        df_proc_b = resample_to_tv_4h(df_b)
                    else:
                        df_proc_b = df_b.copy()
                        if df_proc_b.index.tz is None:
                            df_proc_b.index = pd.to_datetime(df_proc_b.index).tz_localize('UTC').tz_convert('America/New_York')
                        else:
                            df_proc_b.index = df_proc_b.index.tz_convert('America/New_York')
                    
                    b_res = scan_signals(df_proc_b, 14)
                    
                    bull_count, bear_count = 0, 0
                    bull_detail, bear_detail = {}, {}
                    
                    if b_res and b_res["觸發指標通知"]:
                        for sig in b_res["觸發指標通知"].split(" ｜ "):
                            for kw, v in bull_kws_map.items():
                                if kw in sig:
                                    bull_count += 1
                                    bull_detail[v] = True
                            for kw, v in bear_kws_map.items():
                                if kw in sig:
                                    bear_count += 1
                                    bear_detail[v] = True
                    
                    mtn_status = "平"
                    mtn_color = "gray"
                    if bull_count > bear_count:
                        mtn_status = "多"
                        mtn_color = "#00c853"
                    elif bear_count > bull_count:
                        mtn_status = "空"
                        mtn_color = "#ff5252"
                        
                    smc_trend = b_res["SMC_Trend"] if b_res else 0
                    smc_tag = b_res["SMC_Tag"] if b_res else "BOS"
                    
                    smc_prefix = "🟢多頭" if smc_trend == 1 else "🔴空頭"
                    smc_full_tag = f"{smc_prefix}{smc_tag}"
                    
                    action_title, action_desc = advices_matrix.get((smc_full_tag, mtn_status), ("⚪ 盤整觀望", "多空動能不明確，建議觀望"))
                    
                    # 顏色配置
                    card_color = "#f8f9fa"
                    if "🔥" in action_title or "🟢" in action_title: card_color = "#e8f5e9"
                    elif "🔴" in action_title: card_color = "#ffebee"
                    elif "⚠️" in action_title: card_color = "#fff8e1"
                    
                    bull_desc = " ".join([k for k in bull_detail.keys()])
                    bear_desc = " ".join([k for k in bear_detail.keys()])
                    
                    if not bull_desc and not bear_desc: sig_text = "無明顯訊號"
                    else:
                        b_txt = f"<span style='color:#00c853'>{bull_desc}</span>" if bull_desc else ""
                        s_txt = f"<span style='color:#ff5252'>{bear_desc}</span>" if bear_desc else ""
                        sig_text = " ".join([t for t in [b_txt, s_txt] if t])
                    
                    board_name = board_desc_map.get(b_tick, b_tick)
                    
                    with b_cols[idx]:
                        st.markdown(f"""
                        <div style="background-color: {card_color}; padding: 10px; border-radius: 8px; border: 1px solid #ddd; height: 100%;">
                            <h4 style="margin:0; text-align:center;">{b_tick}</h4>
                            <p style="margin:0; text-align:center; font-size:12px; color:#666;">{board_name}</p>
                            <hr style="margin: 8px 0;">
                            <div style="text-align:center;">
                                <span style="font-weight:bold;">結構：</span>{smc_full_tag} <br>
                                <span style="font-weight:bold;">動能：</span><span style="color:{mtn_color}; font-weight:bold;">{mtn_status}</span>
                            </div>
                            <div style="text-align:center; margin-top: 5px; font-size: 11px;">
                                {sig_text}
                            </div>
                            <hr style="margin: 8px 0;">
                            <div style="text-align:center;">
                                <strong>{action_title}</strong><br>
                                <span style="font-size:12px;">{action_desc}</span>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
            except Exception as e:
                with b_cols[idx]:
                    st.error(f"{b_tick} 資料讀取失敗")
                    
    st.markdown("---")
    
    # ─── 基本面資料抓取模組 ───
    fundamental_data = {}
    if scan_mode != "1. 僅看技術指標 (預設)":
        with st.spinner("🔄 正在擷取基本面資料 (PEG, PE, PB)..."):
            progress_bar = st.progress(0)
            for i, ticker in enumerate(all_tickers):
                try:
                    info = yf.Ticker(ticker).info
                    fundamental_data[ticker] = {
                        "PEG": info.get("pegRatio", np.nan),
                        "PE": info.get("trailingPE", np.nan),
                        "PB": info.get("priceToBook", np.nan),
                        "Sector": info.get("sector", "N/A")
                    }
                except:
                    fundamental_data[ticker] = {"PEG": np.nan, "PE": np.nan, "PB": np.nan, "Sector": "N/A"}
                progress_bar.progress((i + 1) / len(all_tickers))
            progress_bar.empty()
    else:
        for ticker in all_tickers:
            fundamental_data[ticker] = {"PEG": np.nan, "PE": np.nan, "PB": np.nan, "Sector": "N/A"}

    # ─── 技術指標資料抓取模組 ───
    tech_data = {}
    if scan_mode != "4. 僅看基本面 (無視技術指標)":
        with st.spinner(f"🔄 正在下載歷史 K線資料... (時間框架: {selected_tf_label}, 週期: {scan_days}天)"):
            data = yf.download(all_tickers, period=f"{scan_days}d", interval=fetch_interval, group_by='ticker', progress=False, threads=True)
    
        with st.spinner("🔄 正在進行 SMC 結構與 WaveTrend 動能運算..."):
            progress_bar = st.progress(0)
            for i, ticker in enumerate(all_tickers):
                try:
                    df = data[ticker] if len(all_tickers) > 1 else data
                    df = df.dropna(subset=['Close'])
                    
                    if len(df) > 40:
                        df.name = ticker
                        if selected_tf == "4h":
                            df_proc = resample_to_tv_4h(df)
                        else:
                            df_proc = df.copy()
                            if df_proc.index.tz is None:
                                df_proc.index = pd.to_datetime(df_proc.index).tz_localize('UTC').tz_convert('America/New_York')
                            else:
                                df_proc.index = df_proc.index.tz_convert('America/New_York')
                                
                        result = scan_signals(df_proc, recent_k)
                        if result:
                            tech_data[ticker] = {
                                "Signals": result["觸發指標通知"],
                                "SMC_Trend": result["SMC_Trend"],
                                "SMC_Tag": result["SMC_Tag"]
                            }
                except Exception as e:
                    pass
                progress_bar.progress((i + 1) / len(all_tickers))
            progress_bar.empty()

    # ─── 最終資料過濾與整併 ───
    final_results = []
    
    with st.spinner("🔄 正在進行綜合篩選與條件比對..."):
        for ticker in all_tickers:
            fund = fundamental_data.get(ticker, {"PEG": np.nan, "PE": np.nan, "PB": np.nan, "Sector": "N/A"})
            tech = tech_data.get(ticker, {"Signals": "", "SMC_Trend": 0, "SMC_Tag": "BOS"})
            
            # 判斷基本面是否過關
            fund_pass = True
            if max_peg > 0: fund_pass = fund_pass and (not pd.isna(fund["PEG"]) and fund["PEG"] < max_peg)
            if max_pe > 0: fund_pass = fund_pass and (not pd.isna(fund["PE"]) and fund["PE"] < max_pe)
            if max_pb > 0: fund_pass = fund_pass and (not pd.isna(fund["PB"]) and fund["PB"] < max_pb)
            
            # 判斷技術面是否過關 (有無訊號)
            has_signals = bool(tech["Signals"])
            
            # 若有指定目標訊號，過濾不符的
            if has_signals and len(target_signals) > 0:
                sig_list = tech["Signals"].split(" ｜ ")
                match = False
                for t_sig in target_signals:
                    for s in sig_list:
                        if t_sig in s:
                            match = True
                            break
                    if match: break
                has_signals = match
            
            is_match = False
            if scan_mode == "1. 僅看技術指標 (預設)":
                is_match = has_signals
            elif scan_mode == "2. 聯集 (技術觸發 OR 基本面達標)":
                is_match = has_signals or (fund_pass and (max_peg > 0 or max_pe > 0 or max_pb > 0))
            elif scan_mode == "3. 交集 (技術觸發 AND 基本面達標)":
                is_match = has_signals and fund_pass
            elif scan_mode == "4. 僅看基本面 (無視技術指標)":
                is_match = fund_pass and (max_peg > 0 or max_pe > 0 or max_pb > 0)
                
            if is_match:
                # 附加標籤 (區分清單來源)
                tags = []
                if ticker in favorites: tags.append("⭐ 我的收藏")
                if ticker in ndx_list: tags.append("💡 NDX 100")
                if ticker in sox_list: tags.append("💻 SOX 半導體")
                if ticker not in favorites and ticker not in ndx_list and ticker not in sox_list: tags.append("🏛️ S&P 500")
                
                smc_prefix = "🟢 多頭" if tech["SMC_Trend"] == 1 else "🔴 空頭" if tech["SMC_Trend"] == -1 else "⚪ 震盪"
                smc_state = f"{smc_prefix} {tech['SMC_Tag']}"
                
                final_results.append({
                    "標的代號": ticker,
                    "清單來源": " / ".join(tags),
                    "產業板塊": fund["Sector"],
                    "SMC 結構": smc_state,
                    "觸發指標通知 (近 {} 根 K線)".format(recent_k): tech["Signals"],
                    "PEG": fund["PEG"],
                    "P/E": fund["PE"],
                    "P/B": fund["PB"]
                })

    # ─── 顯示最終結果 ───
    if final_results:
        df_result = pd.DataFrame(final_results)
        
        # 依照 SMC 趨勢排序 (多頭優先)
        df_result['sort_key'] = df_result['SMC 結構'].apply(lambda x: 0 if '🟢' in x else (1 if '⚪' in x else 2))
        df_result = df_result.sort_values(by=['sort_key', '標的代號']).drop(columns=['sort_key']).reset_index(drop=True)
        
        st.success(f"🎉 篩選完成！共找到 {len(df_result)} 檔符合條件的標的。")
        
        # 格式化輸出
        st.dataframe(
            df_result.style.format({
                "PEG": "{:.2f}",
                "P/E": "{:.2f}",
                "P/B": "{:.2f}"
            }),
            use_container_width=True,
            height=600
        )
    else:
        st.warning("⚠️ 沒有找到符合條件的標的，請嘗試放寬篩選條件。")

st.markdown("---")
st.markdown("💡 **提示：** 本工具內建 TV 標準 4小時K 線合成邏輯（美東時間 09:30 與 13:30），保證訊號與 TradingView 主圖完全同步。SMC 分析支援最新 12 象限矩陣與 OB 支撐壓力精準回踩確認。")
