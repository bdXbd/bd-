import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import time
import warnings
import os
import json
import urllib.request
import xml.etree.ElementTree as ET

warnings.filterwarnings("ignore")

# ════════════════════════════════════════════════════════════════════════════
# 網頁基本設定與自訂 CSS 美化
# ════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="bd の 超級指標(∠·ω< )⌒★ 股票篩選器 V7.5",
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
    ".macro-banner { background: linear-gradient(90deg, rgba(22,27,38,0.98), rgba(32,39,54,0.98)); border: 1px solid rgba(255,255,255,0.12); border-radius: 12px; padding: 14px 18px; margin-bottom: 12px; }"
    "</style>",
    unsafe_allow_html=True
)

st.title("🎯 bd の 超級指標(∠·ω< )⌒★ 股票篩選器 V7.5")
st.caption("全自動總經與技術戰情版：**自動抓取 CPI / PCE / 失業率 / 美債 / VIX / 美元與即時新聞多空判讀** ｜ **全共振區強制回踩確認** ｜ **0秒即時過濾**")

# ════════════════════════════════════════════════════════════════════════════
# 訊號清單與預設戰術組合定義 (已移除 CHOCH / BOS / 纏論123買賣點)
# ════════════════════════════════════════════════════════════════════════════
CONFIG_FILE = "scanner_config.json"
FAV_FILE = "favorites.txt"

ALL_SIG_TYPES = [
    "🌟【中樞共振 Buy】", "🌟【中樞共振 Sell】",
    "🟪【OB共振支撐】", "🟪【OB共振壓力】",
    "🟠【中樞 Buy】", "🟠【中樞 Sell】",
    "🟩【OB支撐確認】", "🟥【OB壓力確認】",
    "🟢【恐慌抄底】", "🟡【Market Bottom】", "🟣【極度超賣】", "🟪【超賣預警】",
    "⚠️【頂部預警】", "🟠【WT 死叉】", "🟡【超買預警】",
    "🛡️【空頭陷阱】", "⚠️【多頭陷阱】"
]

PRESET_FILTERS = {
    "🛠️ 自訂勾選訊號 (記憶模式)": None,
    "🔥 全部訊號 (全開)": ALL_SIG_TYPES,
    "💎 右側回踩做多 (中樞/共振/OB支撐 + Market Bottom)": [
        "🌟【中樞共振 Buy】", "🟪【OB共振支撐】", "🟠【中樞 Buy】", "🟩【OB支撐確認】", "🟡【Market Bottom】"
    ],
    "🌟 頂級共振狙擊 (僅看中樞共振 + OB共振回踩確認)": [
        "🌟【中樞共振 Buy】", "🌟【中樞共振 Sell】", "🟪【OB共振支撐】", "🟪【OB共振壓力】"
    ],
    "🟢 左側恐慌抄底 (恐慌抄底 + 極度超賣 + 空頭陷阱 + Market Bottom)": [
        "🟢【恐慌抄底】", "🟣【極度超賣】", "🛡️【空頭陷阱】", "🟡【Market Bottom】"
    ],
    "🔴 逃頂與做空警訊 (頂部預警 + WT死叉 + 壓力回踩受阻 + 多頭陷阱)": [
        "🌟【中樞共振 Sell】", "🟪【OB共振壓力】", "🟠【中樞 Sell】", "🟥【OB壓力確認】",
        "⚠️【頂部預警】", "🟠【WT 死叉】", "⚠️【多頭陷阱】"
    ]
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
        "vol_sort_by": "日均交易量 (推薦)",
        "fav_first": True,
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

    config["target_signals"] = [s for s in config.get("target_signals", ALL_SIG_TYPES) if s in ALL_SIG_TYPES]
    if not config["target_signals"]:
        config["target_signals"] = list(ALL_SIG_TYPES)

    return config

def save_config(config_dict):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config_dict, f, ensure_ascii=False, indent=4)

# ════════════════════════════════════════════════════════════════════════════
# 🌐 自動抓取總經數據 (FRED CPI/PCE/失業率/利差) + 跨市場資金 + 即時財經新聞引擎
# ════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=900)
def fetch_macro_intelligence():
    macro_cards = []
    market_cards = []
    news_items = []
    bull_score = 0
    bear_score = 0
    key_drivers = []

    # ── 1. 抓取聯準會 FRED 官方公開 CSV 數據 (免 API Key) ──
    def get_fred_series(series_id, tail_n=18):
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            df_f = pd.read_csv(resp)
        df_f.columns = ['DATE', 'VAL']
        df_f['VAL'] = pd.to_numeric(df_f['VAL'], errors='coerce')
        df_f = df_f.dropna().tail(tail_n).reset_index(drop=True)
        return df_f

    # (A) 美國 CPI 消費者物價指數 (CPIAUCSL)
    try:
        df_cpi = get_fred_series("CPIAUCSL", 16)
        if len(df_cpi) >= 14:
            yoy_now = (df_cpi['VAL'].iloc[-1] / df_cpi['VAL'].iloc[-13] - 1.0) * 100.0
            yoy_prev = (df_cpi['VAL'].iloc[-2] / df_cpi['VAL'].iloc[-14] - 1.0) * 100.0
            mom_now = (df_cpi['VAL'].iloc[-1] / df_cpi['VAL'].iloc[-2] - 1.0) * 100.0
            cpi_date = str(df_cpi['DATE'].iloc[-1])[:7]
            diff_yoy = yoy_now - yoy_prev

            if yoy_now > yoy_prev + 0.05 or mom_now >= 0.4:
                bias, cls = "🔴 通膨升溫 (鷹派壓抑估值)", "bear"
                bear_score += 2
                key_drivers.append(f"CPI 年增率升至 {yoy_now:.1f}% (月增 {mom_now:+.2f}%)，通膨反彈加深聯準會鷹派立場")
            elif yoy_now < yoy_prev - 0.05 and mom_now <= 0.25:
                bias, cls = "🟢 通膨降溫 (鴿派利多股市)", "bull"
                bull_score += 2
                key_drivers.append(f"CPI 年增率降至 {yoy_now:.1f}%，通膨趨緩有利科技股估值擴張")
            else:
                bias, cls = "🟡 通膨黏著 (符合預期震盪)", "warn"

            macro_cards.append({
                "title": f"🇺🇸 美國 CPI 通膨 ({cpi_date})",
                "main": f"{yoy_now:.2f}%",
                "sub": f"前值 {yoy_prev:.2f}% ({diff_yoy:+.2f}%) ｜ 月增 {mom_now:+.2f}%",
                "badge": bias,
                "cls": cls
            })
    except Exception:
        pass

    # (B) 美國核心 PCE 物價指數 (PCEPILFE - Fed 最重視指標)
    try:
        df_pce = get_fred_series("PCEPILFE", 16)
        if len(df_pce) >= 14:
            pce_yoy = (df_pce['VAL'].iloc[-1] / df_pce['VAL'].iloc[-13] - 1.0) * 100.0
            pce_prev = (df_pce['VAL'].iloc[-2] / df_pce['VAL'].iloc[-14] - 1.0) * 100.0
            pce_mom = (df_pce['VAL'].iloc[-1] / df_pce['VAL'].iloc[-2] - 1.0) * 100.0
            pce_date = str(df_pce['DATE'].iloc[-1])[:7]
            diff_pce = pce_yoy - pce_prev

            if pce_yoy > pce_prev + 0.05 or pce_yoy >= 2.8:
                bias, cls = "🔴 核心通膨偏高 (降息受阻)", "bear"
                bear_score += 1
            elif pce_yoy < pce_prev:
                bias, cls = "🟢 核心通膨受控 (軟著陸利多)", "bull"
                bull_score += 1
            else:
                bias, cls = "🟡 核心通膨持平", "warn"

            macro_cards.append({
                "title": f"🎯 核心 PCE 年增 ({pce_date})",
                "main": f"{pce_yoy:.2f}%",
                "sub": f"前值 {pce_prev:.2f}% ({diff_pce:+.2f}%) ｜ 月增 {pce_mom:+.2f}%",
                "badge": bias,
                "cls": cls
            })
    except Exception:
        pass

    # (C) 美國非農失業率 (UNRATE)
    try:
        df_un = get_fred_series("UNRATE", 6)
        if len(df_un) >= 3:
            un_now = float(df_un['VAL'].iloc[-1])
            un_prev = float(df_un['VAL'].iloc[-2])
            un_date = str(df_un['DATE'].iloc[-1])[:7]
            diff_un = un_now - un_prev

            if un_now >= 4.4 or diff_un >= 0.2:
                bias, cls = "🔴 失業率攀升 (留意衰退風險)", "bear"
                bear_score += 1
                key_drivers.append(f"失業率升至 {un_now:.1f}%，勞動市場降溫需提防經濟衰退")
            elif un_now <= 4.2 and diff_un <= 0.0:
                bias, cls = "🟢 就業穩健 (支撐消費基本面)", "bull"
                bull_score += 1
            else:
                bias, cls = "🟡 勞動市場溫和放緩", "warn"

            macro_cards.append({
                "title": f"👷 非農失業率 ({un_date})",
                "main": f"{un_now:.1f}%",
                "sub": f"前值 {un_prev:.1f}% (變動 {diff_un:+.1f}%)",
                "badge": bias,
                "cls": cls
            })
    except Exception:
        pass

    # (D) 10Y-2Y 美債殖利率利差 (T10Y2Y)
    try:
        df_sp = get_fred_series("T10Y2Y", 10)
        if len(df_sp) >= 2:
            sp_now = float(df_sp['VAL'].iloc[-1])
            sp_prev = float(df_sp['VAL'].iloc[-5]) if len(df_sp) >= 5 else float(df_sp['VAL'].iloc[-2])
            sp_date = str(df_sp['DATE'].iloc[-1])[:10]

            if sp_now < 0:
                bias, cls = "🔴 殖利率倒掛 (信貸緊縮警戒)", "bear"
                bear_score += 1
            elif sp_now > 0.5:
                bias, cls = "🟡 曲線陡峭化 (留意長債利率)", "warn"
            else:
                bias, cls = "🟢 殖利率曲線正常化", "bull"
                bull_score += 1

            macro_cards.append({
                "title": f"🏦 10Y-2Y 殖利率差 ({sp_date})",
                "main": f"{sp_now:+.2f}%",
                "sub": f"一週前 {sp_prev:+.2f}% ｜ >0 為正常正斜率",
                "badge": bias,
                "cls": cls
            })
    except Exception:
        pass

    # ── 2. 抓取跨市場即時資金指標 (VIX, 10Y美債, 美元指數, 原油, 黃金) ──
    cross_tickers = ["^VIX", "^TNX", "DX-Y.NYB", "CL=F", "GC=F"]
    try:
        m_data = yf.download(cross_tickers, period="10d", interval="1d", group_by='ticker', progress=False, threads=True)

        def parse_m_ticker(sym):
            df_m = m_data[sym].dropna(subset=['Close'])
            if len(df_m) >= 2:
                c_now = float(df_m['Close'].iloc[-1])
                c_prev = float(df_m['Close'].iloc[-2])
                c_5d = float(df_m['Close'].iloc[-5]) if len(df_m) >= 5 else c_prev
                chg_1d = ((c_now - c_prev) / c_prev) * 100.0
                chg_5d = ((c_now - c_5d) / c_5d) * 100.0
                return c_now, chg_1d, chg_5d
            return None

        # (1) VIX 恐慌指數
        vix_info = parse_m_ticker("^VIX")
        if vix_info:
            v_val, v_1d, v_5d = vix_info
            if v_val >= 22.0 or v_1d >= 7.0:
                v_badge, v_cls = "🔴 避險情緒升溫 (美股承壓)", "bear"
                bear_score += 2
                key_drivers.append(f"VIX 恐慌指數位於 {v_val:.2f} ({v_1d:+.1f}%)，機構避險買盤湧入")
            elif v_val < 16.5 and v_1d <= 0:
                v_badge, v_cls = "🟢 市場情緒穩定 (有利多頭)", "bull"
                bull_score += 2
            elif v_1d < -4.0:
                v_badge, v_cls = "🟢 恐慌快速降溫 (支撐反彈)", "bull"
                bull_score += 1
            else:
                v_badge, v_cls = "🟡 情緒中性震盪", "warn"
            market_cards.append({
                "title": "⚡ VIX 恐慌指數", "price": f"{v_val:.2f}", "chg": v_1d,
                "sub": f"5日變動 {v_5d:+.1f}% ｜ <18 安定 / >22 恐慌", "badge": v_badge, "cls": v_cls
            })

        # (2) 10年期美債殖利率 (^TNX)
        tnx_info = parse_m_ticker("^TNX")
        if tnx_info:
            t_val, t_1d, t_5d = tnx_info
            if t_val >= 4.35 or t_5d >= 2.5:
                t_badge, t_cls = "🔴 殖利率飆升 (壓抑科技股估值)", "bear"
                bear_score += 2
                key_drivers.append(f"10年期美債殖利率達 {t_val:.2f}%，無風險利率走高壓抑高估值科技股")
            elif t_1d < -1.2 or t_5d < -2.0:
                t_badge, t_cls = "🟢 殖利率回落 (資金回流成長股)", "bull"
                bull_score += 2
                key_drivers.append(f"10年期美債殖利率回落至 {t_val:.2f}%，緩解科技股估值壓力")
            else:
                t_badge, t_cls = "🟡 殖利率區間整理", "warn"
            market_cards.append({
                "title": "📈 10年期美債殖利率", "price": f"{t_val:.2f}%", "chg": t_1d,
                "sub": f"5日變動 {t_5d:+.1f}% ｜ 科技股折現率指標", "badge": t_badge, "cls": t_cls
            })

        # (3) 美元指數 (DX-Y.NYB)
        dxy_info = parse_m_ticker("DX-Y.NYB")
        if dxy_info:
            d_val, d_1d, d_5d = dxy_info
            if d_1d >= 0.35 or d_5d >= 1.0:
                d_badge, d_cls = "🔴 美元轉強 (外資易自台股流出)", "bear"
                bear_score += 1
                key_drivers.append(f"美元指數走強至 {d_val:.2f}，不利新興市場與台股外資資金面")
            elif d_1d <= -0.30 or d_5d <= -0.8:
                d_badge, d_cls = "🟢 美元走弱 (利好台股與風險資產)", "bull"
                bull_score += 1
            else:
                d_badge, d_cls = "🟡 美元匯率持穩", "warn"
            market_cards.append({
                "title": "💵 DXY 美元指數", "price": f"{d_val:.2f}", "chg": d_1d,
                "sub": f"5日變動 {d_5d:+.1f}% ｜ 全球跨國資金流向指標", "badge": d_badge, "cls": d_cls
            })

        # (4) WTI 原油期貨 (CL=F)
        oil_info = parse_m_ticker("CL=F")
        if oil_info:
            o_val, o_1d, o_5d = oil_info
            if o_val >= 82.0 or o_5d >= 5.0:
                o_badge, o_cls = "🔴 油價大漲 (推升二次通膨隱憂)", "bear"
                bear_score += 1
                key_drivers.append(f"WTI 原油升至 ${o_val:.2f} (5日 {o_5d:+.1f}%)，能源成本推升通膨預期")
            elif o_val <= 72.0 or o_5d <= -4.0:
                o_badge, o_cls = "🟢 油價回落 (緩解通膨與企業成本)", "bull"
                bull_score += 1
            else:
                o_badge, o_cls = "🟡 油價溫和整理", "warn"
            market_cards.append({
                "title": "🛢️ WTI 原油期貨", "price": f"${o_val:.2f}", "chg": o_1d,
                "sub": f"5日變動 {o_5d:+.1f}% ｜ 能源型通膨先行指標", "badge": o_badge, "cls": o_cls
            })

        # (5) 黃金期貨 (GC=F)
        gold_info = parse_m_ticker("GC=F")
        if gold_info:
            g_val, g_1d, g_5d = gold_info
            if g_1d >= 1.2:
                g_badge, g_cls = "🟡 避險/抗通膨資金湧入黃金", "warn"
            else:
                g_badge, g_cls = "⚪ 貴金屬走勢平穩", "warn"
            market_cards.append({
                "title": "🥇 黃金期貨", "price": f"${g_val:.1f}", "chg": g_1d,
                "sub": f"5日變動 {g_5d:+.1f}% ｜ 地緣避險與通膨預期", "badge": g_badge, "cls": g_cls
            })
    except Exception:
        pass

    # ── 3. 即時財經與總經焦點新聞抓取 + 關鍵字多空情緒分析 ──
    bull_words = [
        "beat", "surge", "rally", "cooling", "eases", "cut", "dovish", "optimism",
        "gain", "bull", "jump", "upgrade", "record high", "soar", "rebound", "growth",
        "降溫", "利多", "大漲", "降息", "優於預期", "創高"
    ]
    bear_words = [
        "hotter", "accelerates", "tops forecasts", "hike", "hawkish", "inflation rises",
        "tariff", "sanction", "drop", "fall", "plunge", "miss", "fear", "recession",
        "selloff", "slump", "deficit", "war", "升溫", "高於預期", "升息", "利空", "大跌", "恐慌"
    ]

    seen_titles = set()
    for sym in ["SPY", "QQQ", "^TWII"]:
        try:
            raw_news = yf.Ticker(sym).news
            if raw_news:
                for item in raw_news[:6]:
                    content = item.get('content', item) if isinstance(item, dict) else {}
                    title = content.get('title') or item.get('title', '')
                    link = ""
                    if isinstance(content.get('canonicalUrl'), dict):
                        link = content['canonicalUrl'].get('url', '')
                    elif isinstance(item.get('link'), str):
                        link = item['link']

                    if title and title not in seen_titles:
                        seen_titles.add(title)
                        t_low = title.lower()
                        b_hits = sum(1 for w in bull_words if w in t_low)
                        s_hits = sum(1 for w in bear_words if w in t_low)
                        if s_hits > b_hits:
                            sent_tag = "🔴 偏空解讀"
                            bear_score += 0.5
                        elif b_hits > s_hits:
                            sent_tag = "🟢 偏多解讀"
                            bull_score += 0.5
                        else:
                            sent_tag = "⚪ 中性消息"
                        news_items.append({"title": title, "link": link, "sentiment": sent_tag})
        except Exception:
            pass

    # 若 yfinance 新聞較少，自動補充 Google News 總經/CPI/Fed 即時 RSS
    if len(news_items) < 4:
        try:
            rss_url = "https://news.google.com/rss/search?q=US+CPI+OR+Fed+interest+rate+OR+stock+market+inflation&hl=en-US&gl=US&ceid=US:en"
            req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=6) as resp:
                root = ET.fromstring(resp.read())
            for item in root.findall('.//item')[:6]:
                title = item.find('title').text if item.find('title') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                if title and title not in seen_titles:
                    seen_titles.add(title)
                    t_low = title.lower()
                    b_hits = sum(1 for w in bull_words if w in t_low)
                    s_hits = sum(1 for w in bear_words if w in t_low)
                    sent_tag = "🔴 偏空解讀" if s_hits > b_hits else ("🟢 偏多解讀" if b_hits > s_hits else "⚪ 中性消息")
                    news_items.append({"title": title, "link": link, "sentiment": sent_tag})
        except Exception:
            pass

    net_score = bull_score - bear_score
    if net_score >= 2.0:
        verdict = "🟢 總經與資金環境偏多 (Risk-On)"
        verdict_cls = "bull"
        verdict_advice = "通膨可控且無風險利率/恐慌指標溫和，總經順風有利於「右側回踩支撐 (中樞共振/OB)」積極布局做多。"
    elif net_score <= -2.0:
        verdict = "🔴 總經與資金環境偏空 (Risk-Off 警戒)"
        verdict_cls = "bear"
        verdict_advice = "通膨數據反彈或殖利率/美元/VIX 走高壓抑股市估值，建議提高現金水位、嚴守停損，做多僅限極度超賣或頂級共振支撐分批低接。"
    else:
        verdict = "🟡 總經多空交戰 / 數據消化期 (震盪選股)"
        verdict_cls = "warn"
        verdict_advice = "總經數據與跨市場資金多空力道拉鋸，大盤易呈現區間洗盤，切忌追高殺低，建議嚴格等待回踩中樞/OB共振確認後再出手。"

    return {
        "macro_cards": macro_cards,
        "market_cards": market_cards,
        "news_items": news_items[:8],
        "bull_score": bull_score,
        "bear_score": bear_score,
        "verdict": verdict,
        "verdict_cls": verdict_cls,
        "verdict_advice": verdict_advice,
        "key_drivers": key_drivers
    }

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

def calc_robust_avg_vol(df_raw):
    """穩健計算日均成交量，避免時區或索引格式造成歸零"""
    if 'Volume' not in df_raw.columns or len(df_raw) == 0:
        return 0.0
    try:
        idx_dates = pd.to_datetime(df_raw.index).date
        daily_vols = df_raw['Volume'].groupby(idx_dates).sum()
        non_zero = daily_vols[daily_vols > 0]
        if len(non_zero) > 0:
            return float(non_zero.tail(20).mean())
        return float(df_raw['Volume'].tail(20).mean())
    except Exception:
        return float(df_raw['Volume'].tail(20).mean()) if len(df_raw) > 0 else 0.0

def resample_to_tv_4h(df_1h, ticker=""):
    df = df_1h.copy()
    t_up = str(ticker).upper()

    if "-USD" in t_up or "=F" in t_up:
        if df.index.tz is not None:
            df.index = df.index.tz_convert('UTC')
        else:
            df.index = pd.to_datetime(df.index).tz_localize('UTC')
        df_4h = df.resample('4h', closed='left', label='left').agg({
            'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last', 'Volume': 'sum'
        }).dropna(subset=['Close'])
        return df_4h.sort_index()

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
        return f"https://www.tradingview.com/chart/?symbol=TWSE%3A{t.replace('.TW', '')}"
    if t.endswith(".TWO"):
        return f"https://www.tradingview.com/chart/?symbol=TPEX%3A{t.replace('.TWO', '')}"
    if t == "BTC-USD":
        return "https://www.tradingview.com/chart/?symbol=BINANCE%3ABTCUSDT"
    if t.endswith("-USD"):
        return f"https://www.tradingview.com/chart/?symbol=BINANCE%3A{t.replace('-USD', '')}USDT"
    return f"https://www.tradingview.com/chart/?symbol={t}"

# ════════════════════════════════════════════════════════════════════════════
# 纏論核心引擎 (用於中樞延伸 OB 與大盤 24 態面板，不發送 123 買賣點訊號)
# ════════════════════════════════════════════════════════════════════════════
def run_chan_engine(high_v, low_v, open_v, close_v, hist_v, min_gap=4):
    n = len(close_v)
    if n < 8:
        return [], [], []

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
                        last['high'], last['hIdx'] = hi, i
                    if lo > last['low']:
                        last['low'], last['lIdx'] = lo, i
                else:
                    if hi < last['high']:
                        last['high'], last['hIdx'] = hi, i
                    if lo < last['low']:
                        last['low'], last['lIdx'] = lo, i
            else:
                direction = 1 if hi > last['high'] else -1
                mk_arr.append({'high': hi, 'low': lo, 'hIdx': i, 'lIdx': i})

    fr_arr = []
    if len(mk_arr) >= 3:
        for k in range(1, len(mk_arr) - 1):
            a, c, d = mk_arr[k - 1], mk_arr[k], mk_arr[k + 1]
            if c['high'] > a['high'] and c['high'] > d['high'] and c['low'] > a['low'] and c['low'] > d['low']:
                fr_arr.append({'typ': 1, 'mIdx': k, 'price': c['high'], 'pos': c['hIdx']})
            elif c['low'] < a['low'] and c['low'] < d['low'] and c['high'] < a['high'] and c['high'] < d['high']:
                fr_arr.append({'typ': -1, 'mIdx': k, 'price': c['low'], 'pos': c['lIdx']})

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

    def f_area(idx_a, idx_b):
        s_idx, e_idx = max(0, idx_a), min(n - 1, idx_b)
        return float(np.sum(np.abs(hist_v[s_idx : e_idx + 1]))) if e_idx >= s_idx else 0.0

    def f_leg(zs0, ze, up_dir):
        best_a, best_i = -1.0, -1
        for idx_bi in range(zs0, ze + 1):
            if 0 <= idx_bi < len(bi_arr):
                b = bi_arr[idx_bi]
                if b['up'] == up_dir:
                    area = f_area(b['b0'], b['b1'])
                    if area > best_a:
                        best_a, best_i = area, idx_bi
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
# 完整技術指標掃描引擎 (OB / OB共振 / 中樞 / 中樞共振 皆嚴格回踩確認)
# ════════════════════════════════════════════════════════════════════════════
def update_active_obs(src_obs, max_obs=5, show_overlap=True):
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


def scan_signals(df, recent_k=2, strict_confirm=False, show_swing_ob=False):
    if df is None or len(df) < 40:
        return None

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

    # 1. WVF (模擬 VIX)
    h_close_22 = close_s.rolling(window=22).max()
    wvf = ((h_close_22 - low_s) / h_close_22) * 100.0
    wvf_avg = wvf.rolling(20).mean()
    wvf_std = wvf.rolling(20).std(ddof=0)
    wvf_ext = (wvf >= wvf_avg + 2.0 * wvf_std) | (wvf >= wvf.rolling(50).max() * 0.85)

    # 2. RSI 雷達 (10 ~ 20 多週期面積引擎)
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

    # 3. WaveTrend (10, 21, 4)
    wt_ap = (high_s + low_s + close_s) / 3.0
    wt_esa = wt_ap.ewm(span=10, adjust=False).mean()
    wt_d = (wt_ap - wt_esa).abs().ewm(span=10, adjust=False).mean().replace(0, 0.0001)
    wt1 = ((wt_ap - wt_esa) / (0.015 * wt_d)).ewm(span=21, adjust=False).mean()
    wt2 = wt1.rolling(4).mean()

    # 4. 反轉陷阱通道 (EMA 55, ATR 55 * 4.0)
    rt_basis = close_s.ewm(span=55, adjust=False).mean()
    tr_s = pd.concat([
        high_s - low_s,
        (high_s - close_s.shift(1)).abs(),
        (low_s - close_s.shift(1)).abs()
    ], axis=1).max(axis=1)
    rt_vola = rma(tr_s, 55)
    rt_upper = rt_basis + 4.0 * rt_vola
    rt_lower = rt_basis - 4.0 * rt_vola

    # 5. ATR 與 parsedHighs/Lows
    wt_atr_v = rma(tr_s, 14).values
    atr200_v = rma(tr_s, 200).values

    high_vol = (high_v - low_v) >= (2.0 * atr200_v)
    parsed_high = np.where(high_vol, low_v, high_v)
    parsed_low = np.where(high_vol, high_v, low_v)

    # 6. MACD 與纏論中樞運算
    ema12 = close_s.ewm(span=12, adjust=False).mean()
    ema26 = close_s.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    sig_line = macd_line.ewm(span=9, adjust=False).mean()
    hist_v = (macd_line - sig_line).fillna(0.0).values

    bi_arr, zs_arr, sg_arr = run_chan_engine(high_v, low_v, open_v, close_v, hist_v, min_gap=4)
    last_z = zs_arr[-1] if len(zs_arr) > 0 else None
    zs_search_start = max(2, bi_arr[last_z['startBi']]['b0']) if (last_z is not None and len(bi_arr) > last_z['startBi']) else (n + 1)

    os_ext_trig, os_warn_trig, ob_warn_trig, wt_dead_trig = False, False, False, False
    last_ext_os_sl = np.nan
    mb_fired_in_cycle, vix_in_red_cycle = False, False
    rt_last_sig, rt_blw_cnt, rt_abv_cnt = -1000, 0, 0
    last_buy_state, last_sell_state = False, False

    int_leg = np.zeros(n, dtype=int)
    sw_leg = np.zeros(n, dtype=int)
    ih_val, ih_idx, ih_crossed = np.nan, 0, True
    il_val, il_idx, il_crossed = np.nan, 0, True
    sh_val, sh_idx, sh_crossed = np.nan, 0, True
    sl_val, sl_idx, sl_crossed = np.nan, 0, True

    internal_trend = 0
    last_smc_tag = "BOS"

    internal_obs, swing_obs = [], []
    active_int_obs, active_sw_obs = [], []
    ob_buy_events, ob_sell_events, other_events = [], [], []

    curr_zs_raw = None
    active_zs_zone = None
    last_zs_buy_state, last_zs_sell_state = False, False
    zs_events = []

    last_wt_ph_idx, last_wt_ph_val, last_wt_ph_price = -1, -float('inf'), -float('inf')

    for i in range(2, n):
        t_str = df.index[i].strftime('%m/%d %H:%M')
        c_val = close_v[i]
        c_p = f"{c_val:.2f}"
        cur_atr = wt_atr_v[i] if not np.isnan(wt_atr_v[i]) else (high_v[i] - low_v[i])

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

        # 內部結構突破
        if not np.isnan(ih_val) and close_v[i] > ih_val and close_v[i - 1] <= ih_val and not ih_crossed and ih_val != sh_val:
            ih_crossed = True
            is_choch = (internal_trend == -1)
            internal_trend = 1
            last_smc_tag = "CHOCH" if is_choch else "BOS"
            s_idx = max(0, ih_idx)
            s_slice = parsed_low[s_idx : i]
            if len(s_slice) > 0:
                p_idx = s_idx + int(np.argmin(s_slice))
                internal_obs.insert(0, {'top': float(parsed_high[p_idx]), 'bot': float(parsed_low[p_idx]), 'ob_idx': p_idx, 'gen_i': i, 'bias': 1})
                if len(internal_obs) > 100:
                    internal_obs.pop()

        if not np.isnan(il_val) and close_v[i] < il_val and close_v[i - 1] >= il_val and not il_crossed and il_val != sl_val:
            il_crossed = True
            is_choch = (internal_trend == 1)
            internal_trend = -1
            last_smc_tag = "CHOCH" if is_choch else "BOS"
            s_idx = max(0, il_idx)
            s_slice = parsed_high[s_idx : i]
            if len(s_slice) > 0:
                p_idx = s_idx + int(np.argmax(s_slice))
                internal_obs.insert(0, {'top': float(parsed_high[p_idx]), 'bot': float(parsed_low[p_idx]), 'ob_idx': p_idx, 'gen_i': i, 'bias': -1})
                if len(internal_obs) > 100:
                    internal_obs.pop()

        # 擺動結構突破
        if not np.isnan(sh_val) and close_v[i] > sh_val and close_v[i - 1] <= sh_val and not sh_crossed:
            sh_crossed = True
            if show_swing_ob:
                s_idx = max(0, sh_idx)
                s_slice = parsed_low[s_idx : i]
                if len(s_slice) > 0:
                    p_idx = s_idx + int(np.argmin(s_slice))
                    swing_obs.insert(0, {'top': float(parsed_high[p_idx]), 'bot': float(parsed_low[p_idx]), 'ob_idx': p_idx, 'gen_i': i, 'bias': 1})
                    if len(swing_obs) > 100:
                        swing_obs.pop()

        if not np.isnan(sl_val) and close_v[i] < sl_val and close_v[i - 1] >= sl_val and not sl_crossed:
            sl_crossed = True
            if show_swing_ob:
                s_idx = max(0, sl_idx)
                s_slice = parsed_high[s_idx : i]
                if len(s_slice) > 0:
                    p_idx = s_idx + int(np.argmax(s_slice))
                    swing_obs.insert(0, {'top': float(parsed_high[p_idx]), 'bot': float(parsed_low[p_idx]), 'ob_idx': p_idx, 'gen_i': i, 'bias': -1})
                    if len(swing_obs) > 100:
                        swing_obs.pop()

        # 剃除失效 SMC OB 與更新共振區
        internal_obs = [ob for ob in internal_obs if not ((ob['bias'] == -1 and high_v[i] > ob['top']) or (ob['bias'] == 1 and low_v[i] < ob['bot']))]
        if show_swing_ob:
            swing_obs = [ob for ob in swing_obs if not ((ob['bias'] == -1 and high_v[i] > ob['top']) or (ob['bias'] == 1 and low_v[i] < ob['bot']))]

        active_int_obs, _ = update_active_obs(internal_obs, max_obs=5, show_overlap=True)
        if show_swing_ob:
            active_sw_obs, _ = update_active_obs(swing_obs, max_obs=5, show_overlap=True)

        # ── 中樞延伸 OB 與 中樞×SMC 共振更新 & 嚴格回踩確認 ──
        if last_z is not None and i >= zs_search_start:
            if curr_zs_raw is not None and i > curr_zs_raw['break_idx']:
                if (curr_zs_raw['bias'] == 1 and low_v[i] < curr_zs_raw['ob_lo']) or (curr_zs_raw['bias'] == -1 and high_v[i] > curr_zs_raw['ob_hi']):
                    curr_zs_raw = None
                    active_zs_zone = None
                    last_zs_buy_state, last_zs_sell_state = False, False
                    zs_events = []

            if close_v[i] > last_z['ZG'] and close_v[i - 1] <= last_z['ZG']:
                ob_idx = i - 1
                curr_zs_raw = {
                    'ob_hi': float(parsed_high[ob_idx]),
                    'ob_lo': float(parsed_low[ob_idx]),
                    'ob_idx': ob_idx,
                    'break_idx': i,
                    'bias': 1
                }
                last_zs_buy_state, last_zs_sell_state = False, False
                zs_events = []
            elif close_v[i] < last_z['ZD'] and close_v[i - 1] >= last_z['ZD']:
                ob_idx = i - 1
                curr_zs_raw = {
                    'ob_hi': float(parsed_high[ob_idx]),
                    'ob_lo': float(parsed_low[ob_idx]),
                    'ob_idx': ob_idx,
                    'break_idx': i,
                    'bias': -1
                }
                last_zs_buy_state, last_zs_sell_state = False, False
                zs_events = []

            if curr_zs_raw is not None:
                ob_hi, ob_lo, ob_idx = curr_zs_raw['ob_hi'], curr_zs_raw['ob_lo'], curr_zs_raw['ob_idx']
                break_bias = curr_zs_raw['bias']
                has_zs_reso = False
                final_zs_hi, final_zs_lo = ob_hi, ob_lo
                final_zs_bix = ob_idx
                final_zs_gen = curr_zs_raw['break_idx']

                for idx_o in range(min(5, len(internal_obs))):
                    s_ob = internal_obs[idx_o]
                    if s_ob['bias'] == break_bias:
                        i_top, i_bot = min(ob_hi, s_ob['top']), max(ob_lo, s_ob['bot'])
                        if i_top > i_bot:
                            has_zs_reso = True
                            final_zs_hi, final_zs_lo = min(final_zs_hi, i_top), max(final_zs_lo, i_bot)
                            final_zs_bix = max(final_zs_bix, s_ob['ob_idx'])
                            final_zs_gen = max(final_zs_gen, s_ob['gen_i'])
                            active_int_obs = [x for x in active_int_obs if x['ob_idx'] != s_ob['ob_idx']]

                for x in list(active_int_obs):
                    if x.get('is_reso', False) and x['bias'] == break_bias:
                        if min(ob_hi, x['top']) > max(ob_lo, x['bot']):
                            has_zs_reso = True
                            final_zs_gen = max(final_zs_gen, x['gen_i'])
                            active_int_obs.remove(x)

                if show_swing_ob:
                    for idx_o in range(min(5, len(swing_obs))):
                        s_ob = swing_obs[idx_o]
                        if s_ob['bias'] == break_bias:
                            i_top, i_bot = min(ob_hi, s_ob['top']), max(ob_lo, s_ob['bot'])
                            if i_top > i_bot:
                                has_zs_reso = True
                                final_zs_hi, final_zs_lo = min(final_zs_hi, i_top), max(final_zs_lo, i_bot)
                                final_zs_bix = max(final_zs_bix, s_ob['ob_idx'])
                                final_zs_gen = max(final_zs_gen, s_ob['gen_i'])
                                active_sw_obs = [x for x in active_sw_obs if x['ob_idx'] != s_ob['ob_idx']]

                if final_zs_hi <= final_zs_lo:
                    final_zs_hi, final_zs_lo = ob_hi, ob_lo

                active_zs_zone = {
                    'top': final_zs_hi, 'bot': final_zs_lo, 'ob_idx': final_zs_bix, 'gen_i': final_zs_gen,
                    'bias': break_bias, 'is_reso': has_zs_reso,
                    'type_name': ("🌟 中樞共振支撐" if break_bias == 1 else "🌟 中樞共振壓力") if has_zs_reso else ("🟠 中樞支撐" if break_bias == 1 else "🟠 中樞壓力")
                }

                if i > active_zs_zone['gen_i']:
                    if break_bias == 1:
                        is_touch = (low_v[i] <= final_zs_hi) or (close_v[i - 1] <= final_zs_hi and close_v[i - 1] >= final_zs_lo)
                        is_conf = (close_v[i] > final_zs_hi)
                        is_trend = (close_v[i] > open_v[i]) if strict_confirm else True
                        cur_zs_b = is_touch and is_conf and is_trend
                        if cur_zs_b and not last_zs_buy_state:
                            tag_name = "🌟【中樞共振 Buy】" if has_zs_reso else "🟠【中樞 Buy】"
                            zs_events.append({'bar_i': i, 'sig_str': f"{tag_name}({t_str} 守穩 {final_zs_hi:.2f})"})
                        last_zs_buy_state = cur_zs_b
                    else:
                        is_touch = (high_v[i] >= final_zs_lo) or (close_v[i - 1] >= final_zs_lo and close_v[i - 1] <= final_zs_hi)
                        is_conf = (close_v[i] < final_zs_lo)
                        is_trend = (close_v[i] < open_v[i]) if strict_confirm else True
                        cur_zs_s = is_touch and is_conf and is_trend
                        if cur_zs_s and not last_zs_sell_state:
                            tag_name = "🌟【中樞共振 Sell】" if has_zs_reso else "🟠【中樞 Sell】"
                            zs_events.append({'bar_i': i, 'sig_str': f"{tag_name}({t_str} 受阻 {final_zs_lo:.2f})"})
                        last_zs_sell_state = cur_zs_s

        # WaveTrend 與 RSI 雷達動能訊號
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
                    if 5 <= bars_since <= 60 and curr_wt_ph_price > last_wt_ph_price and curr_wt_ph_val < last_wt_ph_val:
                        other_events.append({'bar_i': i, 'sig_str': f"⚠️【頂部預警】({t_str} @ {c_p})"})
                last_wt_ph_idx = i - size_piv
                last_wt_ph_val = curr_wt_ph_val
                last_wt_ph_price = curr_wt_ph_price

        if (wt1.iloc[i] > wt2.iloc[i]) and (wt1.iloc[i - 1] <= wt2.iloc[i - 1]) and (wt1.iloc[i - 1] <= -60.0) and wvf_ext.iloc[i - 1] and rsi_red_below.iloc[i - 1]:
            other_events.append({'bar_i': i, 'sig_str': f"🟢【恐慌抄底】({t_str} @ {c_p})"})

        if (wt1.iloc[i] <= -60.0) and wvf_ext.iloc[i] and rsi_red_below.iloc[i]:
            if (not os_ext_trig) or (not np.isnan(last_ext_os_sl) and low_v[i] < last_ext_os_sl):
                os_ext_trig = True
                last_ext_os_sl = c_val - (cur_atr * 1.5)
                other_events.append({'bar_i': i, 'sig_str': f"🟣【極度超賣】({t_str} @ {c_p})"})

        wt_golden_cross_mb = (wt1.iloc[i] > wt2.iloc[i]) and (wt1.iloc[i - 1] <= wt2.iloc[i - 1])
        red_is_zero_now = (per_under.iloc[i] == 100.0)
        red_was_present = per_under.iloc[max(0, i - 3) : i].min() < 100.0
        if wt_golden_cross_mb and red_is_zero_now and red_was_present and vix_in_red_cycle and not mb_fired_in_cycle:
            mb_fired_in_cycle = True
            other_events.append({'bar_i': i, 'sig_str': f"🟡【Market Bottom】({t_str} @ {c_p})"})

        if (wt1.iloc[i] <= -53.0) and wvf_ext.iloc[i] and not os_warn_trig:
            os_warn_trig = True
            other_events.append({'bar_i': i, 'sig_str': f"🟪【超賣預警】({t_str} @ {c_p})"})

        wt_dead_cross = (wt1.iloc[i] < wt2.iloc[i]) and (wt1.iloc[i - 1] >= wt2.iloc[i - 1])
        green_area_was_0 = (per_over.iloc[i] == 0.0) or (per_over.iloc[i - 1] == 0.0) or (per_over.iloc[i - 2] == 0.0)
        if wt_dead_cross and green_area_was_0 and (wt1.iloc[i - 1] > 60.0) and not wt_dead_trig:
            wt_dead_trig = True
            other_events.append({'bar_i': i, 'sig_str': f"🟠【WT 死叉】({t_str} @ {c_p})"})

        if (wt1.iloc[i] > 53.0) and not ob_warn_trig:
            ob_warn_trig = True
            other_events.append({'bar_i': i, 'sig_str': f"🟡【超買預警】({t_str} @ {c_p})"})

        # 反轉陷阱通道
        raw_bull_trap = False
        if close_v[i] > rt_lower.iloc[i]:
            if low_v[i] < rt_lower.iloc[i] and close_v[i - 1] > rt_lower.iloc[i - 1] and rt_blw_cnt <= 10:
                raw_bull_trap = True
            elif close_v[i - 1] < rt_lower.iloc[i - 1] and rt_blw_cnt <= 10:
                raw_bull_trap = True
        rt_blw_cnt = (rt_blw_cnt + 1) if (low_v[i] < rt_lower.iloc[i]) else 0

        raw_bear_trap = False
        if close_v[i] < rt_upper.iloc[i]:
            if high_v[i] > rt_upper.iloc[i] and close_v[i - 1] < rt_upper.iloc[i - 1] and rt_abv_cnt <= 10:
                raw_bear_trap = True
            elif close_v[i - 1] > rt_upper.iloc[i - 1] and rt_abv_cnt <= 10:
                raw_bear_trap = True
        rt_abv_cnt = (rt_abv_cnt + 1) if (high_v[i] > rt_upper.iloc[i]) else 0

        can_fire_rt = (i - rt_last_sig) >= 10
        if raw_bull_trap and can_fire_rt and (oversell_count.iloc[i] > 0):
            rt_last_sig = i
            other_events.append({'bar_i': i, 'sig_str': f"🛡️【空頭陷阱】({t_str} @ {c_p})"})
        if raw_bear_trap and can_fire_rt and (overbuy_count.iloc[i] > 0):
            rt_last_sig = i
            other_events.append({'bar_i': i, 'sig_str': f"⚠️【多頭陷阱】({t_str} @ {c_p})"})

        # SMC OB 與 OB 共振回踩確認
        def check_retest_list(ob_list):
            b_trig, s_trig = False, False
            m_b_ob, m_s_ob = None, None
            for ob in ob_list:
                if i > ob.get('gen_i', ob['ob_idx']):
                    top, bot = ob['top'], ob['bot']
                    if ob['bias'] == 1:
                        is_touch = (low_v[i] <= top) or (close_v[i - 1] <= top and close_v[i - 1] >= bot)
                        is_conf = (close_v[i] > top)
                        is_trend = (close_v[i] > open_v[i]) if strict_confirm else True
                        if is_touch and is_conf and is_trend:
                            b_trig, m_b_ob = True, ob
                    elif ob['bias'] == -1:
                        is_touch = (high_v[i] >= bot) or (close_v[i - 1] >= bot and close_v[i - 1] <= top)
                        is_conf = (close_v[i] < bot)
                        is_trend = (close_v[i] < open_v[i]) if strict_confirm else True
                        if is_touch and is_conf and is_trend:
                            s_trig, m_s_ob = True, ob
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

        if fire_buy and match_b_ob is not None:
            sig_txt = f"🟪【OB共振支撐】({t_str} 守穩 {match_b_ob['top']:.2f})" if match_b_ob.get('is_reso') else f"🟩【OB支撐確認】({t_str} 守穩 {match_b_ob['top']:.2f})"
            ob_buy_events.append({'bar_i': i, 'sig_str': sig_txt, 'parent_ob_idx': match_b_ob['ob_idx']})

        if fire_sell and match_s_ob is not None:
            sig_txt = f"🟪【OB共振壓力】({t_str} 受阻 {match_s_ob['bot']:.2f})" if match_s_ob.get('is_reso') else f"🟥【OB壓力確認】({t_str} 受阻 {match_s_ob['bot']:.2f})"
            ob_sell_events.append({'bar_i': i, 'sig_str': sig_txt, 'parent_ob_idx': match_s_ob['ob_idx']})

    # 8. 垃圾回收：僅保留當前仍存活的有效 SMC OB / 共振回踩標籤
    valid_ob_indices = {ob['ob_idx'] for ob in active_int_obs} | {ob['ob_idx'] for ob in active_sw_obs}
    valid_buy_events = [ev for ev in ob_buy_events if ev['parent_ob_idx'] in valid_ob_indices]
    valid_sell_events = [ev for ev in ob_sell_events if ev['parent_ob_idx'] in valid_ob_indices]

    all_valid_events = other_events + valid_buy_events + valid_sell_events + zs_events
    recent_events = [ev for ev in all_valid_events if ev['bar_i'] >= n - recent_k]
    recent_events.sort(key=lambda x: x['bar_i'])

    latest_signals = []
    for ev in recent_events:
        if ev['sig_str'] not in latest_signals:
            latest_signals.append(ev['sig_str'])

    last_close = float(close_v[-1])
    prev_close = float(close_v[-2]) if n >= 2 else last_close
    chg_pct = ((last_close - prev_close) / prev_close) * 100.0 if prev_close != 0 else 0.0

    # 9. 市場狀態面板 (24態) 數值解讀
    vol_avg20 = pd.Series(vol_v).rolling(20).mean().iloc[-1]
    use_prev_bar = (high_v[-1] == low_v[-1]) or (not pd.isna(vol_avg20) and vol_avg20 > 0 and vol_v[-1] < vol_avg20 * 0.15)
    p_idx = -2 if (use_prev_bar and n >= 2) else -1

    p_wt1 = float(wt1.iloc[p_idx])
    p_rsi = float(avg_rsi.iloc[p_idx])

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

    # 10. 最近支撐與壓力區間
    all_zones = []
    if active_zs_zone is not None:
        all_zones.append(active_zs_zone)
    for ob in active_int_obs:
        z_name = ("🟪 OB共振支撐" if ob['bias'] == 1 else "🟪 OB共振壓力") if ob.get('is_reso') else ("🟩 內部OB支撐" if ob['bias'] == 1 else "🟥 內部OB壓力")
        all_zones.append({'top': ob['top'], 'bot': ob['bot'], 'bias': ob['bias'], 'type_name': z_name})

    nearest_sup_str, nearest_res_str = "無", "無"
    bull_zones = [z for z in all_zones if z['bias'] == 1]
    bear_zones = [z for z in all_zones if z['bias'] == -1]

    if bull_zones:
        bull_zones.sort(key=lambda z: abs(last_close - z['top']))
        bz = bull_zones[0]
        dist = ((last_close - bz['top']) / last_close) * 100.0
        in_z = " (⚡踩入!)" if (bz['bot'] <= last_close <= bz['top']) else f" ({dist:+.1f}%)"
        nearest_sup_str = f"{bz['type_name']} [{bz['bot']:.2f}~{bz['top']:.2f}]{in_z}"

    if bear_zones:
        bear_zones.sort(key=lambda z: abs(z['bot'] - last_close))
        rz = bear_zones[0]
        dist = ((rz['bot'] - last_close) / last_close) * 100.0
        in_z = " (⚡進入!)" if (rz['bot'] <= last_close <= rz['top']) else f" ({dist:+.1f}%)"
        nearest_res_str = f"{rz['type_name']} [{rz['bot']:.2f}~{rz['top']:.2f}]{in_z}"

    k2_events = list(dict.fromkeys([ev['sig_str'] for ev in all_valid_events if ev['bar_i'] >= n - 2]))

    return {
        "最新收盤價": last_close,
        "漲跌幅": chg_pct,
        "當前成交量": float(vol_v[-1]),
        "WT快線": p_wt1,
        "平均RSI": p_rsi,
        "RSI狀態": rsi_status,
        "SMC_State_ID": smc_state_id,
        "SMC_Tag_UI": smc_tag_ui,
        "Chan_Tag": chan_tag,
        "Chan_Action_Base": action_txt,
        "Chan_Is_Long": last_bs_is_long,
        "Chan_Cls": last_bs_cls,
        "K2_Signals": k2_events,
        "觸發指標通知": " ｜ ".join(latest_signals) if latest_signals else "",
        "最近支撐區": nearest_sup_str,
        "最近壓力區": nearest_res_str,
        "SMC_Trend": internal_trend,
        "SMC_Tag": last_smc_tag
    }

# ════════════════════════════════════════════════════════════════════════════
# 網頁側邊欄設定
# ════════════════════════════════════════════════════════════════════════════
user_config = load_config()

st.sidebar.header("⚙️ 雷達掃描設定")

st.sidebar.subheader("📌 收藏標的清單")
fav_input = st.sidebar.text_area(
    "請輸入股票代號 (用半形逗號分隔)：",
    value=user_config["favorites"],
    height=120,
    help="台股請加 .TW (如 2330.TW)。大盤 ^TWII，美股期貨 NQ=F，加密貨幣 BTC-USD。"
)

st.sidebar.subheader("🎯 訊號與排序參數")
tf_options = {"15分K": "15m", "1小時K": "1h", "4小時K (TV標準)": "4h", "日K": "1d"}
tf_opts_keys = list(tf_options.keys())
tf_idx = tf_opts_keys.index(user_config["selected_tf_label"]) if user_config["selected_tf_label"] in tf_opts_keys else 2
selected_tf_label = st.sidebar.selectbox("⏳ 選擇時間框架", tf_opts_keys, index=tf_idx)
selected_tf = tf_options[selected_tf_label]

col_s1, col_s2 = st.sidebar.columns(2)
with col_s1:
    recent_k = st.number_input("掃描近 N 根K線", min_value=1, max_value=15, value=int(user_config.get("recent_k", 2)))
with col_s2:
    max_days = 60 if selected_tf in ["15m"] else (730 if selected_tf in ["1h", "4h"] else 1000)
    default_days = max(20, min(int(user_config.get("scan_days", 90)), max_days))
    scan_days = st.number_input("歷史天數", min_value=20, max_value=max_days, value=default_days)

sort_opts = ["日均交易量 (推薦)", "當前K棒成交量"]
sort_idx = 0 if user_config.get("vol_sort_by", "日均交易量 (推薦)") == "日均交易量 (推薦)" else 1
vol_sort_by = st.sidebar.radio("📊 表格成交量排序依據 (由大到小)：", sort_opts, index=sort_idx, horizontal=True)
fav_first = st.sidebar.checkbox("⭐ 收藏清單標的優先置頂 (再依成交量排)", value=bool(user_config.get("fav_first", True)))

with st.sidebar.expander("🛠️ 進階與全市場擴充設定", expanded=False):
    scan_us_indices = st.checkbox("🌍 同步掃描美股三大指數 (SPY, QQQ, SOXX)", value=bool(user_config.get("scan_us_indices", False)))
    strict_confirm = st.checkbox("嚴格收線確認 (Buy需收紅/Sell需收綠)", value=bool(user_config.get("strict_confirm", False)))
    show_swing_ob = st.checkbox("回踩包含擺動 OB (Swing OB)", value=bool(user_config.get("show_swing_ob", False)))

    st.markdown("---")
    scan_options = [
        "1. 僅看技術指標 (預設)",
        "2. 聯集 (技術觸發 OR 基本面達標)",
        "3. 交集 (技術觸發 AND 基本面達標)",
        "4. 僅看基本面 (無視技術指標)"
    ]
    s_idx = scan_options.index(user_config["scan_mode"]) if user_config["scan_mode"] in scan_options else 0
    scan_mode = st.radio("掃描模式：", scan_options, index=s_idx)
    max_peg = st.number_input("市賺率 (PEG) 低於", min_value=0.0, value=float(user_config["max_peg"]), step=0.1)
    max_pe = st.number_input("本益比 (P/E) 低於", min_value=0.0, value=float(user_config["max_pe"]), step=1.0)
    max_pb = st.number_input("股價淨值比 (P/B) 低於", min_value=0.0, value=float(user_config["max_pb"]), step=0.1)

st.sidebar.subheader("🔍 指標過濾器 (即時生效)")

if "ms_target_signals" not in st.session_state:
    saved_sigs = [s for s in user_config.get("target_signals", ALL_SIG_TYPES) if s in ALL_SIG_TYPES]
    st.session_state.ms_target_signals = saved_sigs

def on_preset_change():
    choice = st.session_state.preset_selector
    if PRESET_FILTERS.get(choice) is not None:
        st.session_state.ms_target_signals = list(PRESET_FILTERS[choice])

st.sidebar.selectbox(
    "快速套用戰術濾網：",
    list(PRESET_FILTERS.keys()),
    index=0,
    key="preset_selector",
    on_change=on_preset_change
)

c_sel1, c_sel2 = st.sidebar.columns(2)
with c_sel1:
    if st.button("✅ 全選訊號", use_container_width=True):
        st.session_state.ms_target_signals = list(ALL_SIG_TYPES)
        st.rerun()
with c_sel2:
    if st.button("🗑️ 清空訊號", use_container_width=True):
        st.session_state.ms_target_signals = []
        st.rerun()

target_signals = st.sidebar.multiselect(
    "保留含有以下訊號的標的 (打叉 × 即時隱藏)：",
    options=ALL_SIG_TYPES,
    key="ms_target_signals"
)

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
            "vol_sort_by": vol_sort_by,
            "fav_first": fav_first,
            "target_signals": list(st.session_state.ms_target_signals)
        }
        save_config(new_cfg)
        st.sidebar.success("✅ 設定已記憶！")
        time.sleep(0.4)
        st.rerun()

with col_b2:
    scan_btn = st.button("🚀 立即啟動掃描", type="primary", use_container_width=True)

# ════════════════════════════════════════════════════════════════════════════
# 執行掃描並寫入快取 (讓後續打叉過濾與排序切換 0 秒即時完成)
# ════════════════════════════════════════════════════════════════════════════
if scan_btn:
    favorites = [t.strip().upper() for t in fav_input.split(",") if t.strip()]
    all_tickers = favorites.copy()

    if scan_us_indices:
        with st.spinner("🔄 正在取得美股三大指數成分股清單..."):
            us_stocks, _, _, success = get_us_indices()
            if not success:
                st.warning("⚠️ 維基百科連線受限，已切換至核心權值股備用清單。")
            all_tickers.extend(us_stocks)

    all_tickers = list(dict.fromkeys(all_tickers))
    if not all_tickers:
        st.error("❌ 收藏清單是空的！")
        st.stop()

    fetch_interval = "1h" if selected_tf == "4h" else selected_tf

    # 0. 自動抓取最新總經數據 (FRED CPI/PCE/失業率) 與跨市場資金 + 新聞情緒
    with st.spinner("🌐 正在自動抓取最新 CPI / 核心PCE / 失業率 / 美債殖利率 / VIX 與即時財經新聞..."):
        macro_intel = fetch_macro_intelligence()

    # 1. 掃描大盤 24 態風向標
    barometer_tickers = ["QQQ", "SOXX", "SPY", "^TWII", "BTC-USD"]
    baro_results = {}
    with st.spinner("🔄 正在運算大盤 24 態纏論×SMC 矩陣與近 2K 閃電抄底訊號..."):
        b_data = yf.download(barometer_tickers, period=f"{scan_days}d", interval=fetch_interval, group_by='ticker', progress=False, threads=True)
        for b_tick in barometer_tickers:
            try:
                df_b = b_data[b_tick] if len(barometer_tickers) > 1 else b_data
                df_b = df_b.dropna(subset=['Close'])
                if len(df_b) > 40:
                    df_proc_b = resample_to_tv_4h(df_b, b_tick) if selected_tf == "4h" else df_b.copy()
                    baro_results[b_tick] = scan_signals(df_proc_b, recent_k=14, strict_confirm=strict_confirm, show_swing_ob=show_swing_ob)
            except Exception:
                baro_results[b_tick] = None

    # 2. 批量掃描個股
    progress_bar = st.progress(0)
    status_text = st.empty()
    chunk_size = 80
    all_scanned_rows = []
    successful_tickers = set()
    start_time = time.time()
    use_fund = not scan_mode.startswith("1")

    for i in range(0, len(all_tickers), chunk_size):
        batch = all_tickers[i : i + chunk_size]
        status_text.text(f"⏳ 正在下載與分析 K 線: {i} / {len(all_tickers)} ...")
        try:
            data = yf.download(batch, period=f"{scan_days}d", interval=fetch_interval, group_by='ticker', progress=False, threads=True)
            for t in batch:
                try:
                    df_t = data[t] if len(batch) > 1 else data
                    df_t = df_t.dropna(subset=['Close'])
                    if len(df_t) > 40:
                        successful_tickers.add(t)
                        avg_vol = calc_robust_avg_vol(df_t)

                        df_proc = resample_to_tv_4h(df_t, t) if selected_tf == "4h" else df_t.copy()
                        res_tech = scan_signals(df_proc, recent_k=recent_k, strict_confirm=strict_confirm, show_swing_ob=show_swing_ob)
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

                        smc_str = f"🟢 多頭 {res_tech['SMC_Tag']}" if res_tech["SMC_Trend"] == 1 else (
                            f"🔴 空頭 {res_tech['SMC_Tag']}" if res_tech["SMC_Trend"] == -1 else "⚪ 震盪整理"
                        )

                        cur_vol = float(res_tech["當前成交量"])
                        all_scanned_rows.append({
                            "Raw_Ticker": t,
                            "Is_Fav": t in favorites,
                            "標的代號": f"⭐ {t}" if (t in favorites) else t,
                            "TV圖表": get_tv_link(t),
                            "SMC 結構": smc_str,
                            "最新收盤價": f"{res_tech['最新收盤價']:.2f} ({res_tech['漲跌幅']:+.2f}%)",
                            "當前成交量": cur_vol,
                            "日均交易量": avg_vol,
                            "All_Signals": res_tech["觸發指標通知"],
                            "最近支撐區": res_tech["最近支撐區"],
                            "最近壓力區": res_tech["最近壓力區"],
                            "PEG (市賺率)": f"{peg_val:.2f}" if peg_val > 0 else "N/A",
                            "P/E": f"{pe_val:.2f}" if pe_val > 0 else "N/A",
                            "P/B": f"{pb_val:.2f}" if pb_val > 0 else "N/A",
                            "Pass_Tech": pass_tech,
                            "Pass_Fund": pass_fund
                        })
                except Exception:
                    continue
        except Exception:
            continue
        progress_bar.progress(min((i + chunk_size) / len(all_tickers), 1.0))

    progress_bar.empty()
    status_text.empty()

    st.session_state.scan_cache = {
        "macro_intel": macro_intel,
        "baro_results": baro_results,
        "all_scanned_rows": all_scanned_rows,
        "failed_tickers": [t for t in all_tickers if t not in successful_tickers],
        "elapsed": int(time.time() - start_time),
        "tf_label": selected_tf_label,
        "tf_code": selected_tf
    }

# ════════════════════════════════════════════════════════════════════════════
# 畫面渲染區 (只要有掃描快取，修改左側任何過濾器/排序皆可 0 秒即時更新！)
# ════════════════════════════════════════════════════════════════════════════
if "scan_cache" in st.session_state:
    cache = st.session_state.scan_cache
    macro_intel = cache.get("macro_intel")
    baro_results = cache["baro_results"]
    all_scanned_rows = cache["all_scanned_rows"]

    # ── 第零區：全球總經數據 (CPI / PCE / 失業率) × 跨市場資金多空指揮中心 ──
    if macro_intel:
        st.subheader("🌐 全球總經數據 (CPI / PCE / 非農) × 跨市場資金多空指揮中心")

        v_cls = macro_intel["verdict_cls"]
        b_sc = macro_intel["bull_score"]
        s_sc = macro_intel["bear_score"]
        drivers_html = ""
        if macro_intel["key_drivers"]:
            drivers_html = "<div style='margin-top:6px;font-size:0.82rem;color:#ffd600;'>📌 <b>近期關鍵驅動因子：</b>" + " ｜ ".join(macro_intel["key_drivers"]) + "</div>"

        banner_html = (
            f'<div class="macro-banner baro-{v_cls}">'
            f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;">'
            f'<span style="font-size:1.12rem;font-weight:800;color:#ffffff;">{macro_intel["verdict"]}</span>'
            f'<span class="baro-badge badge-{v_cls}">總經與資金計分：多方 {b_sc:.1f} vs 空方 {s_sc:.1f}</span>'
            f'</div>'
            f'<div style="font-size:0.86rem;color:#d0d5e0;margin-top:4px;">💡 <b>操作策略建議：</b>{macro_intel["verdict_advice"]}</div>'
            f'{drivers_html}'
            f'</div>'
        )
        st.markdown(banner_html, unsafe_allow_html=True)

        # 顯示 FRED 總經數據卡片 (CPI, Core PCE, 失業率, 美債利差)
        if macro_intel["macro_cards"]:
            m_cols = st.columns(len(macro_intel["macro_cards"]))
            for idx, mc in enumerate(macro_intel["macro_cards"]):
                with m_cols[idx]:
                    c_html = (
                        f'<div class="baro-card baro-{mc["cls"]}">'
                        f'<div class="baro-title"><span>{mc["title"]}</span>'
                        f'<span class="baro-price">{mc["main"]}</span></div>'
                        f'<span class="baro-badge badge-{mc["cls"]}">{mc["badge"]}</span>'
                        f'<div class="baro-sub">{mc["sub"]}</div>'
                        f'</div>'
                    )
                    st.markdown(c_html, unsafe_allow_html=True)

        # 顯示跨市場即時資金指標 (VIX, 10Y殖利率, DXY美元, 原油, 黃金)
        if macro_intel["market_cards"]:
            mk_cols = st.columns(len(macro_intel["market_cards"]))
            for idx, mk in enumerate(macro_intel["market_cards"]):
                with mk_cols[idx]:
                    chg_col = "#00e676" if mk["chg"] >= 0 else "#ff5252"
                    mk_html = (
                        f'<div class="baro-card baro-{mk["cls"]}">'
                        f'<div class="baro-title"><span>{mk["title"]}</span>'
                        f'<span class="baro-price">{mk["price"]} <span style="color:{chg_col};font-size:0.80rem;">({mk["chg"]:+.2f}%)</span></span></div>'
                        f'<span class="baro-badge badge-{mk["cls"]}">{mk["badge"]}</span>'
                        f'<div class="baro-sub">{mk["sub"]}</div>'
                        f'</div>'
                    )
                    st.markdown(mk_html, unsafe_allow_html=True)

        if macro_intel["news_items"]:
            with st.expander("📰 點此展開：最新國際財經 / CPI 通膨 / 聯準會焦點快訊與 AI 情緒判讀", expanded=False):
                for n_item in macro_intel["news_items"]:
                    if n_item["link"]:
                        st.markdown(f"- **{n_item['sentiment']}** ｜ [{n_item['title']}]({n_item['link']})")
                    else:
                        st.markdown(f"- **{n_item['sentiment']}** ｜ {n_item['title']}")

        st.markdown("---")

    # ── 第一區：大盤 24 態結構風向標 × 近 2K 閃電抄底雷達 ──
    st.subheader(f"🚥 大盤 24 態結構風向標 × 近 2K 閃電抄底雷達 ({cache['tf_label']})")

    barometer_tickers = ["QQQ", "SOXX", "SPY", "^TWII", "BTC-USD"]
    bull_kws_map = {
        "中樞共振 Buy": "中樞共振Buy", "OB共振支撐": "OB共振支撐", "中樞 Buy": "中樞Buy", "OB支撐確認": "OB支撐",
        "恐慌抄底": "恐慌抄底", "極度超賣": "極度超賣", "Market Bottom": "Market Bottom",
        "超賣預警": "超賣預警", "空頭陷阱": "空頭陷阱"
    }
    bear_kws_map = {
        "中樞共振 Sell": "中樞共振Sell", "OB共振壓力": "OB共振壓力", "中樞 Sell": "中樞Sell", "OB壓力確認": "OB壓力",
        "頂部預警": "頂部預警", "WT 死叉": "WT死叉", "超買預警": "超買預警",
        "多頭陷阱": "多頭陷阱"
    }
    bottom_dip_kws = ["恐慌抄底", "極度超賣", "Market Bottom", "空頭陷阱", "中樞共振 Buy", "OB共振支撐", "中樞 Buy", "OB支撐確認"]
    top_escape_kws = ["頂部預警", "WT 死叉", "多頭陷阱", "中樞共振 Sell", "OB共振壓力", "中樞 Sell", "OB壓力確認"]

    b_cols = st.columns(len(barometer_tickers))
    for idx, b_tick in enumerate(barometer_tickers):
        with b_cols[idx]:
            b_res = baro_results.get(b_tick)
            if b_res:
                bull_count, bear_count = 0, 0
                bull_detail, bear_detail = {}, {}
                sigs = b_res["觸發指標通知"].split(" ｜ ") if b_res["觸發指標通知"] else []

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

                smc_id = b_res["SMC_State_ID"]
                smc_ui = b_res["SMC_Tag_UI"]
                chan_tag = b_res["Chan_Tag"]
                base_advice = b_res["Chan_Action_Base"]
                chan_long = b_res["Chan_Is_Long"]
                chan_cls = b_res["Chan_Cls"]

                struct_is_bull = (smc_id in [1, 2] and (chan_long or chan_cls == 0)) or (smc_id in [3, 4] and chan_long and chan_cls in [1, 2])
                struct_is_bear = (smc_id in [3, 4] and (not chan_long)) or (smc_id in [1, 2] and (not chan_long and chan_cls != 0))

                if bear_count > bull_count:
                    mom_14k_str = f"近14K空偏多 (空{bear_count}>多{bull_count})"
                    tactical_tag = "⚠️ 謹慎做多 (等回踩)" if struct_is_bull else "🔴 順勢做空 / 空單抱牢"
                    style_cls = "warn" if struct_is_bull else "bear"
                elif bull_count > bear_count:
                    mom_14k_str = f"近14K多偏空 (多{bull_count}>空{bear_count})"
                    tactical_tag = "🔥 積極做多 / 順勢抱牢" if struct_is_bull else "⚠️ 謹慎做空 (防反抽)"
                    style_cls = "bull" if struct_is_bull else "warn"
                else:
                    mom_14k_str = f"近14K多空均衡 ({bull_count}:{bear_count})"
                    tactical_tag = "🟢 偏多震盪" if struct_is_bull else ("🔴 偏空震盪" if struct_is_bear else "⚪ 區間觀望")
                    style_cls = "bull" if struct_is_bull else ("bear" if struct_is_bear else "warn")

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
                        st.caption("🟢 **多方：** " + "、".join([f"{k}({v})" for k, v in bull_detail.items()]))
                    if bear_detail:
                        st.caption("🔴 **空方：** " + "、".join([f"{k}({v})" for k, v in bear_detail.items()]))
                    for s in sigs:
                        st.caption(f"• {s}")
            else:
                st.markdown(f"**{b_tick}** - 暫無數據")

    st.markdown("---")

    # ── 第二區：即時過濾與嚴格成交量排序 ──
    use_fund = not scan_mode.startswith("1")
    filtered_rows = []

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

        row_copy = r.copy()
        row_copy["Priority"] = 1 if (fav_first and r["Is_Fav"]) else 0

        if r["All_Signals"] == "":
            if not scan_mode.startswith("1"):
                row_copy["觸發指標通知"] = "無技術訊號"
                filtered_rows.append(row_copy)
        elif len(target_signals) > 0:
            sigs = r["All_Signals"].split(" ｜ ")
            matched_sigs = [s for s in sigs if any(target in s for target in target_signals)]
            if matched_sigs:
                row_copy["觸發指標通知"] = " ｜ ".join(matched_sigs)
                filtered_rows.append(row_copy)

    if cache["failed_tickers"]:
        st.caption(f"⚠️ 無法取得足夠數據的標的：{', '.join(cache['failed_tickers'][:15])}")

    if len(target_signals) == 0 and scan_mode.startswith("1"):
        st.info("💡 你目前已清空所有訊號過濾器！請在左側點擊『✅ 全選訊號』或從下拉選單選擇戰術濾網。")
    elif filtered_rows:
        df_report = pd.DataFrame(filtered_rows)

        vol_col_key = "日均交易量" if vol_sort_by.startswith("日均") else "當前成交量"
        df_report = df_report.sort_values(by=['Priority', vol_col_key], ascending=[False, False]).reset_index(drop=True)

        cols_to_show = ["標的代號", "TV圖表", "SMC 結構", "最新收盤價", "當前成交量", "日均交易量"]
        if use_fund:
            cols_to_show.extend(["PEG (市賺率)", "P/E", "P/B"])
        cols_to_show.append("觸發指標通知")

        st.success(f"🎯 掃描完成！共發現 **{len(df_report)}** 檔符合條件的標的 ｜ 已依 **{vol_sort_by}** 由大到小排序 (耗時: {cache['elapsed']} 秒)")

        st.dataframe(
            df_report[cols_to_show],
            column_config={
                "TV圖表": st.column_config.LinkColumn("TV看圖", display_text="🔗 開圖", width="small"),
                "標的代號": st.column_config.TextColumn("標的代號", width="small"),
                "SMC 結構": st.column_config.TextColumn("SMC 結構", width="small"),
                "最新收盤價": st.column_config.TextColumn("最新收盤價 (漲跌)", width="medium"),
                "當前成交量": st.column_config.NumberColumn("當前成交量", format="compact", width="small"),
                "日均交易量": st.column_config.NumberColumn("日均交易量", format="compact", width="small"),
                "觸發指標通知": st.column_config.TextColumn("觸發指標通知 (近 N 根 K 棒)", width="large"),
            },
            use_container_width=True,
            hide_index=True,
            height=600
        )

        with st.expander("📦 點此展開：各標的「最近 OB / 共振 / 中樞支撐與壓力區間」潛伏表"):
            cols_zone = ["標的代號", "TV圖表", "最新收盤價", "SMC 結構", "最近支撐區", "最近壓力區"]
            st.dataframe(
                df_report[cols_zone],
                column_config={"TV圖表": st.column_config.LinkColumn("TV看圖", display_text="🔗 開圖", width="small")},
                use_container_width=True,
                hide_index=True
            )
    else:
        st.warning("🎯 目前沒有標的同時符合「觸發條件」與「訊號過濾器」。可直接在左側切換戰術濾網或把近 N 根 K 線調大。")
else:
    st.info("👈 請確認左側參數後，點擊 **「🚀 立即啟動掃描」** 開始分析！")
