import streamlit as st
import yfinance as yf
import plotly.graph_objects as go
import requests
from datetime import datetime, timedelta
import re

def simple_sentiment(text):
    """Score sentiment without any external API"""
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
    if total == 0: return 0, "Neutral"
    score = (pos - neg) / total
    if score > 0.2:  return score,  "Positive"
    if score < -0.2: return score,  "Negative"
    return score, "Neutral"

def show(ticker):
    st.header(f"📰 {ticker} — News Sentiment")

    with st.spinner("Loading news..."):
        stock = yf.Ticker(ticker)
        try: news = stock.news
        except: news = []

        f = stock.fast_info
        price = float(f.get("lastPrice") or f.get("regularMarketPrice") or 0)

    if not news:
        st.warning("No news available for this ticker.")
        return

    # ── SCORE ALL ARTICLES ─────────────────────────────────────
    articles = []
    for item in news:
        try:
            content = item.get("content", {})
            title   = content.get("title", "") or item.get("title", "")
            summary = content.get("summary", "") or ""
            text    = title + " " + summary
            pub     = content.get("pubDate", "") or item.get("providerPublishTime", "")
            url     = content.get("canonicalUrl", {}).get("url", "") if isinstance(content.get("canonicalUrl"), dict) else ""
            provider = content.get("provider", {}).get("displayName", "Unknown") if isinstance(content.get("provider"), dict) else "Unknown"

            if not title: continue

            score, label = simple_sentiment(text)
            articles.append({
                "title":    title,
                "summary":  summary,
                "score":    score,
                "label":    label,
                "pub":      str(pub)[:10] if pub else "N/A",
                "url":      url,
                "provider": provider
            })
        except: continue

    if not articles:
        st.warning("Could not parse news articles.")
        return

    # ── SENTIMENT SUMMARY CARDS ────────────────────────────────
    pos_count = sum(1 for a in articles if a["label"] == "Positive")
    neg_count = sum(1 for a in articles if a["label"] == "Negative")
    neu_count = sum(1 for a in articles if a["label"] == "Neutral")
    avg_score = round(sum(a["score"] for a in articles) / len(articles), 3)

    overall = "🟢 Bullish" if avg_score > 0.1 else "🔴 Bearish" if avg_score < -0.1 else "🟡 Neutral"

    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1a1a2e,#16213e);
                padding:24px 32px;border-radius:16px;margin-bottom:24px'>
        <div style='color:#888;font-size:12px;letter-spacing:3px'>OVERALL SENTIMENT</div>
        <div style='color:#fff;font-size:40px;font-weight:800;margin:8px 0'>{overall}</div>
        <div style='color:#aaa;font-size:15px'>Based on {len(articles)} recent articles</div>
    </div>
    """, unsafe_allow_html=True)

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Avg Sentiment Score", avg_score)
    c2.metric("🟢 Positive",  pos_count)
    c3.metric("🟡 Neutral",   neu_count)
    c4.metric("🔴 Negative",  neg_count)

    st.divider()

    # ── SENTIMENT DISTRIBUTION PIE ────────────────────────────
    st.subheader("📊 Sentiment Breakdown")
    col1, col2 = st.columns(2)

    with col1:
        fig1 = go.Figure(go.Pie(
            labels=["Positive","Neutral","Negative"],
            values=[pos_count, neu_count, neg_count],
            hole=0.5,
            marker_colors=["#26a69a","#888","#ef5350"],
            textfont=dict(color="white")
        ))
        fig1.update_layout(height=320,
            paper_bgcolor="#0e1117", font_color="white",
            legend=dict(font=dict(color="white")),
            showlegend=True)
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = go.Figure(go.Bar(
            x=["Positive","Neutral","Negative"],
            y=[pos_count, neu_count, neg_count],
            marker_color=["#26a69a","#888","#ef5350"],
            text=[pos_count, neu_count, neg_count],
            textposition="outside",
            textfont=dict(color="white")
        ))
        fig2.update_layout(height=320,
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font_color="white", showlegend=False)
        fig2.update_xaxes(gridcolor="#1e1e1e")
        fig2.update_yaxes(gridcolor="#1e1e1e")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── SENTIMENT SCORE PER ARTICLE ───────────────────────────
    st.subheader("📈 Sentiment Score by Article")
    scores = [a["score"] for a in articles]
    labels = [a["title"][:40]+"..." if len(a["title"]) > 40 else a["title"] for a in articles]
    colors = ["#26a69a" if s > 0.1 else "#ef5350" if s < -0.1 else "#888" for s in scores]

    fig3 = go.Figure(go.Bar(
        x=scores, y=labels,
        orientation="h",
        marker_color=colors,
        text=[f"{s:+.2f}" for s in scores],
        textposition="outside",
        textfont=dict(color="white")
    ))
    fig3.add_vline(x=0, line_dash="dash", line_color="#888")
    fig3.update_layout(
        height=max(400, len(articles)*32),
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font_color="white", xaxis_title="Sentiment Score",
        margin=dict(l=20, r=80)
    )
    fig3.update_xaxes(gridcolor="#1e1e1e", range=[-1,1])
    fig3.update_yaxes(gridcolor="#1e1e1e")
    st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # ── BEHAVIORAL SENTIMENT FLAGS ────────────────────────────
    st.subheader("🧠 Behavioral Sentiment Flags")

    if avg_score > 0.3:
        st.error("⚠️ **Extreme Optimism Detected** — Sentiment is very bullish. Historically, extreme positive sentiment can signal a crowded trade. Consider whether good news is already priced in.")
    elif avg_score > 0.1:
        st.success("✅ **Moderately Bullish** — Positive sentiment with room to run. Watch for confirmation in price action.")
    elif avg_score < -0.3:
        st.success("💡 **Extreme Pessimism Detected** — Sentiment is very bearish. Contrarian opportunity may exist if fundamentals are intact.")
    elif avg_score < -0.1:
        st.warning("⚠️ **Moderately Bearish** — Negative sentiment building. Monitor for further deterioration or a reversal catalyst.")
    else:
        st.info("🟡 **Neutral Sentiment** — No strong directional bias in recent news.")

    st.divider()

    # ── ALL ARTICLES ──────────────────────────────────────────
    st.subheader("📰 All Recent Articles")

    sentiment_filter = st.radio("Filter by sentiment:",
        ["All","Positive","Neutral","Negative"], horizontal=True)

    filtered = articles if sentiment_filter == "All" else \
               [a for a in articles if a["label"] == sentiment_filter]

    for a in filtered:
        color = "#26a69a" if a["label"] == "Positive" else \
                "#ef5350"  if a["label"] == "Negative" else "#888"
        label_emoji = "🟢" if a["label"] == "Positive" else \
                      "🔴" if a["label"] == "Negative" else "🟡"

        with st.expander(f"{label_emoji} {a['title']}"):
            col1, col2, col3 = st.columns(3)
            col1.markdown(f"**Source:** {a['provider']}")
            col2.markdown(f"**Date:
