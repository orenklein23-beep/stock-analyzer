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
    if not text: return ""
    text = str(text)
    replacements = {
        "\u2014":"-", "\u2013":"-", "\u2012":"-",
        "\u2018":"'", "\u2019":"'",
        "\u201c":'"', "\u201d":'"',
        "\u2026":"...", "\u2022":"*",
        "\u00a0":" ", "\u25b2":"^", "\u25bc":"v",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode("latin-1", errors="replace").decode("latin-1")

class PDF(FPDF):
    def __init__(self, ticker):
        super().__init__()
        self.ticker = ticker
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(10, 10, 10)

    def header(self):
        self.set_fill_color(26, 26, 46)
        self.rect(0, 0, 210, 20, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 12)
        self.set_xy(10, 5)
        self.cell(130, 10, clean(f"Stock Analyzer | {self.ticker} Analyst Report"), ln=False)
        self.set_font("Helvetica", "", 9)
        self.set_xy(140, 5)
        self.cell(60, 10, datetime.now().strftime("%B %d, %Y"), align="R")
        self.set_text_color(0, 0, 0)
        self.ln(22)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()} | Stock Analyzer | For informational purposes only", align="C")
        self.set_text_color(0, 0, 0)

    def section_title(self, title):
        self.set_fill_color(26, 26, 46)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, clean(f"  {title}"), ln=True, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(3)

    def two_col_metrics(self, items):
        """Render metrics in a simple 2-column table — very safe layout"""
        self.set_font("Helvetica", "", 9)
        col_w = 95
        for i in range(0, len(items), 2):
            y = self.get_y()
            # Left cell
            label1, val1 = items[i]
            self.set_fill_color(245, 245, 250)
            self.set_xy(10, y)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(100, 100, 120)
            self.cell(col_w, 5, clean(str(label1)), ln=False, fill=True)
            self.set_xy(10, y + 5)
            self.set_font("Helvetica", "B", 10)
            self.set_text_color(20, 20, 40)
            self.cell(col_w, 6, clean(str(val1)), ln=False, fill=True)
            # Right cell
            if i + 1 < len(items):
                label2, val2 = items[i + 1]
                self.set_xy(10 + col_w + 2, y)
                self.set_font("Helvetica", "", 8)
                self.set_text_color(100, 100, 120)
                self.cell(col_w, 5, clean(str(label2)), ln=False, fill=True)
                self.set_xy(10 + col_w + 2, y + 5)
                self.set_font("Helvetica", "B", 10)
                self.set_text_color(20, 20, 40)
                self.cell(col_w, 6, clean(str(val2)), ln=False, fill=True)
            self.set_text_color(0, 0, 0)
            self.set_xy(10, y + 12)
        self.ln(3)

    def add_chart(self, fig, h=75):
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                fig.write_image(tmp.name, width=900, height=400, scale=2)
                self.image(tmp.name, x=10, w=190, h=h)
                os.unlink(tmp.name)
            self.ln(4)
        except Exception as e:
            self.set_font("Helvetica", "I", 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 6, clean(f"[Chart unavailable: {str(e)[:60]}]"), ln=True)
            self.set_text_color(0, 0, 0)


def show(ticker):
    st.header(f"PDF Export | {ticker}")
    st.markdown("Generate a full analyst-style PDF report.")

    analyst_name = st.text_input("Your name (appears on report)", value="Stock Analyzer")

    col1, col2 = st.columns(2)
    with col1:
        inc_fund = st.checkbox("Include Fundamentals",     value=True)
        inc_earn = st.checkbox("Include Earnings Analysis", value=True)
    with col2:
        inc_sent = st.checkbox("Include News Sentiment",    value=True)
        inc_charts = st.checkbox("Include Charts",          value=True)

    if st.button("Generate PDF Report", type="primary"):
        with st.spinner("Building report... ~30 seconds"):
            try:
                # ── FETCH ─────────────────────────────────────
                stock  = yf.Ticker(ticker)
                fi     = stock.fast_info
                price  = float(fi.get("lastPrice") or fi.get("regularMarketPrice") or 0)
                prev   = float(fi.get("previousClose") or price)
                mcap   = float(fi.get("marketCap") or 0)
                shares = float(fi.get("shares") or fi.get("impliedShares") or 0)

                try: fin = stock.financials.T.sort_index()
                except: fin = pd.DataFrame()
                try: bs = stock.balance_sheet.T.sort_index()
                except: bs = pd.DataFrame()
                try: cf = stock.cashflow.T.sort_index()
                except: cf = pd.DataFrame()
                try:
                    h52  = stock.history(period="1y")
                    w52h = float(h52["High"].max()) if not h52.empty else 0
                    w52l = float(h52["Low"].min())  if not h52.empty else 0
                except: w52h, w52l = 0, 0
                try: news_raw = stock.news or []
                except: news_raw = []
                try: earn_dates = stock.earnings_dates
                except: earn_dates = None

                # ── COMPUTE ───────────────────────────────────
                rev     = safe(fin, "Total Revenue")
                gross_p = safe(fin, "Gross Profit")
                net_inc = safe(fin, "Net Income")
                ebitda  = safe(fin, "EBITDA") or safe(fin, "Normalized EBITDA")
                debt    = safe(bs,  "Total Debt")
                cash    = safe(bs,  "Cash And Cash Equivalents") or safe(bs, "Cash Cash Equivalents And Short Term Investments")
                equity  = safe(bs,  "Stockholders Equity") or safe(bs, "Common Stock Equity")
                assets  = safe(bs,  "Total Assets")
                op_cf   = safe(cf,  "Operating Cash Flow")
                fcf     = safe(cf,  "Free Cash Flow")

                chg     = round(price - prev, 2)
                chgp    = round((chg/prev)*100, 2) if prev else 0
                net_debt= (debt-cash)          if debt and cash else None
                gross_m = round(gross_p/rev*100,1) if gross_p and rev else None
                net_m   = round(net_inc/rev*100,1)  if net_inc and rev else None
                eps     = net_inc/shares             if net_inc and shares else None
                pe      = price/eps                  if eps and eps > 0 else None
                pb      = mcap/equity                if equity and equity > 0 else None
                roe     = net_inc/equity*100         if net_inc and equity and equity > 0 else None
                de      = debt/equity                if debt and equity and equity > 0 else None

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

                # Title
                pdf.set_font("Helvetica","B",20)
                pdf.set_text_color(26,26,46)
                pdf.cell(0,10, clean(f"{ticker} Analyst Report"), ln=True)
                pdf.set_font("Helvetica","",10)
                pdf.set_text_color(80,80,80)
                pdf.cell(0,6, clean(f"Prepared by: {analyst_name}"), ln=True)
                pdf.cell(0,6, clean(f"Date: {datetime.now().strftime('%B %d, %Y')}"), ln=True)
                pdf.ln(4)

                # Price box
                direction = "+" if chg >= 0 else ""
                pdf.set_fill_color(26,26,46)
                pdf.rect(10, pdf.get_y(), 190, 18, 'F')
                pdf.set_text_color(255,255,255)
                pdf.set_font("Helvetica","B",15)
                pdf.set_xy(14, pdf.get_y()+3)
                pdf.cell(90, 8, clean(f"${round(price,2)}"), ln=False)
                pdf.set_font("Helvetica","",10)
                pdf.cell(90, 8, clean(f"{direction}{chg} ({chgp}%) today"), ln=True)
                pdf.set_text_color(0,0,0)
                pdf.ln(8)

                # ── FUNDAMENTALS ──────────────────────────────
                if inc_fund:
                    pdf.section_title("FUNDAMENTALS")
                    pdf.two_col_metrics([
                        ("Market Cap",    fmt(mcap)),
                        ("Revenue TTM",   fmt(rev)),
                        ("Gross Profit",  fmt(gross_p)),
                        ("Net Income",    fmt(net_inc)),
                        ("EPS",           f"${round(eps,2)}" if eps else "N/A"),
                        ("P/E Ratio",     str(round(pe,1)) if pe else "N/A"),
                        ("P/B Ratio",     str(round(pb,2)) if pb else "N/A"),
                        ("Gross Margin",  f"{gross_m}%" if gross_m else "N/A"),
                        ("Net Margin",    f"{net_m}%" if net_m else "N/A"),
                        ("ROE",           f"{round(roe,1)}%" if roe else "N/A"),
                        ("Debt/Equity",   str(round(de,2)) if de else "N/A"),
                        ("Free CF",       fmt(fcf)),
                        ("Total Debt",    fmt(debt)),
                        ("Cash",          fmt(cash)),
                        ("Net Debt",      fmt(net_debt)),
                        ("EBITDA",        fmt(ebitda)),
                        ("52W High",      f"${round(w52h,2)}" if w52h else "N/A"),
                        ("52W Low",       f"${round(w52l,2)}" if w52l else "N/A"),
                        ("Op Cash Flow",  fmt(op_cf)),
                        ("Total Assets",  fmt(assets)),
                    ])

                    if inc_charts and not fin.empty:
                        try:
                            f2 = fin.copy()
                            f2.index = f2.index.astype(str).str[:10]
                            fig_rev = go.Figure()
                            for cn, col in [
                                ("Total Revenue","#4A90D9"),
                                ("Gross Profit","#9B59B6"),
                                ("Net Income","#27AE60")
                            ]:
                                if cn in f2.columns:
                                    fig_rev.add_trace(go.Bar(
                                        x=f2.index, y=f2[cn],
                                        name=cn, marker_color=col))
                            fig_rev.update_layout(
                                barmode="group", height=400,
                                paper_bgcolor="white",
                                plot_bgcolor="#f8f8f8",
                                title="Revenue, Gross Profit & Net Income",
                                legend=dict(orientation="h"))
                            pdf.add_chart(fig_rev)
                        except: pass

                # ── EARNINGS ──────────────────────────────────
                if inc_earn:
                    pdf.add_page()
                    pdf.section_title("EARNINGS ANALYSIS")
                    if earn_dates is not None and not earn_dates.empty:
                        try:
                            ed = earn_dates.copy().dropna(
                                subset=["EPS Estimate","Reported EPS"])
                            ed = ed.sort_index()
                            ed.index = ed.index.tz_localize(None) if ed.index.tzinfo else ed.index
                            ed["Surp"] = ((ed["Reported EPS"]-ed["EPS Estimate"])/
                                          ed["EPS Estimate"].abs()*100).round(1)
                            beats  = int((ed["Reported EPS"]>=ed["EPS Estimate"]).sum())
                            misses = len(ed) - beats
                            avg_su = round(ed["Surp"].mean(),1)

                            pdf.two_col_metrics([
                                ("Quarters Tracked", str(len(ed))),
                                ("EPS Beats",        str(beats)),
                                ("EPS Misses",       str(misses)),
                                ("Avg Surprise",     f"{avg_su}%"),
                            ])

                            if inc_charts:
                                ed2 = ed.copy()
                                ed2.index = ed2.index.astype(str).str[:10]
                                bc = ["#26a69a" if b else "#ef5350"
                                      for b in (ed2["Reported EPS"]>=ed2["EPS Estimate"])]
                                fig_e = make_subplots(rows=2, cols=1,
                                    shared_xaxes=True,
                                    row_heights=[0.6,0.4],
                                    vertical_spacing=0.1)
                                fig_e.add_trace(go.Bar(
                                    x=ed2.index, y=ed2["EPS Estimate"],
                                    name="Estimate",
                                    marker_color="#888", opacity=0.6), row=1, col=1)
                                fig_e.add_trace(go.Scatter(
                                    x=ed2.index, y=ed2["Reported EPS"],
                                    name="Actual",
                                    mode="lines+markers",
                                    line=dict(color="#FFA500",width=2),
                                    marker=dict(size=7,color=bc)), row=1, col=1)
                                fig_e.add_trace(go.Bar(
                                    x=ed2.index, y=ed2["Surp"],
                                    name="Surprise %",
                                    marker_color=bc), row=2, col=1)
                                fig_e.update_layout(height=480,
                                    paper_bgcolor="white",
                                    plot_bgcolor="#f8f8f8",
                                    title="EPS Actual vs Estimate",
                                    legend=dict(orientation="h"))
                                pdf.add_chart(fig_e, h=85)
                        except: pass
                    else:
                        pdf.set_font("Helvetica","I",9)
                        pdf.cell(0,7,"No earnings data available.",ln=True)

                # ── SENTIMENT ─────────────────────────────────
                if inc_sent and articles:
                    pdf.add_page()
                    pdf.section_title("NEWS SENTIMENT")
                    pdf.two_col_metrics([
                        ("Overall",       sent_label),
                        ("Avg Score",     f"{avg_s:+.3f}"),
                        ("Positive",      str(pos_c)),
                        ("Negative",      str(neg_c)),
                    ])

                    if avg_s > 0.3:
                        flag = "Extreme Optimism - very bullish. Good news may be priced in already."
                    elif avg_s > 0.1:
                        flag = "Moderately Bullish - positive sentiment with room to run."
                    elif avg_s < -0.3:
                        flag = "Extreme Pessimism - contrarian opportunity may exist if fundamentals intact."
                    elif avg_s < -0.1:
                        flag = "Moderately Bearish - negative sentiment building."
                    else:
                        flag = "Neutral - no strong directional bias in recent news."

                    pdf.set_font("Helvetica","B",9)
                    pdf.set_text_color(26,26,46)
                    pdf.cell(0,6,"Behavioral Flag:",ln=True)
                    pdf.set_font("Helvetica","",9)
                    pdf.set_text_color(60,60,60)
                    pdf.multi_cell(0,5,clean(flag))
                    pdf.set_text_color(0,0,0)
                    pdf.ln(3)

                    if inc_charts:
                        try:
                            fig_pie = go.Figure(go.Pie(
                                labels=["Positive","Neutral","Negative"],
                                values=[pos_c, neu_c, neg_c],
                                hole=0.5,
                                marker_colors=["#26a69a","#888","#ef5350"]
                            ))
                            fig_pie.update_layout(
                                height=380, paper_bgcolor="white",
                                title="Sentiment Breakdown")
                            pdf.add_chart(fig_pie, h=65)
                        except: pass

                    pdf.set_font("Helvetica","B",9)
                    pdf.set_text_color(26,26,46)
                    pdf.cell(0,6,"Recent Headlines:",ln=True)
                    for a in articles[:10]:
                        tag = "+" if a["label"]=="Positive" else \
                              "-" if a["label"]=="Negative" else "o"
                        lc  = (39,174,96)  if a["label"]=="Positive" else \
                              (231,76,60)  if a["label"]=="Negative" else \
                              (100,100,100)
                        pdf.set_font("Helvetica","",8)
                        pdf.set_text_color(*lc)
                        pdf.cell(8,5,f"[{tag}]",ln=False)
                        pdf.set_text_color(40,40,40)
                        t = clean(a["title"])
                        t = (t[:85]+"...") if len(t)>85 else t
                        pdf.multi_cell(0,5,t)
                    pdf.set_text_color(0,0,0)

                # ── DISCLAIMER ────────────────────────────────
                pdf.add_page()
                pdf.section_title("DISCLAIMER")
                pdf.set_font("Helvetica","",8)
                pdf.set_text_color(100,100,100)
                pdf.multi_cell(0,5,clean(
                    "This report is generated automatically by Stock Analyzer and is for "
                    "informational and educational purposes only. It does not constitute "
                    "financial advice or an offer to buy or sell any security. Data is sourced "
                    "from publicly available information and may not be accurate or current. "
                    "Past performance is not indicative of future results. Always consult a "
                    "qualified financial advisor before making investment decisions."))

                # ── DOWNLOAD ──────────────────────────────────
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    pdf.output(tmp.name)
                    with open(tmp.name,"rb") as fout:
                        pdf_bytes = fout.read()
                    os.unlink(tmp.name)

                st.success("Report generated!")
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
