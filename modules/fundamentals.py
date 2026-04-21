import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import requests

def get_stock_data(ticker):
    """Try yfinance first, return stock object and info dict"""
    try:
        stock = yf.Ticker(ticker)
        fast = stock.fast_info
        info = {}
        try:
            info = stock.info
        except Exception:
            pass
        return stock, fast, info
    except Exception as e:
        st.error(f"Could not load {ticker}: {e}")
        return None, None, None

def fmt_large(val):
    """Format large numbers into readable form"""
    if val is None:
        return "N/A"
    try:
        val = float(val)
        if val >= 1e12:
            return f"${val/1e12:.2f}T"
        elif val >= 1e9:
            return f"${val/1e9:.2f}B"
        elif val >= 1e6:
            return f"${val/1e6:.2f}M"
        else:
            return f"${val:,.0f}"
    except Exception:
        return "N/A"

def show(ticker):
    st.header(f"📊 Fundamentals — {ticker}")

    stock, fast, info = get_stock_data(ticker)
    if stock is None:
        return

    # ── PRICE HEADER ──────────────────────────────────────────────
    price = fast.get("lastPrice") or fast.get("regularMarketPrice", 0)
    prev_close = fast.get("previousClose", 0)
    change = round(price - prev_close, 2) if prev_close else 0
    change_pct = round((change / prev_close) * 100, 2) if prev_close else 0
    direction = "▲" if change >= 0 else "▼"
    color = "green" if change >= 0 else "red"

    st.markdown(f"""
    <div style='background: linear-gradient(135deg, #1a1a2e, #16213e); 
                padding: 24px; border-radius: 16px; margin-bottom: 20px;'>
        <div style='color: #aaa; font-size: 14px; margin-bottom: 4px'>{ticker}</div>
        <div style='color: white; font-size: 48px; font-weight: 700'>${round(price,2)}</div>
        <div style='color: {color}; font-size: 20px'>{direction} ${abs(change)} ({change_pct}%)</div>
    </div>
    """, unsafe_allow_html=True)

    # ── KEY METRICS ROW ───────────────────────────────────────────
    market_cap = fast.get("marketCap", None)
    pe = info.get("trailingPE", None)
    forward_pe = info.get("forwardPE", None)
    eps = info.get("trailingEps", None)
    dividend = info.get("dividendYield", None)
    beta = info.get("beta", None)
    week52_high = fast.get("fiftyTwoWeekHigh", None)
    week52_low = fast.get("fiftyTwoWeekLow", None)
    revenue = info.get("totalRevenue", None)
    gross_margin = info.get("grossMargins", None)
    profit_margin = info.get("profitMargins", None)
    roe = info.get("returnOnEquity", None)

    metrics = [
        ("Market Cap", fmt_large(market_cap)),
        ("Revenue (TTM)", fmt_large(revenue)),
        ("P/E Ratio", round(pe, 2) if pe else "N/A"),
        ("Forward P/E", round(forward_pe, 2) if forward_pe else "N/A"),
        ("EPS (TTM)", f"${round(eps,2)}" if eps else "N/A"),
        ("Gross Margin", f"{round(gross_margin*100,1)}%" if gross_margin else "N/A"),
        ("Profit Margin", f"{round(profit_margin*100,1)}%" if profit_margin else "N/A"),
        ("Return on Equity", f"{round(roe*100,1)}%" if roe else "N/A"),
        ("Beta", round(beta, 2) if beta else "N/A"),
        ("Dividend Yield", f"{round(dividend*100,2)}%" if dividend else "N/A"),
        ("52W High", f"${round(week52_high,2)}" if week52_high else "N/A"),
        ("52W Low", f"${round(week52_low,2)}" if week52_low else "N/A"),
    ]

    cols = st.columns(4)
    for i, (label, value) in enumerate(metrics):
        with cols[i % 4]:
            st.metric(label, value)

    st.divider()

    # ── PRICE CHART ───────────────────────────────────────────────
    st.subheader("📈 Price History")
    period_choice = st.radio("Period", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], horizontal=True, index=3)

    try:
        hist = stock.history(period=period_choice)
        if not hist.empty:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                row_heights=[0.7, 0.3], vertical_spacing=0.05)

            fig.add_trace(go.Candlestick(
                x=hist.index,
                open=hist["Open"],
                high=hist["High"],
                low=hist["Low"],
                close=hist["Close"],
                name="Price",
                increasing_line_color="#26a69a",
                decreasing_line_color="#ef5350"
            ), row=1, col=1)

            # 50-day MA
            hist["MA50"] = hist["Close"].rolling(50).mean()
            fig.add_trace(go.Scatter(
                x=hist.index, y=hist["MA50"],
                name="50-day MA", line=dict(color="#FFA500", width=1.5)
            ), row=1, col=1)

            # Volume bars
            colors = ["#26a69a" if c >= o else "#ef5350"
                      for c, o in zip(hist["Close"], hist["Open"])]
            fig.add_trace(go.Bar(
                x=hist.index, y=hist["Volume"],
                name="Volume", marker_color=colors, opacity=0.7
            ), row=2, col=1)

            fig.update_layout(
                height=500,
                xaxis_rangeslider_visible=False,
                paper_bgcolor="#0e1117",
                plot_bgcolor="#0e1117",
                font_color="white",
                legend=dict(orientation="h", y=1.05)
            )
            fig.update_xaxes(gridcolor="#2a2a2a")
            fig.update_yaxes(gridcolor="#2a2a2a")

            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load price chart: {e}")

    st.divider()

    # ── FINANCIALS ────────────────────────────────────────────────
    st.subheader("💰 Revenue & Profit Over Time")
    try:
        fin = stock.financials.T.sort_index()
        fin.index = fin.index.astype(str).str[:10]

        fig2 = make_subplots(specs=[[{"secondary_y": True}]])

        if "Total Revenue" in fin.columns:
            fig2.add_trace(go.Bar(
                x=fin.index, y=fin["Total Revenue"],
                name="Revenue", marker_color="#4A90D9", opacity=0.85
            ), secondary_y=False)

        if "Gross Profit" in fin.columns:
            fig2.add_trace(go.Bar(
                x=fin.index, y=fin["Gross Profit"],
                name="Gross Profit", marker_color="#9B59B6", opacity=0.85
            ), secondary_y=False)

        if "Net Income" in fin.columns:
            fig2.add_trace(go.Scatter(
                x=fin.index, y=fin["Net Income"],
                name="Net Income", line=dict(color="#27AE60", width=3),
                mode="lines+markers", marker=dict(size=8)
            ), secondary_y=True)

        fig2.update_layout(
            height=400, barmode="group",
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font_color="white", legend=dict(orientation="h", y=1.1)
        )
        fig2.update_xaxes(gridcolor="#2a2a2a")
        fig2.update_yaxes(gridcolor="#2a2a2a")
        st.plotly_chart(fig2, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load financials chart: {e}")

    st.divider()

    # ── MARGINS OVER TIME ─────────────────────────────────────────
    st.subheader("📊 Margin Trends")
    try:
        fin = stock.financials.T.sort_index()
        fin.index = fin.index.astype(str).str[:10]

        if "Total Revenue" in fin.columns and "Gross Profit" in fin.columns and "Net Income" in fin.columns:
            margins = pd.DataFrame(index=fin.index)
            margins["Gross Margin %"] = (fin["Gross Profit"] / fin["Total Revenue"] * 100).round(1)
            margins["Net Margin %"] = (fin["Net Income"] / fin["Total Revenue"] * 100).round(1)

            fig3 = go.Figure()
            fig3.add_trace(go.Scatter(
                x=margins.index, y=margins["Gross Margin %"],
                name="Gross Margin %", line=dict(color="#4A90D9", width=3),
                mode="lines+markers", fill="tozeroy", fillcolor="rgba(74,144,217,0.15)"
            ))
            fig3.add_trace(go.Scatter(
                x=margins.index, y=margins["Net Margin %"],
                name="Net Margin %", line=dict(color="#27AE60", width=3),
                mode="lines+markers", fill="tozeroy", fillcolor="rgba(39,174,96,0.15)"
            ))
            fig3.update_layout(
                height=350,
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font_color="white", yaxis_title="Margin %"
            )
            fig3.update_xaxes(gridcolor="#2a2a2a")
            fig3.update_yaxes(gridcolor="#2a2a2a")
            st.plotly_chart(fig3, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load margin chart: {e}")

    st.divider()

    # ── BALANCE SHEET ─────────────────────────────────────────────
    st.subheader("🏦 Balance Sheet — Assets vs Liabilities")
    try:
        bs = stock.balance_sheet.T.sort_index()
        bs.index = bs.index.astype(str).str[:10]

        fig4 = go.Figure()
        if "Total Assets" in bs.columns:
            fig4.add_trace(go.Bar(x=bs.index, y=bs["Total Assets"], name="Total Assets", marker_color="#4A90D9"))
        if "Total Liabilities Net Minority Interest" in bs.columns:
            fig4.add_trace(go.Bar(x=bs.index, y=bs["Total Liabilities Net Minority Interest"], name="Total Liabilities", marker_color="#E74C3C"))
        if "Stockholders Equity" in bs.columns:
            fig4.add_trace(go.Bar(x=bs.index, y=bs["Stockholders Equity"], name="Equity", marker_color="#27AE60"))

        fig4.update_layout(
            barmode="group", height=380,
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font_color="white", legend=dict(orientation="h", y=1.1)
        )
        fig4.update_xaxes(gridcolor="#2a2a2a")
        fig4.update_yaxes(gridcolor="#2a2a2a")
        st.plotly_chart(fig4, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load balance sheet: {e}")

    st.divider()

    # ── CASH FLOW ─────────────────────────────────────────────────
    st.subheader("💵 Cash Flow")
    try:
        cf = stock.cashflow.T.sort_index()
        cf.index = cf.index.astype(str).str[:10]

        fig5 = go.Figure()
        if "Operating Cash Flow" in cf.columns:
            fig5.add_trace(go.Bar(x=cf.index, y=cf["Operating Cash Flow"], name="Operating CF", marker_color="#27AE60"))
        if "Free Cash Flow" in cf.columns:
            fig5.add_trace(go.Bar(x=cf.index, y=cf["Free Cash Flow"], name="Free CF", marker_color="#4A90D9"))
        if "Capital Expenditure" in cf.columns:
            fig5.add_trace(go.Bar(x=cf.index, y=cf["Capital Expenditure"], name="CapEx", marker_color="#E74C3C"))

        fig5.update_layout(
            barmode="group", height=380,
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font_color="white", legend=dict(orientation="h", y=1.1)
        )
        fig5.update_xaxes(gridcolor="#2a2a2a")
        fig5.update_yaxes(gridcolor="#2a2a2a")
        st.plotly_chart(fig5, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load cash flow: {e}")

    st.divider()

    # ── 52 WEEK RANGE GAUGE ───────────────────────────────────────
    st.subheader("📍 52-Week Price Position")
    try:
        if week52_high and week52_low and price:
            position = (price - week52_low) / (week52_high - week52_low) * 100

            fig6 = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=round(position, 1),
                delta={"reference": 50, "suffix": "%"},
                title={"text": f"Where ${round(price,2)} sits in 52W range (${round(week52_low,2)} — ${round(week52_high,2)})", "font": {"color": "white"}},
                gauge={
                    "axis": {"range": [0, 100], "tickcolor": "white"},
                    "bar": {"color": "#4A90D9"},
                    "steps": [
                        {"range": [0, 25], "color": "#E74C3C"},
                        {"range": [25, 75], "color": "#F39C12"},
                        {"range": [75, 100], "color": "#27AE60"},
                    ],
                    "threshold": {"line": {"color": "white", "width": 3}, "value": position}
                },
                number={"suffix": "%", "font": {"color": "white"}}
            ))
            fig6.update_layout(
                height=300,
                paper_bgcolor="#0e1117",
                font_color="white"
            )
            st.plotly_chart(fig6, use_container_width=True)
    except Exception as e:
        st.warning(f"Could not load gauge: {e}")
