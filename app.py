import streamlit as st

st.set_page_config(
    page_title="Stock Analyzer",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Stock Analyzer")
st.caption("Fundamental analysis through a behavioral lens")

ticker = st.text_input("Enter any ticker symbol", value="AAPL").upper().strip()

st.sidebar.title("Modules")
module = st.sidebar.radio("Go to:", [
    "📊 Fundamentals",
    "📈 Earnings Analysis",
    "📰 News Sentiment",
    "📄 PDF Export"
])

if ticker:
    if module == "📊 Fundamentals":
        from modules import fundamentals
        fundamentals.show(ticker)
    elif module == "📈 Earnings Analysis":
        from modules import earnings
        earnings.show(ticker)
    elif module == "📰 News Sentiment":
        from modules import news
        news.show(ticker)
    elif module == "📄 PDF Export":
        from modules import pdf_export
        pdf_export.show(ticker)
