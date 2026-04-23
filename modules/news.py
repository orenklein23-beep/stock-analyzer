import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

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
    if total == 0: return 0, "Neutral"
    score = (pos - neg) / total
    if score > 0.2:  return round(score,3), "Positive"
    if score < -0.2: return round(score,3), "Negative"
    return round(score,3), "Neutral"

def show(ticker):
    st.header(f"📰 {ticker} — News Sentiment")

    with st.spinner("Loading news..."):
        stock = yf.Ticker(ticker)
        try:
            news = stock.news
        except:
            news = []

    if not news:
        st.warning("No news available for this ticker.")
        return

    # ── PARSE ARTICLES ─────────────────────────────────────────
    articles = []
    for item in news:
        try:
            content  = item.get("content", {})
            title    = content.get("title", "") if content else item.get("title", "")
            summary  = content.get("summary", "") if content else ""
            pub      = content.get("pubDate", "") if content else ""
            provider = "Unknown"
            url      = ""

            if content:
                p = content.get("provider", {})
                if isinstance(p, dict):
                    provider = p.get("displayName", "Unknown")
                c = content.get("canonicalUrl", {})
                if isinstance(c, dict):
                    url = c.get("url", "")

            if not title:
                continue

            score, label = simple_sentiment(title + " " + summary)
            articles.append({
                "title":    title,
                "summary":  summary,
                "score":    score,
                "label":    label,
                "pub":      str(pub)[:10] if pub else "N/A",
                "url":      url,
                "provider": provider
            })
        except:
            continue

    if not articles:
        st.warning("Could not parse news articles.")
        return

    # ── SUMMARY STATS ──────────────────────────────────────────
    pos_count = sum(1 for a in articles if a["label"] == "Positive")
    neg_count = sum(1 for a in articles if a["label"] == "Negative")
    neu_count = sum(1 for a in articles if a["label"] == "Neutral")
    avg_score = round(sum(a["score"] for a in articles) / len(articles), 3)
    overall   = "🟢 Bullish" if avg_score > 0.1 else "🔴 Bearish" if avg_score < -0.1 else "🟡 Neutral"

    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1a1a2e,#16213e);
                padding:24px 32px;border-radius:16px;margin-bottom:24px'>
        <div style='color:#888;font-size:12px;letter-spacing:3px'>OVERALL SENTIMENT</div>
        <div style='color:#fff;font-size:40px;font-weight:800;margin:8px 0'>{overall}</div>
        <div style='color:#aaa;font-size:15px'>Based on {len(articles)} recent articles</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg Score",    avg_score)
    c2.metric("🟢 Positive",  pos_count)
    c3.metric("🟡 Neutral",   neu_count)
    c4.metric("🔴 Negative",  neg_count)

    st.divider()

    # ── PIE + BAR ──────────────────────────────────────────────
    st.subheader("📊 Sentiment Breakdown")
    col1, col2 = st.columns(2)

    with col1:
        fig1 = go.Figure(go.Pie(
            labels=["Positive","Neutral","Negative"],
            values=[pos_count, neu_count, neg_count],
            hole=0.5,
            marker_colors=["#26a69a","#888","#ef5350"]
        ))
        fig1.update_layout(height=300,
            paper_bgcolor="#0e1117", font_color="white")
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
        fig2.update_layout(height=300,
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font_color="white")
        fig2.update_xaxes(gridcolor="#1e1e1e")
        fig2.update_yaxes(gridcolor="#1e1e1e")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── SCORE PER ARTICLE ──────────────────────────────────────
    st.subheader("📈 Sentiment Score by Article")
    scores = [a["score"] for a in articles]
    labels = [a["title"][:45]+"..." if len(a["title"]) > 45 else a["title"] for a in articles]
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
        height=max(400, len(articles)*34),
        paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
        font_color="white", xaxis_title="Sentiment Score",
        margin=dict(l=20, r=80)
    )
    fig3.update_xaxes(gridcolor="#1e1e1e", range=[-1,1])
    fig3.update_yaxes(gridcolor="#1e1e1e")
    st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # ── BEHAVIORAL FLAG ────────────────────────────────────────
    st.subheader("🧠 Behavioral Sentiment Flag")
    if avg_score > 0.3:
        st.error("⚠️ **Extreme Optimism** — Very bullish sentiment. Good news may already be priced in. Classic buy-the-rumor, sell-the-news setup.")
    elif avg_score > 0.1:
        st.success("✅ **Moderately Bullish** — Positive sentiment with room to run. Watch for price confirmation.")
    elif avg_score < -0.3:
        st.success("💡 **Extreme Pessimism** — Very bearish sentiment. Contrarian opportunity may exist if fundamentals are intact.")
    elif avg_score < -0.1:
        st.warning("⚠️ **Moderately Bearish** — Negative sentiment building. Monitor for reversal catalyst.")
    else:
        st.info("🟡 **Neutral** — No strong directional bias in recent news.")

    st.divider()

    # ── ARTICLE LIST ───────────────────────────────────────────
    st.subheader("📰 All Recent Articles")
    filt = st.radio("Filter:", ["All","Positive","Neutral","Negative"], horizontal=True)
    filtered = articles if filt == "All" else [a for a in articles if a["label"] == filt]

    for a in filtered:
        emoji = "🟢" if a["label"] == "Positive" else "🔴" if a["label"] == "Negative" else "🟡"
        with st.expander(f"{emoji} {a['title']}"):
            col1, col2, col3 = st.columns(3)
            col1.markdown(f"**Source:** {a['provider']}")
            col2.markdown(f"**Date:** {a['pub']}")
            col3.markdown(f"**Score:** `{a['score']:+.3f}`")
            if a["summary"]:
                st.markdown(f"_{a['summary']}_")
            if a["url"]:
                st.markdown(f"[Read full article →]({a['url']})")
