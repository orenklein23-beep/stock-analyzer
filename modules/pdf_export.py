import streamlit as st
import yfinance as yf
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
    chars = {
        "\u2014":"-","\u2013":"-","\u2018":"'","\u2019":"'",
        "\u201c":'"',"\u201d":'"',"\u2026":"...","\u2022":"*",
        "\u00a0":" ","\u25b2":"^","\u25bc":"v",
    }
    for k,v in chars.items():
        text = text.replace(k,v)
    return text.encode("latin-1", errors="replace").decode("latin-1")

class PDF(FPDF):
    def __init__(self, ticker):
        super().__init__()
        self.ticker = ticker
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(15, 15, 15)

    def header(self):
        self.set_fill_color(26, 26, 46)
        self.rect(0, 0, 210, 18, 'F')
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 11)
        self.set_xy(15, 4)
        self.cell(120, 10, clean(f"Stock Analyzer | {self.ticker} Report"), ln=False)
        self.set_font("Helvetica", "", 9)
        self.set_xy(135, 4)
        self.cell(60, 10, datetime.now().strftime("%b %d, %Y"), align="R")
        self.set_text_color(0, 0, 0)
        self.ln(20)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f"Page {self.page_no()} | Stock Analyzer | For informational purposes only", align="C")
        self.set_text_color(0, 0, 0)

    def section_title(self, title):
        self.set_fill_color(26, 26, 46)
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(255, 255, 255)
        self.cell(0, 7, clean(f"  {title}"), ln=True, fill=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

    def metric_table(self, items):
        """Simple 2-column label: value table — bulletproof layout"""
        self.set_font("Helvetica", "", 9)
        usable = 180  # total usable width
        lw = 70       # label column width
        vw = 110      # value column width
        for label, value in items:
            y = self.get_y()
            self.set_xy(15, y)
            self.set_font("Helvetica", "", 8)
            self.set_text_color(80, 80, 100)
            self.cell(lw, 6, clean(str(label)), ln=False)
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(20, 20, 40)
            self.cell(vw, 6, clean(str(value)), ln=True)
        self.set_text_color(0, 0, 0)
        self.ln(2)

def show(ticker):
    st.header(f"PDF Export | {ticker}")
    st.markdown("Generate a full analyst-style PDF report.")

    analyst_name = st.text_input("Your name (appears on report)", value="Stock Analyzer")

    col1, col2 = st.columns(2)
    with col1:
        inc_fund = st.checkbox("Include Fundamentals",      value=True)
        inc_earn = st.checkbox("Include Earnings Analysis", value=True)
    with col2:
        inc_sent = st.checkbox("Include News Sentiment",    value=True)

    if st.button("Generate PDF Report", type="primary"):
        with st.spinner("Building report..."):
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
                net_debt= (debt-cash)              if debt and cash else None
                gross_m = round(gross_p/rev*100,1) if gross_p and rev else None
                net_m   = round(net_inc/rev*100,1) if net_inc and rev else None
                eps     = net_inc/shares            if net_inc and shares else None
                pe      = price/eps                 if eps and eps > 0 else None
                pb      = mcap/equity               if equity and equity > 0 else None
                roe     = net_inc/equity*100        if net_inc and equity and equity > 0 else None
                de      = debt/equity               if debt and equity and equity > 0 else None

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
                avg_s = round(sum(a["score"] for a in articles)/len(articles),3) if articles else 0
                sent_label = "Bullish" if avg_s>0.1 else "Bearish" if avg_s<-0.1 else "Neutral"

                # ── BUILD PDF ─────────────────────────────────
                pdf = PDF(ticker)
                pdf.add_page()

                # Title
                pdf.set_font("Helvetica","B",18)
                pdf.set_text_color(26,26,46)
                pdf.cell(0,10, clean(f"{ticker} Analyst Report"), ln=True)
                pdf.set_font("Helvetica","",9)
                pdf.set_text_color(80,80,80)
                pdf.cell(0,5, clean(f"Prepared by: {analyst_name}"), ln=True)
                pdf.cell(0,5, clean(f"Date: {datetime.now().strftime('%B %d, %Y')}"), ln=True)
                pdf.ln(4)

                # Price row
                direction = "+" if chg >= 0 else ""
                pdf.set_font("Helvetica","B",13)
                pdf.set_text_color(26,26,46)
                pdf.cell(0,8, clean(f"Current Price: ${round(price,2)}  |  {direction}{chg} ({chgp}%) today"), ln=True)
                pdf.set_text_color(0,0,0)
                pdf.ln(4)

                # ── FUNDAMENTALS ──────────────────────────────
                if inc_fund:
                    pdf.section_title("FUNDAMENTALS")
                    pdf.metric_table([
                        ("Market Cap",       fmt(mcap)),
                        ("Revenue (TTM)",    fmt(rev)),
                        ("Gross Profit",     fmt(gross_p)),
                        ("Net Income",       fmt(net_inc)),
                        ("EBITDA",           fmt(ebitda)),
                        ("EPS",              f"${round(eps,2)}" if eps else "N/A"),
                        ("P/E Ratio",        str(round(pe,1)) if pe else "N/A"),
                        ("P/B Ratio",        str(round(pb,2)) if pb else "N/A"),
                        ("Gross Margin",     f"{gross_m}%" if gross_m else "N/A"),
                        ("Net Margin",       f"{net_m}%" if net_m else "N/A"),
                        ("Return on Equity", f"{round(roe,1)}%" if roe else "N/A"),
                        ("Debt / Equity",    str(round(de,2)) if de else "N/A"),
                        ("Total Debt",       fmt(debt)),
                        ("Cash",             fmt(cash)),
                        ("Net Debt",         fmt(net_debt)),
                        ("Free Cash Flow",   fmt(fcf)),
                        ("Op Cash Flow",     fmt(op_cf)),
                        ("Total Assets",     fmt(assets)),
                        ("Equity",           fmt(equity)),
                        ("52-Week High",     f"${round(w52h,2)}" if w52h else "N/A"),
                        ("52-Week Low",      f"${round(w52l,2)}" if w52l else "N/A"),
                    ])

                # ── EARNINGS ──────────────────────────────────
                if inc_earn:
                    pdf.section_title("EARNINGS ANALYSIS")
                    if earn_dates is not None and not earn_dates.empty:
                        try:
                            ed = earn_dates.copy().dropna(subset=["EPS Estimate","Reported EPS"])
                            ed = ed.sort_index()
                            ed.index = ed.index.tz_localize(None) if ed.index.tzinfo else ed.index
                            ed["Surp"] = ((ed["Reported EPS"]-ed["EPS Estimate"])/
                                          ed["EPS Estimate"].abs()*100).round(1)
                            beats  = int((ed["Reported EPS"]>=ed["EPS Estimate"]).sum())
                            misses = len(ed) - beats
                            avg_su = round(ed["Surp"].mean(),1)

                            pdf.metric_table([
                                ("Quarters Tracked", str(len(ed))),
                                ("EPS Beats",        str(beats)),
                                ("EPS Misses",       str(misses)),
                                ("Avg EPS Surprise", f"{avg_su}%"),
                            ])
                            pdf.ln(2)

                            # Earnings table
                            pdf.set_font("Helvetica","B",8)
                            pdf.set_fill_color(240,240,245)
                            pdf.set_text_color(26,26,46)
                            pdf.cell(45,6,"Date",border=1,fill=True)
                            pdf.cell(45,6,"EPS Estimate",border=1,fill=True)
                            pdf.cell(45,6,"Reported EPS",border=1,fill=True)
                            pdf.cell(45,6,"Surprise %",border=1,fill=True,ln=True)

                            pdf.set_font("Helvetica","",8)
                            for date, row in ed.tail(12).iterrows():
                                beat = row["Reported EPS"] >= row["EPS Estimate"]
                                pdf.set_text_color(0,0,0)
                                pdf.cell(45,5,clean(str(date)[:10]),border=1)
                                pdf.cell(45,5,clean(str(round(row["EPS Estimate"],2))),border=1)
                                if beat:
                                    pdf.set_text_color(39,174,96)
                                else:
                                    pdf.set_text_color(231,76,60)
                                pdf.cell(45,5,clean(str(round(row["Reported EPS"],2))),border=1)
                                surp = row["Surp"]
                                pdf.cell(45,5,clean(f"{surp:+.1f}%"),border=1,ln=True)
                            pdf.set_text_color(0,0,0)
                            pdf.ln(4)
                        except: pass
                    else:
                        pdf.set_font("Helvetica","I",9)
                        pdf.cell(0,6,"No earnings data available.",ln=True)

                # ── SENTIMENT ─────────────────────────────────
                if inc_sent and articles:
                    pdf.section_title("NEWS SENTIMENT")
                    pdf.metric_table([
                        ("Overall Sentiment", sent_label),
                        ("Avg Score",         f"{avg_s:+.3f}"),
                        ("Positive Articles", str(pos_c)),
                        ("Negative Articles", str(neg_c)),
                        ("Total Articles",    str(len(articles))),
                    ])

                    if avg_s > 0.3:
                        flag = "Extreme Optimism - very bullish sentiment. Good news may already be priced in."
                    elif avg_s > 0.1:
                        flag = "Moderately Bullish - positive sentiment with room to run."
                    elif avg_s < -0.3:
                        flag = "Extreme Pessimism - contrarian opportunity may exist if fundamentals are intact."
                    elif avg_s < -0.1:
                        flag = "Moderately Bearish - negative sentiment building."
                    else:
                        flag = "Neutral - no strong directional bias in recent news."

                    pdf.set_font("Helvetica","B",9)
                    pdf.set_text_color(26,26,46)
                    pdf.cell(0,5,"Behavioral Flag:",ln=True)
                    pdf.set_font("Helvetica","",9)
                    pdf.set_text_color(60,60,60)
                    pdf.multi_cell(0,5,clean(flag))
                    pdf.set_text_color(0,0,0)
                    pdf.ln(3)

                    pdf.set_font("Helvetica","B",9)
                    pdf.set_text_color(26,26,46)
                    pdf.cell(0,5,"Recent Headlines:",ln=True)
                    pdf.set_text_color(0,0,0)
                    for a in articles[:10]:
                        tag = "+" if a["label"]=="Positive" else \
                              "-" if a["label"]=="Negative" else "o"
                        lc  = (39,174,96)   if a["label"]=="Positive" else \
                              (231,76,60)   if a["label"]=="Negative" else \
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
                    "financial advice or an offer to buy or sell any security. Data sourced "
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
