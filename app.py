import streamlit as st

# --- Page Config ---
st.set_page_config(
    page_title="Stock Analyzer",
    page_icon="📈",
    layout="wide"
)

# --- Header ---
st.title("📈 Stock Analyzer")
st.caption("Fundamental analysis through a behavioral lens")

# --- Ticker Input ---
ticker = st.text_input("Enter any ticker symbol", value="AAPL").upper().strip()

# --- Sidebar Navigation ---
st.sidebar.title("Modules")
module = st.sidebar.radio("Go to:", [
    "📊 Fundamentals",
    "📈 Earnings Analysis",
    "📰 News Sentiment",
    "📄 PDF Export"
])

# --- Load Module ---
if ticker:
    if module == "📊 Fundamentals":
        from modules import fundamentals
        fundamentals.show(ticker)
    elif module == "📈 Earnings Analysis":
        from modules import earnings
        earnings.show(ticker)
    else:
        st.info(f"{module} coming soon...")
