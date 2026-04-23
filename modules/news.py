import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

def simple_sentiment(text):
    positive = ["beat","strong","growth","record","surge","gain","profit","up","rise",
                "raised","upgrade","outperform","bullish","exceed","positive","boost",
                "soar","rally","jump","expand","buy","opportunity","innovative","leading",
                "higher","recovery","rebound","optimistic","confident","robust","solid"]
    negative = ["miss","weak","decline","fall","drop","loss","down","cut","lower","risk",
                "downgrade","underperform","bearish","disappoint","negative","concern",
                "slump","crash","sell","lawsuit","investigation","warning","slowdown",
                "trouble","struggle","pressure","volatile","uncertain","fear","worry"]

    text_lower = text.lower()
    words = text_lower.split()

    pos = sum(1 for w in positive if w in text_lower)
    neg = sum(1 for w in negative if w in text_lower)
    total = pos + neg

    if total == 0:
        return 0.0, "Neutral"

    # Weighted score — require at least 2 matches for extreme scores
    raw = (pos - neg) / total
    # Dampen single-match extremes
    weight = min(total, 5) / 5
    score = round(raw * weight, 3)

    if score > 0.15:  return score, "Positive"
    if score < -0.15: return score, "Negative"
    return score, "Neutral"

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
    overall_color = "#26a69a" if avg_score > 0.1 else "#ef5350" if avg_score < -0.1 else "#888"

    st.markdown(f"""
    <div style='background:linear-gradient(135deg,#1a1a2e,#16213e);
                padding:24px 32px;border-radius:16px;margin-bottom:24px'>
        <div style='color:#888;font-size:12px;letter-spacing:3px'>OVERALL SENTIMENT</div>
        <div style='color:{overall_color};font-size:40px;font-weight:800;margin:8px 0'>{overall}</div>
        <div style='color:#aaa;font-size:15px'>Based on {len(articles)} recent articles &nbsp;|&nbsp; Avg score: {avg_score:+.3f}</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Articles Analyzed", len(articles))
    c2.metric("🟢 Positive", pos_count)
    c3.metric("🟡 Neutral",  neu_count)
    c4.metric("🔴 Negative", neg_count)

    st.divider()

    # ── PIE + BAR ──────────────────────────────────────────────
    st.subheader("📊 Sentiment Breakdown")
    col1, col2 = st.columns(2)

    with col1:
        fig1 = go.Figure(go.Pie(
            labels=["Positive","Neutral","Negative"],
            values=[pos_count, neu_count, neg_count],
            hole=0.55,
            marker_colors=["#26a69a","#555","#ef5350"],
            textfont=dict(color="white", size=14)
        ))
        fig1.update_layout(height=300,
            paper_bgcolor="#0e1117", font_color="white",
            legend=dict(font=dict(color="white")))
        st.plotly_chart(fig1, use_container_width=True)

    with col2:
        fig2 = go.Figure(go.Bar(
            x=["🟢 Positive","🟡 Neutral","🔴 Negative"],
            y=[pos_count, neu_count, neg_count],
            marker_color=["#26a69a","#555","#ef5350"],
            text=[pos_count, neu_count, neg_count],
            textposition="outside",
            textfont=dict(color="white", size=16),
            width=0.5
        ))
        fig2.update_layout(height=300,
            paper_bgcolor="#0e1117", plot_bgcolor="#0e1117",
            font_color="white", showlegend=False,
            yaxis=dict(range=[0, max(pos_count, neu_count, neg_count) * 1.3]))
        fig2.update_xaxes(gridcolor="#1e1e1e")
        fig2.update_yaxes(gridcolor="#1e1e1e")
        st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── SCORE PER ARTICLE ──────────────────────────────────────
    st.subheader("📈 Sentiment Score by Article")

    sorted_articles = sorted(articles, key=lambda x: x["score"])
    scores = [a["score"] for a in sorted_articles]
    labels = [a["title"][:50]+"..." if len(a["title"]) > 50 else a["title"] for a in sorted_articles]
    colors = ["#26a69a" if s > 0.15 else "#ef5350" if s < -0.15 else "#777" for s in scores]

    fig3 = go.Figure(go.Bar(
        x=scores,
        y=labels,
        orientation="h",
        marker_color=colors,
        marker_line_width=0,
        text=[f"{s:+.2f}" for s in scores],
        textposition="outside",
        textfont=dict(color="white", size=11),
        width=0.6
    ))
    fig3.add_vline(x=0, line_dash="solid", line_color="#444", line_width=2)

    max_abs = max(abs(min(scores)), abs(max(scores)), 0.5)
    fig3.update_layout(
        height=max(380, len(articles)*36),
        paper_bgcolor="#0e1117",
        plot_bgcolor="#0e1117",
        font_color="white",
        xaxis_title="Sentiment Score",
        xaxis=dict(range=[-(max_abs+0.15), max_abs+0.15], gridcolor="#1e1e1e"),
        yaxis=dict(gridcolor="#1e1e1e"),
        margin=dict(l=10, r=80, t=20, b=40)
    )
    st.plotly_chart(fig3, use_container_width=True)

    st.divider()

    # ── BEHAVIORAL FLAG ────────────────────────────────────────
    st.subheader("🧠 Behavioral Sentiment Flag")
    if avg_score > 0.3:
        st.error("⚠️ **Extreme Optimism Detected** — Sentiment is very bullish. Good news may already be priced in. Classic buy-the-rumor, sell-the-news risk.")
    elif avg_score > 0.1:
        st.success("✅ **Moderately Bullish** — Positive sentiment with room to run. Watch for price action confirmation.")
    elif avg_score < -0.3:
        st.success("💡 **Extreme Pessimism Detected** — Sentiment is very bearish. Contrarian opportunity may exist if fundamentals are intact.")
    elif avg_score < -0.1:
        st.warning("⚠️ **Moderately Bearish** — Negative sentiment building. Monitor for deterioration or a reversal catalyst.")
    else:
        st.info("🟡 **Neutral Sentiment** — No strong directional bias in recent news. Market is in wait-and-see mode.")

    st.divider()

    # ── ARTICLE LIST ───────────────────────────────────────────
    st.subheader("📰 All Recent Articles")
    filt = st.radio("Filter by sentiment:", ["All","Positive","Neutral","Negative"], horizontal=True)
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
