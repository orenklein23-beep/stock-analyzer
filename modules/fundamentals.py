import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def fmt(val):
    if val is None: return "N/A"
    try:
        v = float(val)
        if v >= 1e12: return f"${v/1e12:.2f}T"
        if v >= 1e9:  return f"${v/1e9:.2f}B"
        if v >= 1e6:  return f"${v/1e6:.2f}M"
        return f"${v:,.2f}"
    except: return "N/A"

def safe(df, col):
    try:
        if col in df.columns:
            val = df[col].dropna()
            if len(val): return float(val.iloc[-1])
    except: pass
    return None

def show(ticker):
    st.header(f"📊 {ticker} — Full Analysis")

    with st.spinner("Fetching data..."):
        stock = yf.Ticker(ticker)
        f = stock.fast_info

        try: fin = stock.financials.T.sort_index()
        except: fin = pd.DataFrame()

        try: bs = stock.balance_sheet.T.sort_index()
        except: bs = pd.DataFrame()

        try: cf = stock.cashflow.T.sort_index()
        except: cf = pd.DataFrame()

        try: qfin = stock.quarterly_financials.T.sort_index()
        except: qfin = pd.DataFrame()

        try:
            h52 = stock.history(period="1y")
            w52h = float(h52["High"].max()) if not h52.empty else 0
            w52l = float(h52["Low"].min())  if not h52.empty else 0
        except:
            w52h, w52l = 0, 0

        try: apt = stock.analyst_price_targets
        except: apt = None

    # ── CORE VALUES ────────────────────────────────────────────
    price  = float(f.get("lastPrice") or f.get("regularMarketPrice") or 0)
    prev   = float(f.get("previousClose") or price)
    mcap   = float(f.get("marketCap") or 0)
    shares = float(f.get("shares") or f.get("impliedShares") or 0)

    rev     = safe(fin, "Total Revenue")
    gross_p = safe(fin, "Gross Profit")
    net_inc = safe(fin, "Net Income")
    op_inc  = safe(fin, "Operating Income")
    ebitda  = safe(fin, "EBITDA") or safe(fin, "Normalized EBITDA")
    debt    = safe(bs, "Total Debt")
    cash    = safe(bs, "Cash And Cash Equivalents") or safe(bs, "Cash Cash Equivalents And Short Term Investments")
    equity  = safe(bs, "Stockholders Equity") or safe(bs, "Common Stock Equity")
    assets  = safe(bs, "Total Assets")
    op_cf   = safe(cf, "Operating Cash Flow")
    fcf     = safe(cf, "Free Cash Flow")
    capex   = safe(cf, "Capital Expenditure")

    net_debt = (debt - cash)        if debt and cash else None
    gross_m  = round(gross_p/rev*100,1) if gross_p and rev else None
    net_m    = round(net_inc/rev*100,1) if net_inc and rev else None
    op_m     = round(op_inc/rev*100,1)  if op_inc  and rev else None
    eps      = net_inc/shares           if net_inc and shares else None
    pe       = price/eps                if eps and eps > 0 else None
    pb       = mcap/equity              if equity and equity > 0 else None
    ps       = mcap/rev                 if rev and rev > 0 else None
    roe      = net_inc/equity*100       if net_inc and equity and equity > 0 else None
    de       = debt/equity              if debt and equity and equity > 0 else None
    capex_d  = abs(capex)               if capex else None

    chg  = round(price - prev, 2)
    chgp = round((chg/prev)*100, 2) if prev else 0
    pcol = "#26a69a" if chg >= 0 else "#ef5350"
    arr  = "▲" if chg >= 0 else "▼"

    # ── PRICE BANNER ──────────────────────────────────────────
    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1a1a2e,#16213e);
                padding:28px 32px;border-radius:16px;margin-bottom:24px'>
        <div style='color:#888;font-size:12px;letter-spacing:3px'>{ticker.upper()}</div>
        <div style='color:#fff;font-size:56px;font-weight:800;line-height:1.1'>${round(price,2)}</div>
        <div style='color:{pcol};font-size:20px;margin-top:6px'>
            {arr} ${abs(chg)} ({chgp}%) today
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── METRIC CARDS ──────────────────────────────────────────
    cards = [
        ("Market Cap",       fmt(mcap)),
        ("Revenue (TTM)",    fmt(rev)),
        ("Gross Profit",     fmt(gross_p)),
        ("Net Income",       fmt(net_inc)),
        ("EPS",              f"${round(eps,2)}"  if eps    else "N/A"),
        ("P/E Ratio",        round(pe,1)          if pe     else "N/A"),
        ("P/B Ratio",        round(pb,2)          if pb     else "N/A"),
        ("P/S Ratio",        round(ps,2)          if ps     else "N/A"),
        ("Gross Margin",     f"{gross_m}%"        if gross_m else "N/A"),
        ("Net Margin",       f"{net_m}%"          if net_m   else "N/A"),
        ("Op Margin",        f"{op_m}%"           if op_m    else "N/A"),
        ("Return on Equity", f"{round(roe,1)}%"   if roe     else "N/A"),
        ("Debt/Equity",      round(de,2)          if de     else "N/A"),
        ("Total Debt",       fmt(debt)),
        ("Cash",             fmt(cash)),
        ("Net Debt",         fmt(net_debt)),
        ("Free Cash Flow",   fmt(fcf)),
        ("Op Cash Flow",     fmt(op_cf)),
        ("EBITDA",           fmt(ebitda)),
        ("CapEx",            fmt(capex_d)),
        ("52W High",         f"${round(w52h,2)}" if w52h else "N/A"),
        ("52W Low",          f"${round(w52l,2)}" if w52l else "N/A"),
        ("Total Assets",     fmt(assets)),
        ("Equity",           fmt(equity)),
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
        h = stock.history(period=period)
        if not h.empty:
            h["MA20"] = h["Close"].rolling(20).mean()
            h["MA50"] = h["Close"].rolling(50).mean()
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                row_heights=[0.72,0.28], vertical_spacing=0.03)
            fig.add_trace(go.Candlestick(
                x=h.index, open=h.Open, high=h.High,
                low=h.Low, close=h.Close, name="Price",
                increasing_line_color="#26a69a",
                decreasing_line_color="#ef5350"
            ), row=1, col=1)
            fig.add_trace(go.Scatter(x=h.index, y=h.MA20, name="MA20",
                line=dict(color="#FFA500",width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=h.index, y=h.MA50, name="MA50",
                line=dict(color="#9B59B6",width=1.5)), row=1, col=1)
            vcols = ["#26a69a" if c>=o else "#ef5350"
                     for c,o in zip(h.Close, h.Open)]
            fig.add_trace(go.Bar(x=h.index, y=h.Volume, name="Volume",
                marker_color=vcols, opacity=0.7), row=2, col=1)
            fig.update_layout(height=520, xaxis_rangeslider_visible=False,
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font_color="white", legend=dict(orientation="h",y=1.05))
            fig.update_xaxes(gridcolor="#1e1e1e")
            fig.update_yaxes(gridcolor="#1e1e1e")
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.warning(f"Price chart: {e}")

    st.divider()

    # ── REVENUE / GROSS / NET ──────────────────────────────────
    st.subheader("💰 Revenue, Gross Profit & Net Income")
    if not fin.empty:
        try:
            f2 = fin.copy()
            f2.index = f2.index.astype(str).str[:10]
            fig2 = make_subplots(specs=[[{"secondary_y":True}]])
            for cn, color, sy in [
                ("Total Revenue","#4A90D9",False),
                ("Gross Profit","#9B59B6",False),
            ]:
                if cn in f2.columns:
                    fig2.add_trace(go.Bar(x=f2.index, y=f2[cn],
                        name=cn, marker_color=color, opacity=0.9), secondary_y=sy)
            if "Net Income" in f2.columns:
                fig2.add_trace(go.Scatter(x=f2.index, y=f2["Net Income"],
                    name="Net Income", line=dict(color="#27AE60",width=3),
                    mode="lines+markers", marker=dict(size=9)), secondary_y=True)
            fig2.update_layout(height=400, barmode="group",
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font_color="white", legend=dict(orientation="h",y=1.1))
            fig2.update_xaxes(gridcolor="#1e1e1e")
            fig2.update_yaxes(gridcolor="#1e1e1e")
            st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.warning(f"Revenue chart: {e}")

    st.divider()

    # ── MARGIN TRENDS ──────────────────────────────────────────
    st.subheader("📊 Margin Trends")
    if not fin.empty and "Total Revenue" in fin.columns:
        try:
            f3 = fin.copy()
            f3.index = f3.index.astype(str).str[:10]
            m = pd.DataFrame(index=f3.index)
            if "Gross Profit"     in f3.columns: m["Gross Margin %"] = (f3["Gross Profit"]    /f3["Total Revenue"]*100).round(1)
            if "Net Income"       in f3.columns: m["Net Margin %"]   = (f3["Net Income"]      /f3["Total Revenue"]*100).round(1)
            if "Operating Income" in f3.columns: m["Op Margin %"]    = (f3["Operating Income"]/f3["Total Revenue"]*100).round(1)
            colors = ["#4A90D9","#27AE60","#FFA500"]
            fig3 = go.Figure()
            for i, c in enumerate(m.columns):
                r,g,b = tuple(int(colors[i].lstrip("#")[j:j+2],16) for j in (0,2,4))
                fig3.add_trace(go.Scatter(x=m.index, y=m[c], name=c,
                    line=dict(color=colors[i],width=3), mode="lines+markers",
                    fill="tozeroy", fillcolor=f"rgba({r},{g},{b},0.1)"))
            fig3.update_layout(height=350,
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font_color="white", yaxis_title="Margin %")
            fig3.update_xaxes(gridcolor="#1e1e1e")
            fig3.update_yaxes(gridcolor="#1e1e1e")
            st.plotly_chart(fig3, use_container_width=True)
        except Exception as e:
            st.warning(f"Margin chart: {e}")

    st.divider()

    # ── BALANCE SHEET ──────────────────────────────────────────
    st.subheader("🏦 Balance Sheet")
    if not bs.empty:
        try:
            b2 = bs.copy()
            b2.index = b2.index.astype(str).str[:10]
            fig4 = go.Figure()
            for cn, color in [
                ("Total Assets","#4A90D9"),
                ("Total Liabilities Net Minority Interest","#E74C3C"),
                ("Common Stock Equity","#27AE60"),
                ("Total Debt","#F39C12"),
            ]:
                if cn in b2.columns:
                    fig4.add_trace(go.Bar(x=b2.index, y=b2[cn],
                        name=cn.replace(" Net Minority Interest",""),
                        marker_color=color))
            fig4.update_layout(barmode="group", height=400,
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font_color="white", legend=dict(orientation="h",y=1.1))
            fig4.update_xaxes(gridcolor="#1e1e1e")
            fig4.update_yaxes(gridcolor="#1e1e1e")
            st.plotly_chart(fig4, use_container_width=True)
        except Exception as e:
            st.warning(f"Balance sheet: {e}")

    st.divider()

    # ── CASH FLOW ──────────────────────────────────────────────
    st.subheader("💵 Cash Flow")
    if not cf.empty:
        try:
            c2 = cf.copy()
            c2.index = c2.index.astype(str).str[:10]
            fig5 = go.Figure()
            for cn, color in [
                ("Operating Cash Flow","#27AE60"),
                ("Free Cash Flow","#4A90D9"),
                ("Capital Expenditure","#E74C3C"),
            ]:
                if cn in c2.columns:
                    vals = c2[cn].abs() if cn == "Capital Expenditure" else c2[cn]
                    fig5.add_trace(go.Bar(x=c2.index, y=vals,
                        name=cn, marker_color=color))
            fig5.update_layout(barmode="group", height=380,
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font_color="white", legend=dict(orientation="h",y=1.1))
            fig5.update_xaxes(gridcolor="#1e1e1e")
            fig5.update_yaxes(gridcolor="#1e1e1e")
            st.plotly_chart(fig5, use_container_width=True)
        except Exception as e:
            st.warning(f"Cash flow: {e}")

    st.divider()

    # ── QUARTERLY EARNINGS ─────────────────────────────────────
    st.subheader("📅 Quarterly Revenue & Net Income")
    if not qfin.empty:
        try:
            q2 = qfin.copy()
            q2.index = q2.index.astype(str).str[:10]
            fig6 = make_subplots(specs=[[{"secondary_y":True}]])
            if "Total Revenue" in q2.columns:
                fig6.add_trace(go.Bar(x=q2.index, y=q2["Total Revenue"],
                    name="Revenue", marker_color="#4A90D9", opacity=0.9),
                    secondary_y=False)
            if "Net Income" in q2.columns:
                fig6.add_trace(go.Scatter(x=q2.index, y=q2["Net Income"],
                    name="Net Income", line=dict(color="#27AE60",width=3),
                    mode="lines+markers", marker=dict(size=9)),
                    secondary_y=True)
            fig6.update_layout(height=380, barmode="group",
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font_color="white", legend=dict(orientation="h",y=1.1))
            fig6.update_xaxes(gridcolor="#1e1e1e")
            fig6.update_yaxes(gridcolor="#1e1e1e")
            st.plotly_chart(fig6, use_container_width=True)
        except Exception as e:
            st.warning(f"Quarterly chart: {e}")

    st.divider()

    # ── 52W GAUGE ──────────────────────────────────────────────
    st.subheader("📍 52-Week Price Position")
    if w52h and w52l and price:
        try:
            pos = (price - w52l) / (w52h - w52l) * 100
            fig7 = go.Figure(go.Indicator(
                mode="gauge+number",
                value=round(pos,1),
                title={"text":f"Low ${round(w52l,2)}  ←  current  →  High ${round(w52h,2)}",
                       "font":{"color":"white","size":14}},
                gauge={
                    "axis":{"range":[0,100],"tickcolor":"white"},
                    "bar":{"color":"#4A90D9"},
                    "steps":[
                        {"range":[0,30],"color":"#E74C3C"},
                        {"range":[30,70],"color":"#F39C12"},
                        {"range":[70,100],"color":"#27AE60"},
                    ]
                },
                number={"suffix":"%","font":{"color":"white"}}
            ))
            fig7.update_layout(height=280,
                paper_bgcolor="#0e1117", font_color="white")
            st.plotly_chart(fig7, use_container_width=True)
        except Exception as e:
            st.warning(f"Gauge: {e}")

    st.divider()

    # ── ANALYST PRICE TARGETS ─────────────────────────────────
    st.subheader("🎯 Analyst Price Targets")
    try:
        if apt is not None and hasattr(apt, '__len__') and len(apt) > 0:
            low_t    = apt.get("low")
            mean_t   = apt.get("mean")
            high_t   = apt.get("high")
            median_t = apt.get("median")
            upside   = round(((mean_t-price)/price)*100,1) if mean_t and price else None

            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Target Low",    f"${round(low_t,2)}"    if low_t    else "N/A")
            c2.metric("Target Median", f"${round(median_t,2)}" if median_t else "N/A")
            c3.metric("Target Mean",   f"${round(mean_t,2)}"   if mean_t   else "N/A",
                      delta=f"{upside}% upside" if upside else None)
            c4.metric("Target High",   f"${round(high_t,2)}"   if high_t   else "N/A")

            if mean_t and low_t and high_t:
                pts = {
                    "Label": ["52W Low","Current Price","Target Low","Target Median","Target Mean","Target High","52W High"],
                    "Price": [w52l, price, low_t, median_t or mean_t, mean_t, high_t, w52h],
                    "Color": ["#888","#FFA500","#E74C3C","#F39C12","#4A90D9","#27AE60","#888"]
                }
                fig8 = go.Figure()
                fig8.add_trace(go.Scatter(
                    x=pts["Label"], y=pts["Price"],
                    mode="lines+markers",
                    line=dict(color="#333",width=2),
                    marker=dict(size=14, color=pts["Color"],
                                line=dict(color="white",width=2)),
                    text=[f"${round(p,2)}" for p in pts["Price"]],
                    textposition="top center",
                    textfont=dict(color="white")
                ))
                fig8.add_hline(y=price, line_dash="dash",
                    line_color="#FFA500",
                    annotation_text=f"  Current ${round(price,2)}",
                    annotation_font_color="#FFA500")
                fig8.update_layout(height=350,
                    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                    font_color="white", yaxis_title="Price ($)",
                    showlegend=False)
                fig8.update_xaxes(gridcolor="#1e1e1e")
                fig8.update_yaxes(gridcolor="#1e1e1e")
                st.plotly_chart(fig8, use_container_width=True)
        else:
            st.info("Analyst targets not available for this ticker.")
    except Exception as e:
        st.info("Analyst targets not available for this ticker.")
