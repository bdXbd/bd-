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
st.set_page_config(page_title="bd の 超級指標(∠·ω )⌒★ 股票篩選器 V5.8", page_icon="🎯", layout="wide")
st.title("🎯 bd の 超級指標(∠·ω )⌒★ 股票篩選器 V5.8")
st.markdown("精準捕捉 **OB 訂單塊**、**WT 恐慌轉折**，並搭載 **宏觀大盤多空計分板 (訊號防連發鎖定版)**。")

# ─── 記憶功能 (回歸極簡純收藏) ───
FAV_FILE = "favorites.txt"
DEFAULT_FAVS = "SPY, QQQ, NVDA, TSLA, 2330.TW, 0050.TW, BZ=F, ^TWII, EWT, NQ=F, BTC-USD"

def load_favorites():
    if os.path.exists(FAV_FILE):
        try:
            with open(FAV_FILE, "r", encoding="utf-8") as f:
                content = f.read().strip()
                if content and not content.startswith("{"): return content
        except: pass
    return DEFAULT_FAVS

def save_favorites(fav_str):
    with open(FAV_FILE, "w", encoding="utf-8") as f:
        f.write(fav_str)

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
    rt_last_sig, rt_blw_cnt, rt_abv_cnt = -1000, 0, 0
    bull_obs, bear_obs, latest_signals = [], [], []
    last_ph, last_pl, ph_idx, pl_idx = float('inf'), -float('inf'), -1, -1

    last_wt_ph_idx = -1
    last_wt_ph_val = -float('inf')
    last_wt_ph_price = -float('inf')

    for i in range(2, n):
        if low.iloc[i] < rt_lower.iloc[i]: rt_blw_cnt += 1
        else: rt_blw_cnt = 0
        if high.iloc[i] > rt_upper.iloc[i]: rt_abv_cnt += 1
        else: rt_abv_cnt = 0

        # 當跌入紅區時，解鎖 Market Bottom 觸發器
        if per_under.iloc[i] < 100.0: 
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
                start_idx = max(0, pl_idx)
                ob_idx, min_l = start_idx, low.iloc[start_idx]
                for j in range(start_idx, i + 1):
                    if low.iloc[j] < min_l: min_l, ob_idx = low.iloc[j], j
                bull_obs.append({'top': high.iloc[ob_idx], 'bot': low.iloc[ob_idx]})
                last_ph = float('inf')

            if close.iloc[i] < last_pl and pl_idx != -1:
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

        bull_obs = [ob for ob in bull_obs if close.iloc[i] >= ob['bot']][-5:]
        bear_obs = [ob for ob in bear_obs if close.iloc[i] <= ob['top']][-5:]

        if (wt1.iloc[i] > wt2.iloc[i]) and (wt1.iloc[i-1] <= wt2.iloc[i-1]) and (wt1.iloc[i-1] <= -60.0) and wvf_ext.iloc[i-1] and rsi_red_below.iloc[i-1]: 
            curr_sigs.append(f"🟢【恐慌抄底】({t_str} @ {c_p})")
            
        if (wt1.iloc[i] <= -60.0) and wvf_ext.iloc[i] and rsi_red_below.iloc[i] and not os_ext_trig:
            curr_sigs.append(f"🟣【極度超賣】({t_str} @ {c_p})")
            os_ext_trig = True
            
        # ── V5.8: Market Bottom 防連發鎖定機制 ──
        wt_golden_cross_mb = (wt1.iloc[i] > wt2.iloc[i]) and (wt1.iloc[i-1] <= wt2.iloc[i-1])
        red_area_was_0 = (per_under.iloc[i] == 100.0) or (per_under.iloc[i-1] == 100.0) or (per_under.iloc[i-2] == 100.0)
        had_red_area = per_under.iloc[max(0, i-9):i+1].min() < 100.0
        
        if wt_golden_cross_mb and red_area_was_0 and had_red_area and not mb_fired_in_cycle:
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
            for ob in bull_obs:
                if low.iloc[i-1] >= ob['top'] and low.iloc[i] <= ob['top']: 
                    curr_sigs.append(f"🟩【OB支撐回踩】({t_str} 踩 {ob['top']:.2f})")
                if close.iloc[i-1] >= ob['bot'] and close.iloc[i] < ob['bot']:
                    curr_sigs.append(f"⚠️【跌破OB支撐】({t_str} 破 {ob['bot']:.2f})")
            
            for ob in bear_obs:
                if high.iloc[i-1] <= ob['bot'] and high.iloc[i] >= ob['bot']: 
                    curr_sigs.append(f"🟥【OB壓力測試】({t_str} 測 {ob['bot']:.2f})")
                if close.iloc[i-1] <= ob['top'] and close.iloc[i] > ob['top']:
                    curr_sigs.append(f"🚀【突破OB壓力】({t_str} 破 {ob['top']:.2f})")
            
            for sig in curr_sigs:
                if sig not in latest_signals: latest_signals.append(sig)

    if latest_signals:
        return {"標的代號": df.name if hasattr(df, 'name') else "", "觸發指標通知": " ｜ ".join(latest_signals)}
    return None

def format_vol(val):
    if val == 0 or pd.isna(val): return "N/A"
    if val >= 1e9: return f"{val/1e9:.2f} B"
    if val >= 1e6: return f"{val/1e6:.2f} M"
    if val >= 1e3: return f"{val/1e3:.2f} K"
    return f"{val:.0f}"

# ─── 網頁側邊欄設定 ───
st.sidebar.header("⚙️ 雷達掃描設定")

st.sidebar.subheader("📌 收藏標的清單")
fav_input = st.sidebar.text_area(
    "請輸入股票代號 (用半形逗號分隔)：",
    value=load_favorites(),
    height=150,
    help="台股請加 .TW (如 2330.TW)。大盤 ^TWII，台期貨替身 EWT。"
)

if st.sidebar.button("💾 儲存清單"):
    save_favorites(fav_input)
    st.sidebar.success("清單已儲存！")
    time.sleep(0.5)
    st.rerun()

st.sidebar.divider()

with st.sidebar.expander("📊 掃描模式與基本面過濾", expanded=True):
    scan_mode = st.radio(
        "選擇掃描模式：",
        [
            "1. 僅看技術指標 (預設)", 
            "2. 聯集 (技術觸發 OR 基本面達標)", 
            "3. 交集 (技術觸發 AND 基本面達標)", 
            "4. 僅看基本面 (無視技術指標)"
        ]
    )
    
    st.markdown("---")
    max_peg = st.number_input("市賺率 (PEG) 低於", min_value=0.0, value=1.0, step=0.1, help="設 0 為不限制")
    max_pe = st.number_input("本益比 (P/E) 低於", min_value=0.0, value=0.0, step=1.0, help="設 0 為不限制")
    max_pb = st.number_input("股價淨值比 (P/B) 低於", min_value=0.0, value=0.0, step=0.1, help="設 0 為不限制")

st.sidebar.divider()

st.sidebar.subheader("🌍 全市場掃描擴充")
scan_us_indices = st.sidebar.checkbox("同步掃描美股三大指數 (SPY,QQQ,SOXX)", value=False)

st.sidebar.subheader("🎯 訊號與時間參數")
tf_options = {"15分K": "15m", "1小時K": "1h", "4小時K (TV標準)": "4h", "日K": "1d"}
selected_tf_label = st.sidebar.selectbox("⏳ 選擇時間框架", list(tf_options.keys()), index=2)
selected_tf = tf_options[selected_tf_label]

recent_k = st.sidebar.number_input("個股掃描近 N 根 K線", min_value=1, max_value=10, value=2)

max_days = 60 if selected_tf in ["15m"] else (730 if selected_tf in ["1h", "4h"] else 1000)
default_days = min(60, max_days)
scan_days = st.sidebar.slider("載入歷史天數", min_value=10, max_value=max_days, value=default_days)

st.sidebar.subheader("🔍 指標過濾器")
all_sig_types = [
    "🟢【恐慌抄底】", "🟣【極度超賣】", "🟡【Market Bottom】",
    "🟪【超賣預警】", "⚠️【頂部預警】", "🟠【WT 死叉】", "🟡【超買預警】",
    "🛡️【空頭陷阱】", "⚠️【多頭陷阱】", "🟩【OB支撐回踩】", "🟥【OB壓力測試】",
    "🚀【突破OB壓力】", "⚠️【跌破OB支撐】"
]
target_signals = st.sidebar.multiselect("保留含有以下訊號的標的 (若清空則顯示全部)", all_sig_types, default=all_sig_types)

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

    # ─── 大盤風向球預警系統 (明確警告旗下個股操作) ───
    st.markdown("---")
    st.subheader("🚥 大盤環境與板塊操作建議 (回看 14 根 K 線)")
    
    barometer_tickers = ["QQQ", "SOXX", "SPY", "^TWII", "BTC-USD"]
    
    board_desc_map = {
        "SPY": "美股全市場個股",
        "QQQ": "科技板塊個股",
        "SOXX": "半導體及硬體個股",
        "^TWII": "台股大盤及相關個股",
        "BTC-USD": "加密貨幣板塊"
    }
    
    bull_kws_map = {
        "恐慌抄底": "恐慌抄底", "極度超賣": "極度超賣", "Market Bottom": "Market Bottom",
        "超賣預警": "超賣預警", "空頭陷阱": "空頭陷阱", "支撐回踩": "OB支撐", "突破OB壓力": "突破OB壓力"
    }
    bear_kws_map = {
        "頂部預警": "頂部預警", "WT 死叉": "WT死叉", "超買預警": "超買預警",
        "多頭陷阱": "多頭陷阱", "壓力測試": "OB壓力", "跌破OB支撐": "跌破OB支撐"
    }
    
    with st.spinner("🔄 正在分析大盤宏觀風向..."):
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
                    
                    board_name = board_desc_map.get(b_tick, "相關個股")
                    
                    with b_cols[idx]:
                        st.markdown(f"**{b_tick}**")
                        if bear_count > bull_count:
                            st.error(f"🔴 {board_name}偏空\n\n**謹慎做多** (空{bear_count}|多{bull_count})")
                        elif bull_count > bear_count:
                            st.success(f"🟢 {board_name}偏多\n\n**謹慎做空** (多{bull_count}|空{bear_count})")
                        elif bull_count > 0 and bear_count > 0 and bull_count == bear_count:
                            st.warning(f"⚖️ {board_name}震盪\n\n**多空交戰洗盤** (各{bull_count})")
                        else:
                            st.info(f"⚪ 趨勢中性\n\n(近14K無極端訊號)")
                            
                        if bull_count > 0 or bear_count > 0:
                            with st.expander("詳細計分板與時間軸"):
                                if bull_count > 0:
                                    st.markdown("**🟢 多方訊號:**")
                                    for k, v in bull_detail.items(): st.caption(f"• {k}: **{v}**次")
                                if bear_count > 0:
                                    st.markdown("**🔴 空方訊號:**")
                                    for k, v in bear_detail.items(): st.caption(f"• {k}: **{v}**次")
                                st.markdown("---")
                                st.markdown("**🕒 觸發時間軸:**")
                                for s in sigs: st.caption(s)
            except:
                with b_cols[idx]:
                    st.markdown(f"**{b_tick}**")
                    st.write("讀取失敗")
                    
    st.markdown("---")

    # ─── 一般個股掃描 ───
    st.info(f"🚀 正在掃描共 {len(all_tickers)} 檔個股標的...")
    progress_bar = st.progress(0)
    status_text = st.empty()

    chunk_size = 80
    triggered_results = []
    successful_tickers = set()
    start_time = time.time()
    
    use_fund = not scan_mode.startswith("1")

    for i in range(0, len(all_tickers), chunk_size):
        batch = all_tickers[i:i+chunk_size]
        status_text.text(f"⏳ 正在下載與分析 K 線: {i} / {len(all_tickers)} ...")

        try:
            data = yf.download(batch, period=f"{scan_days}d", interval=fetch_interval, group_by='ticker', progress=False, threads=True)
            for t in batch:
                try:
                    df_t = data[t] if len(batch) > 1 else data
                    df_t = df_t.dropna(subset=['Close'])
                    
                    if len(df_t) > 40:
                        successful_tickers.add(t)
                        df_t.name = t
                        
                        try:
                            avg_vol = df_t.groupby(df_t.index.date)['Volume'].sum().mean()
                        except:
                            avg_vol = 0
                        
                        if selected_tf == "4h":
                            df_proc = resample_to_tv_4h(df_t)
                        else:
                            df_proc = df_t.copy()
                            if df_proc.index.tz is None:
                                df_proc.index = pd.to_datetime(df_proc.index).tz_localize('UTC').tz_convert('America/New_York')
                            else:
                                df_proc.index = df_proc.index.tz_convert('America/New_York')
                                
                        res_tech = scan_signals(df_proc, recent_k)
                        pass_tech = res_tech is not None
                        
                        pass_fund = False
                        pe_val, peg_val, pb_val = 0, 0, 0
                        
                        if use_fund:
                            try:
                                info = yf.Ticker(t).info
                                pe_val = info.get('trailingPE') or 0
                                peg_val = info.get('pegRatio') or 0
                                pb_val = info.get('priceToBook') or 0
                                
                                cond_pe = (0 < pe_val <= max_pe) if max_pe > 0 else True
                                cond_peg = (0 < peg_val <= max_peg) if max_peg > 0 else True
                                cond_pb = (0 < pb_val <= max_pb) if max_pb > 0 else True
                                
                                if max_pe == 0 and max_peg == 0 and max_pb == 0:
                                    pass_fund = True 
                                else:
                                    pass_fund = cond_pe and cond_peg and cond_pb
                            except:
                                pass_fund = False 

                        should_add = False
                        if scan_mode.startswith("1"):
                            should_add = pass_tech
                        elif scan_mode.startswith("2"):
                            should_add = pass_tech or pass_fund
                        elif scan_mode.startswith("3"):
                            should_add = pass_tech and pass_fund
                        elif scan_mode.startswith("4"):
                            should_add = pass_fund
                            
                        if should_add:
                            final_res = res_tech if res_tech else {}
                            final_res["標的代號"] = t
                            final_res["Raw_Volume"] = avg_vol
                            final_res["觸發指標通知"] = res_tech["觸發指標通知"] if pass_tech else "無技術訊號"
                            
                            if use_fund:
                                final_res["PEG (市賺率)"] = f"{peg_val:.2f}" if peg_val > 0 else "N/A"
                                final_res["P/E"] = f"{pe_val:.2f}" if pe_val > 0 else "N/A"
                                final_res["P/B"] = f"{pb_val:.2f}" if pb_val > 0 else "N/A"
                                
                            triggered_results.append(final_res)
                except: continue
        except: continue

        progress_bar.progress(min((i + chunk_size) / len(all_tickers), 1.0))

    status_text.text("🔍 掃描完畢！正在過濾分析結果...")

    failed_tickers = [t for t in all_tickers if t not in successful_tickers]
    if failed_tickers:
        st.warning(f"⚠️ 以下標的無法取得足夠數據 (可能代號錯誤、近期無交易紀錄，或該時間框架無資料)：\n\n **{', '.join(failed_tickers)}**")

    if triggered_results:
        filtered_results = []
        for res in triggered_results:
            if not target_signals or res["觸發指標通知"] == "無技術訊號": 
                filtered_results.append(res) 
            else:
                sigs = res["觸發指標通知"].split(" ｜ ")
                match = False
                for s in sigs:
                    for target in target_signals:
                        if target in s:
                            match = True
                            break
                    if match: break
                
                if match:
                    filtered_results.append(res)

        if filtered_results:
            for res in filtered_results:
                ticker = res['標的代號']
                raw_vol = res.get('Raw_Volume', 0)
                res['日均交易量'] = format_vol(raw_vol)
                res['Priority'] = 1 if ticker in favorites else 0
                if ticker in favorites: res['標的代號'] = f"⭐ {ticker}"

            df_report = pd.DataFrame(filtered_results)
            df_report = df_report.sort_values(by=['Priority', 'Raw_Volume'], ascending=[False, False])
            
            cols_to_show = ["標的代號", "日均交易量"]
            if use_fund:
                cols_to_show.extend(["PEG (市賺率)", "P/E", "P/B"])
            cols_to_show.append("觸發指標通知")

            st.success(f"🎯 個股掃描完成！共發現 {len(df_report)} 檔符合條件的標的。(總耗時: {int(time.time() - start_time)} 秒)")
            st.dataframe(df_report[cols_to_show], use_container_width=True, height=600)
        else:
            st.warning(f"🎯 雖然有個股觸發訊號，但全都被「指標過濾器」濾掉了！可以試著把過濾條件放寬一點。")
    else:
        st.warning(f"🎯 目前掃描清單內，未發現任何符合條件的個股。(總耗時: {int(time.time() - start_time)} 秒)")
