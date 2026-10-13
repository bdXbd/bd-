                    bear_detail = {}
                    
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
