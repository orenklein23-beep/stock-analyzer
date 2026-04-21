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
ticker = st.text_input("Enter a ticker symbol", value="AAPL").upper().strip()

if ticker:
    st.success(f"Analyzing: {ticker}")
    st.info("Modules coming soon...")
