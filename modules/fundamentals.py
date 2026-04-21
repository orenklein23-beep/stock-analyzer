import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import time

def fmt(val):
    if val is None: return "N/A"
    try:
        val = float(val)
        if val >= 1e12: return f"${val/1e12:.2f}T"
        if val >= 1e9:  return f"${val/1e9:.2f}B"
        if val >= 1e6:  return f"${val/1e6:.2f}M"
        return f"${val:,.2f}"
    except: return "N/A"

def pct(val):
    if val is None: return "N/A"
    try: return f"{round(float(val)*100, 2)}%"
    except: return "N/A"

def load_info(stock):
    for _ in range(3):
        try:
            info = stock.info
            if info and len(info) > 10:
                return info
        except: pass
        time.sleep(2)
    return {}

def show(ticker):
    st.header(f"📊 {ticker} — Full Analysis")

    with st.spinner("Loading data..."):
        stock = yf.Ticker(ticker)
        fast = stock.fast_info
        info = load_info(stock)

    # ── PRICE BANNER ──────────────────────────────────────────
    price = fast.get("lastPrice") or fast.get("regularMarketPrice", 0)
    prev  = fast.get("previousClose", price)
    chg   = round(price - prev, 2)
    chg_p = round((chg / prev) * 100, 2) if prev else 0
    color = "#26a69a" if chg >= 0 else "#ef5350"
    arrow = "▲" if chg >= 0 else "▼"

    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1a1a2e,#16213e);
                padding:28px 32px;border-radius:16px;margin-bottom:24px'>
        <div style='color:#888;font-size:13px;letter-spacing:2px'>{ticker.upper()}</div>
        <div style='color:#fff;font-size:52px;font-weight:800;line-height:1.1'>${round(price,2)}</div>
        <div style='color:{color};font-size:20px;margin-top:4px'>
            {arrow} ${abs(chg)} &nbsp;({chg_p}%) today
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── 12 METRIC CARDS ───────────────────────────────────────
    w52h = fast.get("fiftyTwoWeekHigh") or info.get("fiftyTwoWeekHigh")
    w52l = fast.get("fiftyTwoWeekLow")  or info.get("fiftyTwoWeekLow")
    mcap = fast.get("marketCap")        or info.get("marketCap")

    cards = [
        ("Market Cap",       fmt(mcap)),
        ("Revenue (TTM)",    fmt(info.get("totalRevenue"))),
        ("P/E Ratio",        round(info.get("trailingPE","N/A"),2) if info.get("trailingPE") else "N/A"),
        ("Forward P/E",      round(info.get("forwardPE","N/A"),2)  if info.get("forwardPE")  else "N/A"),
        ("EPS (TTM)",        f"${round(info.get('trailingEps',0),2)}" if info.get("trailingEps") else "N/A"),
        ("Gross Margin",     pct(info.get("grossMargins"))),
        ("Profit Margin",    pct(info.get("profitMargins"))),
        ("Return on Equity", pct(info.get("returnOnEquity"))),
        ("Beta",             round(info.get("beta",0),2) if info.get("beta") else "N/A"),
        ("Dividend Yield",   pct(info.get("dividendYield"))),
        ("52W High",         f"${round(w52h,2)}" if w52h else "N/A"),
        ("52W Low",          f"${round(w52l,2)}" if w52l else "N/A"),
    ]

    cols = st.columns(4)
    for i,(label,val) in enumerate(cards):
        cols[i%4].metric(label, val)

    st.divider()

    # ── CANDLESTICK + VOLUME ───────────────────────────────────
    st.subheader("📈 Price Chart")
    period = st.radio("Period", ["1mo","3mo","6mo","1y","2y","5y"],
                      horizontal=True, index=3, key="period")
    try:
        hist = stock.history(period=period)
        if not hist.empty:
            hist["MA20"] = hist["Close"].rolling(20).mean()
            hist["MA50"] = hist["Close"].rolling(50).mean()

            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                row_heights=[0.72,0.28], vertical_spacing=0.03)

            fig.add_trace(go.Candlestick(
                x=hist.index, open=hist.Open, high=hist.High,
                low=hist.Low, close=hist.Close, name="Price",
                increasing_line_color="#26a69a",
                decreasing_line_color="#ef5350"
            ), row=1, col=1)

            fig.add_trace(go.Scatter(x=hist.index, y=hist.MA20,
                name="MA20", line=dict(color="#FFA500", width=1.4)), row=1, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=hist.MA50,
                name="MA50", line=dict(color="#9B59B6", width=1.4)), row=1, col=1)

            vol_colors = ["#26a69a" if c>=o else "#ef5350"
                          for c,o in zip(hist.Close, hist.Open)]
            fig.add_trace(go.Bar(x=hist.index, y=hist.Volume,
                name="Volume", marker_color=vol_colors, opacity=0.7), row=2, col=1)

            fig.update_layout(height=520, xaxis_rangeslider_visible=False,
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font_color="white", legend=dict(orientation="h", y=1.05))
            fig.update_xaxes(gridcolor="#1e1e1e")
            fig.update_yaxes(gridcolor="#1e1e1e")
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Price chart error: {e}")

    st.divider()

    # ── REVENUE / GROSS PROFIT / NET INCOME ───────────────────
    st.subheader("💰 Revenue, Gross Profit & Net Income")
    try:
        fin = stock.financials.T.sort_index()
        fin.index = fin.index.astype(str).str[:10]

        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
        if "Total Revenue" in fin.columns:
            fig2.add_trace(go.Bar(x=fin.index, y=fin["Total Revenue"],
                name="Revenue", marker_color="#4A90D9", opacity=0.9), secondary_y=False)
        if "Gross Profit" in fin.columns:
            fig2.add_trace(go.Bar(x=fin.index, y=fin["Gross Profit"],
                name="Gross Profit", marker_color="#9B59B6", opacity=0.9), secondary_y=False)
        if "Net Income" in fin.columns:
            fig2.add_trace(go.Scatter(x=fin.index, y=fin["Net Income"],
                name="Net Income", line=dict(color="#27AE60", width=3),
                mode="lines+markers", marker=dict(size=9)), secondary_y=True)

        fig2.update_layout(height=400, barmode="group",
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font_color="white", legend=dict(orientation="h", y=1.1))
        fig2.update_xaxes(gridcolor="#1e1e1e")
        fig2.update_yaxes(gridcolor="#1e1e1e")
        st.plotly_chart(fig2, use_container_width=True)
    except Exception as e:
        st.warning(f"Financials error: {e}")

    st.divider()

    # ── MARGIN TRENDS ──────────────────────────────────────────
    st.subheader("📊 Margin Trends Over Time")
    try:
        fin = stock.financials.T.sort_index()
        fin.index = fin.index.astype(str).str[:10]
        if all(c in fin.columns for c in ["Total Revenue","Gross Profit","Net Income"]):
            m = pd.DataFrame(index=fin.index)
            m["Gross Margin %"] = (fin["Gross Profit"] / fin["Total Revenue"] * 100).round(1)
            m["Net Margin %"]   = (fin["Net Income"]   / fin["Total Revenue"] * 100).round(1)

            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(x=m.index, y=m["Gross Margin %"],
                name="Gross Margin %", line=dict(color="#4A90D9", width=3),
                mode="lines+markers", fill="tozeroy",
                fillcolor="rgba(74,144,217,0.12)"))
            fig3.add_trace(go.Scatter(x=m.index, y=m["Net Margin %"],
                name="Net Margin %", line=dict(color="#27AE60", width=3),
                mode="lines+markers", fill="tozeroy",
                fillcolor="rgba(39,174,96,0.12)"))
            fig3.update_layout(height=350,
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font_color="white", yaxis_title="Margin %")
            fig3.update_xaxes(gridcolor="#1e1e1e")
            fig3.update_yaxes(gridcolor="#1e1e1e")
            st.plotly_chart(fig3, use_container_width=True)
    except Exception as e:
        st.warning(f"Margin chart error: {e}")

    st.divider()

    # ── BALANCE SHEET ──────────────────────────────────────────
    st.subheader("🏦 Balance Sheet")
    try:
        bs = stock.balance_sheet.T.sort_index()
        bs.index = bs.index.astype(str).str[:10]

        fig4 = go.Figure()
        if "Total Assets" in bs.columns:
            fig4.add_trace(go.Bar(x=bs.index, y=bs["Total Assets"],
                name="Total Assets", marker_color="#4A90D9"))
        if "Total Liabilities Net Minority Interest" in bs.columns:
            fig4.add_trace(go.Bar(x=bs.index,
                y=bs["Total Liabilities Net Minority Interest"],
                name="Total Liabilities", marker_color="#E74C3C"))
        if "Stockholders Equity" in bs.columns:
            fig4.add_trace(go.Bar(x=bs.index, y=bs["Stockholders Equity"],
                name="Equity", marker_color="#27AE60"))

        fig4.update_layout(barmode="group", height=380,
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font_color="white", legend=dict(orientation="h", y=1.1))
        fig4.update_xaxes(gridcolor="#1e1e1e")
        fig4.update_yaxes(gridcolor="#1e1e1e")
        st.plotly_chart(fig4, use_container_width=True)
    except Exception as e:
        st.warning(f"Balance sheet error: {e}")

    st.divider()

    # ── CASH FLOW ──────────────────────────────────────────────
    st.subheader("💵 Cash Flow")
    try:
        cf = stock.cashflow.T.sort_index()
        cf.index = cf.index.astype(str).str[:10]

        fig5 = go.Figure()
        if "Operating Cash Flow" in cf.columns:
            fig5.add_trace(go.Bar(x=cf.index, y=cf["Operating Cash Flow"],
                name="Operating CF", marker_color="#27AE60"))
        if "Free Cash Flow" in cf.columns:
            fig5.add_trace(go.Bar(x=cf.index, y=cf["Free Cash Flow"],
                name="Free CF", marker_color="#4A90D9"))
        if "Capital Expenditure" in cf.columns:
            fig5.add_trace(go.Bar(x=cf.index, y=cf["Capital Expenditure"],
                name="CapEx", marker_color="#E74C3C"))

        fig5.update_layout(barmode="group", height=380,
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font_color="white", legend=dict(orientation="h", y=1.1))
        fig5.update_xaxes(gridcolor="#1e1e1e")
        fig5.update_yaxes(gridcolor="#1e1e1e")
        st.plotly_chart(fig5, use_container_width=True)
    except Exception as e:
        st.warning(f"Cash flow error: {e}")

    st.divider()

    # ── 52W GAUGE ──────────────────────────────────────────────
    st.subheader("📍 52-Week Price Position")
    try:
        if w52h and w52l and price:
            pos = (price - w52l) / (w52h - w52l) * 100
            fig6 = go.Figure(go.Indicator(
                mode="gauge+number",
                value=round(pos, 1),
                title={"text": f"${round(w52l,2)} ← current → ${round(w52h,2)}",
                       "font": {"color":"white"}},
                gauge={
                    "axis": {"range":[0,100], "tickcolor":"white"},
                    "bar":  {"color":"#4A90D9"},
                    "steps":[
                        {"range":[0,25],  "color":"#E74C3C"},
                        {"range":[25,75], "color":"#F39C12"},
                        {"range":[75,100],"color":"#27AE60"},
                    ]
                },
                number={"suffix":"%","font":{"color":"white"}}
            ))
            fig6.update_layout(height=280,
                paper_bgcolor="#0e1117", font_color="white")
            st.plotly_chart(fig6, use_container_width=True)
    except Exception as e:
        st.warning(f"Gauge error: {e}")

    st.divider()

    # ── ANALYST TARGETS ────────────────────────────────────────
    st.subheader("🎯 Analyst Price Targets")
    try:
        low  = info.get("targetLowPrice")
        mean = info.get("targetMeanPrice")
        high = info.get("targetHighPrice")
        rec  = info.get("recommendationKey","").upper()

        if mean:
            upside = round(((mean - price) / price) * 100, 1)
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Target Low",  f"${low}"  if low  else "N/A")
            c2.metric("Target Mean", f"${mean}" if mean else "N/A",
                      delta=f"{upside}% upside")
            c3.metric("Target High", f"${high}" if high else "N/A")
            c4.metric("Consensus",   rec if rec else "N/A")
        else:
            st.info("Analyst targets not available for this ticker.")
    except Exception as e:
        st.warning(f"Analyst targets error: {e}")
