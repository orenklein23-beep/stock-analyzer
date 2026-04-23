import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

def show(ticker):
    st.header(f"📈 {ticker} — Earnings Analysis")

    with st.spinner("Loading earnings data..."):
        stock = yf.Ticker(ticker)

        try: hist_earn = stock.earnings_history
        except: hist_earn = None

        try: earn_dates = stock.earnings_dates
        except: earn_dates = None

        try: qfin = stock.quarterly_financials.T.sort_index()
        except: qfin = pd.DataFrame()

        try: qbs = stock.quarterly_balance_sheet.T.sort_index()
        except: qbs = pd.DataFrame()

        try: qcf = stock.quarterly_cashflow.T.sort_index()
        except: qcf = pd.DataFrame()

        f = stock.fast_info
        price = float(f.get("lastPrice") or f.get("regularMarketPrice") or 0)

    # ── EPS BEATS & MISSES ────────────────────────────────────
    st.subheader("🎯 EPS — Actual vs Estimate")
    try:
        if earn_dates is not None and not earn_dates.empty:
            ed = earn_dates.copy().dropna(subset=["EPS Estimate","Reported EPS"])
            ed = ed.sort_index()
            ed.index = ed.index.tz_localize(None) if ed.index.tzinfo else ed.index
            ed.index = ed.index.astype(str).str[:10]

            ed["Surprise %"] = ((ed["Reported EPS"] - ed["EPS Estimate"]) / ed["EPS Estimate"].abs() * 100).round(1)
            ed["Beat"] = ed["Reported EPS"] >= ed["EPS Estimate"]

            bar_colors = ["#26a69a" if b else "#ef5350" for b in ed["Beat"]]

            fig1 = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                 row_heights=[0.6,0.4], vertical_spacing=0.08,
                                 subplot_titles=["EPS Actual vs Estimate","Surprise %"])

            fig1.add_trace(go.Bar(
                x=ed.index, y=ed["EPS Estimate"],
                name="Estimate", marker_color="#888", opacity=0.6
            ), row=1, col=1)

            fig1.add_trace(go.Scatter(
                x=ed.index, y=ed["Reported EPS"],
                name="Actual EPS", mode="lines+markers",
                line=dict(color="#FFA500", width=3),
                marker=dict(size=10, color=bar_colors,
                            line=dict(color="white", width=2))
            ), row=1, col=1)

            fig1.add_trace(go.Bar(
                x=ed.index, y=ed["Surprise %"],
                name="Surprise %",
                marker_color=bar_colors, opacity=0.9
            ), row=2, col=1)

            fig1.add_hline(y=0, line_dash="dash", line_color="#888", row=2, col=1)

            fig1.update_layout(height=550,
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font_color="white", legend=dict(orientation="h", y=1.05))
            fig1.update_xaxes(gridcolor="#1e1e1e")
            fig1.update_yaxes(gridcolor="#1e1e1e")
            st.plotly_chart(fig1, use_container_width=True)

            # ── BEAT/MISS SUMMARY ─────────────────────────────
            beats = ed["Beat"].sum()
            misses = (~ed["Beat"]).sum()
            avg_surprise = ed["Surprise %"].mean()

            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Quarters Tracked", len(ed))
            c2.metric("Beats", int(beats), delta=f"{round(beats/len(ed)*100)}% of quarters")
            c3.metric("Misses", int(misses))
            c4.metric("Avg Surprise", f"{round(avg_surprise,1)}%",
                      delta="beats estimates on avg" if avg_surprise > 0 else "misses estimates on avg")

        else:
            st.info("No earnings estimate data available for this ticker.")
    except Exception as e:
        st.warning(f"EPS chart error: {e}")

    st.divider()

    # ── BEHAVIORAL FLAGS ──────────────────────────────────────
    st.subheader("🧠 Behavioral Flags")
    try:
        if earn_dates is not None and not earn_dates.empty:
            ed2 = earn_dates.copy().dropna(subset=["EPS Estimate","Reported EPS"])
            ed2 = ed2.sort_index()
            ed2.index = ed2.index.tz_localize(None) if ed2.index.tzinfo else ed2.index
            ed2["Surprise %"] = ((ed2["Reported EPS"] - ed2["EPS Estimate"]) / ed2["EPS Estimate"].abs() * 100).round(1)

            flags = []
            for date, row in ed2.iterrows():
                s = row["Surprise %"]
                if s > 15:
                    flags.append({"Date": str(date)[:10], "Flag": "🟢 Large Beat",
                        "Detail": f"+{s}% surprise — market may have already priced this in (buy the rumor, sell the news)"})
                elif s < -15:
                    flags.append({"Date": str(date)[:10], "Flag": "🔴 Large Miss",
                        "Detail": f"{s}% surprise — watch for oversold bounce if fundamentals intact"})
                elif 5 < s <= 15:
                    flags.append({"Date": str(date)[:10], "Flag": "🟡 Moderate Beat",
                        "Detail": f"+{s}% surprise — healthy beat, watch guidance for follow-through"})
                elif -15 <= s < -5:
                    flags.append({"Date": str(date)[:10], "Flag": "🟠 Moderate Miss",
                        "Detail": f"{s}% surprise — management guidance will be key"})

            if flags:
                for flag in reversed(flags[-6:]):
                    with st.expander(f"{flag['Date']} — {flag['Flag']}"):
                        st.write(flag["Detail"])
            else:
                st.info("No significant behavioral flags detected.")
        else:
            st.info("Not enough data for behavioral analysis.")
    except Exception as e:
        st.warning(f"Behavioral flags error: {e}")

    st.divider()

    # ── QUARTERLY REVENUE TREND ───────────────────────────────
    st.subheader("📊 Quarterly Revenue & Net Income")
    if not qfin.empty:
        try:
            q = qfin.copy()
            q.index = q.index.astype(str).str[:10]
            fig2 = make_subplots(specs=[[{"secondary_y":True}]])
            if "Total Revenue" in q.columns:
                fig2.add_trace(go.Bar(x=q.index, y=q["Total Revenue"],
                    name="Revenue", marker_color="#4A90D9", opacity=0.9),
                    secondary_y=False)
            if "Gross Profit" in q.columns:
                fig2.add_trace(go.Bar(x=q.index, y=q["Gross Profit"],
                    name="Gross Profit", marker_color="#9B59B6", opacity=0.9),
                    secondary_y=False)
            if "Net Income" in q.columns:
                fig2.add_trace(go.Scatter(x=q.index, y=q["Net Income"],
                    name="Net Income", line=dict(color="#27AE60",width=3),
                    mode="lines+markers", marker=dict(size=9)),
                    secondary_y=True)
            fig2.update_layout(height=400, barmode="group",
                paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                font_color="white", legend=dict(orientation="h",y=1.1))
            fig2.update_xaxes(gridcolor="#1e1e1e")
            fig2.update_yaxes(gridcolor="#1e1e1e")
            st.plotly_chart(fig2, use_container_width=True)
        except Exception as e:
            st.warning(f"Quarterly revenue: {e}")

    st.divider()

    # ── QUARTERLY MARGINS ─────────────────────────────────────
    st.subheader("📉 Quarterly Margin Trends")
    if not qfin.empty and "Total Revenue" in qfin.columns:
        try:
            q2 = qfin.copy()
            q2.index = q2.index.astype(str).str[:10]
            m = pd.DataFrame(index=q2.index)
            if "Gross Profit"     in q2.columns: m["Gross Margin %"] = (q2["Gross Profit"]    /q2["Total Revenue"]*100).round(1)
            if "Net Income"       in q2.columns: m["Net Margin %"]   = (q2["Net Income"]      /q2["Total Revenue"]*100).round(1)
            if "Operating Income" in q2.columns: m["Op Margin %"]    = (q2["Operating Income"]/q2["Total Revenue"]*100).round(1)
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
            st.warning(f"Quarterly margins: {e}")

    st.divider()

    # ── QUARTERLY EPS TREND ───────────────────────────────────
    st.subheader("💰 Quarterly EPS Trend")
    if not qfin.empty:
        try:
            q3 = qfin.copy()
            q3.index = q3.index.astype(str).str[:10]
            f3 = stock.fast_info
            shares = float(f3.get("shares") or f3.get("impliedShares") or 0)
            if "Net Income" in q3.columns and shares:
                q3["EPS"] = (q3["Net Income"] / shares).round(2)
                colors_eps = ["#26a69a" if v >= 0 else "#ef5350" for v in q3["EPS"]]
                fig4 = go.Figure()
                fig4.add_trace(go.Bar(x=q3.index, y=q3["EPS"],
                    name="EPS", marker_color=colors_eps))
                fig4.add_hline(y=0, line_dash="dash", line_color="#888")
                fig4.update_layout(height=320,
                    paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
                    font_color="white", yaxis_title="EPS ($)")
                fig4.update_xaxes(gridcolor="#1e1e1e")
                fig4.update_yaxes(gridcolor="#1e1e1e")
                st.plotly_chart(fig4, use_container_width=True)
        except Exception as e:
            st.warning(f"EPS trend: {e}")
