import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from fpdf import FPDF
import pandas as pd
import tempfile
import os
from datetime import datetime

def simple_sentiment(text):
    positive = ["beat","strong","growth","record","surge","gain","profit","up","rise",
                "raised","upgrade","outperform","bullish","exceed","positive","boost",
                "soar","rally","jump","expand","buy","opportunity","innovative","leading"]
    negative = ["miss","weak","decline","fall","drop","loss","down","cut","lower","risk",
                "downgrade","underperform","bearish","disappoint","negative","concern",
                "slump","crash","sell","lawsuit","investigation","warning","slowdown"]
    text_lower = text.lower()
    pos = sum(1 for w in positive if w in text_lower)
    neg = sum(1 for w in negative if w in text_lower)
    total = pos + neg
    if total == 0: return 0.0, "Neutral"
    raw = (pos - neg) / total
    weight = min(total, 5) / 5
    score = round(raw * weight, 3)
    if score > 0.15:  return score, "Positive"
    if score < -0.15: return score, "Negative"
    return score, "Neutral"

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

def clean(text):
    """Remove characters unsupported by fpdf2 Helvetica"""
    replacements = {
        "\u2014": "-", "\u2013": "-", "\u2012": "-",
        "\u2018": "'", "\u2019": "'",
        "\u201c": '"', "\u201d": '"',
        "\u2026": "...", "\u00e9": "e",
        "\u00e0": "a", "\u00e8": "e",
        "\u2022": "*", "\u00b7": "*",
        "\u00a0": " ", "\u00b0": " deg",
        "\u25b2": "^", "\u25bc": "v",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", errors="replace").decode("latin-1")

class PDF(FPDF):
    def __init__(self, ticker):
        super().__init__()
        self.ticker = ticker
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        self.set_fill_color(26, 26, 46)
        self.rect(0, 0, 210, 22, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 13)
        self.set_xy(10, 6)
        self.cell(0, 10, clean(f"Stock Analyzer | {self.ticker} Report"), ln=False)
        self.set_font("Helvetica", "", 9)
        self.set_xy(0, 6)
        self.cell(200, 10, datetime.now().strftime("%B %d, %Y"), align="R")
        self.set_text_color(0, 0, 0)
        self.ln(18)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()} | Stock Analyzer | For informational purposes only", align="C")
        self.set_text_color(0, 0, 0)

    def section_title(self, title):
        self.set_fill_color(240, 240, 245)
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(26, 26, 46)
        self.cell(0, 9, clean(title), ln=True, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def metric_row(self, items):
        col_w = 190 / len(items)
        x_start = self.get_x()
        y_start = self.get_y()
        for label, value in items:
            self.set_xy(x_start, y_start)
            self.set_fill_color(248, 248, 252)
            self.rect(x_start, y_start, col_w - 2, 16, 'F')
            self.set_font("Helvetica", "", 7.5)
            self.set_text_color(100, 100, 120)
            self.set_xy(x_start + 2, y_start + 1)
            self.cell(col_w - 4, 5, clean(str(label)), ln=True)
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(20, 20, 40)
            self.set_xy(x_start + 2, y_start + 7)
            self.cell(col_w - 4, 6, clean(str(value)), ln=True)
            x_start += col_w
        self.set_text_color(0, 0, 0)
        self.set_xy(self.l_margin, y_start + 18)

    def add_image_from_fig(self, fig, w=190, h=80):
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                fig.write_image(tmp.name, width=950, height=450, scale=1.5)
                self.image(tmp.name, x=10, w=w, h=h)
                os.unlink(tmp.name)
            self.ln(3)
        except Exception as e:
            self.set_font("Helvetica", "I", 9)
            self.set_text_color(150, 150, 150)
            self.cell(0, 8, clean(f"[Chart unavailable: {e}]"), ln=True)
            self.set_text_color(0, 0, 0)


def show(ticker):
    st.header(f"PDF Export | {ticker}")
    st.markdown("Generate a full analyst-style PDF report with fundamentals, earnings, and sentiment.")

    analyst_name = st.text_input("Your name (appears on report)", value="Stock Analyzer")

    col1, col2 = st.columns(2)
    with col1:
        include_fundamentals = st.checkbox("Include Fundamentals",     value=True)
        include_earnings     = st.checkbox("Include Earnings Analysis", value=True)
    with col2:
        include_sentiment    = st.checkbox("Include News Sentiment",    value=True)
        include_charts       = st.checkbox("Include Charts",            value=True)

    if st.button("Generate PDF Report", type="primary"):
        with st.spinner("Building your report... this takes about 30 seconds"):
            try:
                # ── FETCH DATA ────────────────────────────────
                stock  = yf.Ticker(ticker)
                f      = stock.fast_info
                price  = float(f.get("lastPrice") or f.get("regularMarketPrice") or 0)
                prev   = float(f.get("previousClose") or price)
                mcap   = float(f.get("marketCap") or 0)
                shares = float(f.get("shares") or f.get("impliedShares") or 0)

                try: fin  = stock.financials.T.sort_index()
                except: fin = pd.DataFrame()
                try: bs   = stock.balance_sheet.T.sort_index()
                except: bs = pd.DataFrame()
                try: cf   = stock.cashflow.T.sort_index()
                except: cf = pd.DataFrame()
                try:
                    h52  = stock.history(period="1y")
                    w52h = float(h52["High"].max()) if not h52.empty else 0
                    w52l = float(h52["Low"].min())  if not h52.empty else 0
                except: w52h, w52l = 0, 0
                try: news_raw    = stock.news or []
                except: news_raw = []
                try: earn_dates  = stock.earnings_dates
                except: earn_dates = None

                # ── METRICS ───────────────────────────────────
                rev     = safe(fin, "Total Revenue")
                gross_p = safe(fin, "Gross Profit")
                net_inc = safe(fin, "Net Income")
                op_inc  = safe(fin, "Operating Income")
                ebitda  = safe(fin, "EBITDA") or safe(fin, "Normalized EBITDA")
                debt    = safe(bs,  "Total Debt")
                cash    = safe(bs,  "Cash And Cash Equivalents") or safe(bs, "Cash Cash Equivalents And Short Term Investments")
                equity  = safe(bs,  "Stockholders Equity") or safe(bs, "Common Stock Equity")
                assets  = safe(bs,  "Total Assets")
                op_cf   = safe(cf,  "Operating Cash Flow")
                fcf     = safe(cf,  "Free Cash Flow")

                chg      = round(price - prev, 2)
                chgp     = round((chg/prev)*100, 2) if prev else 0
                net_debt = (debt - cash)          if debt and cash else None
                gross_m  = round(gross_p/rev*100,1) if gross_p and rev else None
                net_m    = round(net_inc/rev*100,1)  if net_inc and rev else None
                eps      = net_inc/shares             if net_inc and shares else None
                pe       = price/eps                  if eps and eps > 0 else None
                pb       = mcap/equity                if equity and equity > 0 else None
                roe      = net_inc/equity*100         if net_inc and equity and equity > 0 else None
                de       = debt/equity                if debt and equity and equity > 0 else None

                # ── SENTIMENT ─────────────────────────────────
                articles = []
                for item in news_raw:
                    try:
                        content = item.get("content", {})
                        title   = content.get("title","") if content else item.get("title","")
                        summary = content.get("summary","") if content else ""
                        if not title: continue
                        score, label = simple_sentiment(title + " " + summary)
                        articles.append({"title":title,"score":score,"label":label})
                    except: continue

                pos_c = sum(1 for a in articles if a["label"]=="Positive")
                neg_c = sum(1 for a in articles if a["label"]=="Negative")
                neu_c = sum(1 for a in articles if a["label"]=="Neutral")
                avg_s = round(sum(a["score"] for a in articles)/len(articles),3) if articles else 0
                sent_label = "Bullish" if avg_s>0.1 else "Bearish" if avg_s<-0.1 else "Neutral"

                # ── BUILD PDF ─────────────────────────────────
                pdf = PDF(ticker)
                pdf.add_page()

                # Title block
                pdf.set_font("Helvetica","B",22)
                pdf.set_text_color(26,26,46)
                pdf.cell(0,12, clean(f"{ticker} | Analyst Report"), ln=True)
                pdf.set_font("Helvetica","",11)
                pdf.set_text_color(80,80,80)
                pdf.cell(0,7, clean(f"Prepared by: {analyst_name}"), ln=True)
                pdf.cell(0,7, clean(f"Generated: {datetime.now().strftime('%B %d, %Y at %H:%M')}"), ln=True)
                pdf.ln(4)

                # Price banner
                direction = "+" if chg >= 0 else "-"
                pdf.set_fill_color(26,26,46)
                pdf.rect(10, pdf.get_y(), 190, 20, 'F')
                pdf.set_text_color(255,255,255)
                pdf.set_font("Helvetica","B",16)
                pdf.set_xy(14, pdf.get_y()+3)
                pdf.cell(80,8, clean(f"${round(price,2)}"), ln=False)
                pdf.set_font("Helvetica","",11)
                pdf.cell(100,8, clean(f"{direction}${abs(chg)} ({chgp}%) today"), ln=True)
                pdf.set_text_color(0,0,0)
                pdf.ln(10)

                # ── FUNDAMENTALS ──────────────────────────────
                if include_fundamentals:
                    pdf.section_title("FUNDAMENTALS")
                    pdf.metric_row([
                        ("Market Cap",    fmt(mcap)),
                        ("Revenue TTM",   fmt(rev)),
                        ("Gross Profit",  fmt(gross_p)),
                        ("Net Income",    fmt(net_inc)),
                    ])
                    pdf.metric_row([
                        ("EPS",           f"${round(eps,2)}" if eps else "N/A"),
                        ("P/E Ratio",     str(round(pe,1))   if pe  else "N/A"),
                        ("P/B Ratio",     str(round(pb,2))   if pb  else "N/A"),
                        ("Gross Margin",  f"{gross_m}%"      if gross_m else "N/A"),
                    ])
                    pdf.metric_row([
                        ("Net Margin",    f"{net_m}%"        if net_m else "N/A"),
                        ("ROE",           f"{round(roe,1)}%" if roe   else "N/A"),
                        ("Debt/Equity",   str(round(de,2))   if de   else "N/A"),
                        ("Free Cash Flow",fmt(fcf)),
                    ])
                    pdf.metric_row([
                        ("Total Debt",    fmt(debt)),
                        ("Cash",          fmt(cash)),
                        ("Net Debt",      fmt(net_debt)),
                        ("EBITDA",        fmt(ebitda)),
                    ])
                    pdf.metric_row([
                        ("52W High",      f"${round(w52h,2)}" if w52h else "N/A"),
                        ("52W Low",       f"${round(w52l,2)}" if w52l else "N/A"),
                        ("Op Cash Flow",  fmt(op_cf)),
                        ("Total Assets",  fmt(assets)),
                    ])
                    pdf.ln(4)

                    if include_charts and not fin.empty:
                        try:
                            f2 = fin.copy()
                            f2.index = f2.index.astype(str).str[:10]
                            fig_rev = go.Figure()
                            for cn, col in [("Total Revenue","#4A90D9"),("Gross Profit","#9B59B6"),("Net Income","#27AE60")]:
                                if cn in f2.columns:
                                    fig_rev.add_trace(go.Bar(x=f2.index, y=f2[cn], name=cn, marker_color=col))
                            fig_rev.update_layout(barmode="group", height=400,
                                paper_bgcolor="white", plot_bgcolor="#f8f8f8",
                                title="Revenue, Gross Profit & Net Income",
                                legend=dict(orientation="h"))
                            pdf.add_image_from_fig(fig_rev)
                        except: pass

                # ── EARNINGS ──────────────────────────────────
                if include_earnings:
                    pdf.add_page()
                    pdf.section_title("EARNINGS ANALYSIS")
                    if earn_dates is not None and not earn_dates.empty:
                        try:
                            ed = earn_dates.copy().dropna(subset=["EPS Estimate","Reported EPS"])
                            ed = ed.sort_index()
                            ed.index = ed.index.tz_localize(None) if ed.index.tzinfo else ed.index
                            ed["Surprise %"] = ((ed["Reported EPS"]-ed["EPS Estimate"])/ed["EPS Estimate"].abs()*100).round(1)
                            beats   = int((ed["Reported EPS"]>=ed["EPS Estimate"]).sum())
                            misses  = int((ed["Reported EPS"]< ed["EPS Estimate"]).sum())
                            avg_sur = round(ed["Surprise %"].mean(),1)
                            pdf.metric_row([
                                ("Quarters Tracked", str(len(ed))),
                                ("Beats",            str(beats)),
                                ("Misses",           str(misses)),
                                ("Avg EPS Surprise", f"{avg_sur}%"),
                            ])
                            pdf.ln(4)
                            if include_charts:
                                ed2 = ed.copy()
                                ed2.index = ed2.index.astype(str).str[:10]
                                bar_colors = ["#26a69a" if b else "#ef5350"
                                              for b in (ed2["Reported EPS"]>=ed2["EPS Estimate"])]
                                fig_eps = make_subplots(rows=2, cols=1, shared_xaxes=True,
                                    row_heights=[0.6,0.4], vertical_spacing=0.1)
                                fig_eps.add_trace(go.Bar(x=ed2.index, y=ed2["EPS Estimate"],
                                    name="Estimate", marker_color="#888", opacity=0.6), row=1, col=1)
                                fig_eps.add_trace(go.Scatter(x=ed2.index, y=ed2["Reported EPS"],
                                    name="Actual", mode="lines+markers",
                                    line=dict(color="#FFA500",width=2),
                                    marker=dict(size=8,color=bar_colors)), row=1, col=1)
                                fig_eps.add_trace(go.Bar(x=ed2.index, y=ed2["Surprise %"],
                                    name="Surprise %", marker_color=bar_colors), row=2, col=1)
                                fig_eps.update_layout(height=500,
                                    paper_bgcolor="white", plot_bgcolor="#f8f8f8",
                                    title="EPS Actual vs Estimate",
                                    legend=dict(orientation="h"))
                                pdf.add_image_from_fig(fig_eps, h=90)
                        except: pass
                    else:
                        pdf.set_font("Helvetica","I",10)
                        pdf.cell(0,8,"No earnings estimate data available.",ln=True)

                # ── SENTIMENT ─────────────────────────────────
                if include_sentiment and articles:
                    pdf.add_page()
                    pdf.section_title("NEWS SENTIMENT ANALYSIS")
                    pdf.metric_row([
                        ("Overall Sentiment", sent_label),
                        ("Avg Score",         f"{avg_s:+.3f}"),
                        ("Positive",          str(pos_c)),
                        ("Negative",          str(neg_c)),
                    ])
                    pdf.ln(4)
                    pdf.set_font("Helvetica","B",10)
                    pdf.set_text_color(26,26,46)
                    pdf.cell(0,7,"Behavioral Flag:",ln=True)
                    pdf.set_font("Helvetica","",9)
                    pdf.set_text_color(60,60,60)
                    if avg_s > 0.3:   flag = "Extreme Optimism - sentiment very bullish. Good news may be priced in."
                    elif avg_s > 0.1: flag = "Moderately Bullish - positive sentiment with room to run."
                    elif avg_s < -0.3:flag = "Extreme Pessimism - contrarian opportunity may exist if fundamentals intact."
                    elif avg_s < -0.1:flag = "Moderately Bearish - negative sentiment building."
                    else:             flag = "Neutral Sentiment - no strong directional bias in recent news."
                    pdf.multi_cell(0, 6, clean(flag))
                    pdf.ln(3)
                    pdf.set_text_color(0,0,0)

                    if include_charts:
                        try:
                            fig_pie = go.Figure(go.Pie(
                                labels=["Positive","Neutral","Negative"],
                                values=[pos_c, neu_c, neg_c],
                                hole=0.5,
                                marker_colors=["#26a69a","#888","#ef5350"]
                            ))
                            fig_pie.update_layout(height=400, paper_bgcolor="white",
                                title="Sentiment Breakdown")
                            pdf.add_image_from_fig(fig_pie, h=70)
                        except: pass

                    pdf.ln(2)
                    pdf.set_font("Helvetica","B",10)
                    pdf.set_text_color(26,26,46)
                    pdf.cell(0,7,"Recent Headlines:",ln=True)
                    pdf.set_text_color(0,0,0)
                    for a in articles[:12]:
                        tag   = "+" if a["label"]=="Positive" else "-" if a["label"]=="Negative" else "o"
                        lc    = (39,174,96) if a["label"]=="Positive" else (231,76,60) if a["label"]=="Negative" else (100,100,100)
                        pdf.set_font("Helvetica","",8)
                        pdf.set_text_color(*lc)
                        pdf.cell(8,6,f"[{tag}]",ln=False)
                        pdf.set_text_color(40,40,40)
                        t = clean(a["title"])
                        t = t[:90]+"..." if len(t)>90 else t
                        pdf.multi_cell(0,6,t)

                # ── DISCLAIMER ────────────────────────────────
                pdf.add_page()
                pdf.section_title("DISCLAIMER")
                pdf.set_font("Helvetica","",9)
                pdf.set_text_color(100,100,100)
                pdf.multi_cell(0,6, clean(
                    "This report is generated automatically by Stock Analyzer and is intended for "
                    "informational and educational purposes only. It does not constitute financial advice, "
                    "investment recommendations, or an offer to buy or sell any security. All data is "
                    "sourced from publicly available information and may not be accurate or up to date. "
                    "Past performance is not indicative of future results. Always consult a qualified "
                    "financial advisor before making investment decisions."))

                # ── SAVE & DOWNLOAD ───────────────────────────
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    pdf.output(tmp.name)
                    with open(tmp.name,"rb") as fout:
                        pdf_bytes = fout.read()
                    os.unlink(tmp.name)

                st.success("Report generated successfully!")
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_bytes,
                    file_name=f"{ticker}_report_{datetime.now().strftime('%Y%m%d')}.pdf",
                    mime="application/pdf",
                    type="primary"
                )

            except Exception as e:
                st.error(f"Error generating PDF: {e}")
                st.info("Try unchecking Include Charts if the error persists.")
