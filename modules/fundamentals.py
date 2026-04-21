import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

def show(ticker):
    st.header(f"📊 Fundamentals — {ticker}")

    stock = yf.Ticker(ticker)
    info = stock.info

    if not info or (info.get("currentPrice") is None and info.get("regularMarketPrice") is None):
        st.error(f"Could not find data for '{ticker}'. Check the ticker and try again.")
        return

    # --- Key Stats ---
    st.subheader("Key Stats")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"${info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))}")
    col2.metric("P/E Ratio", info.get("trailingPE", "N/A"))
    col3.metric("Market Cap", f"${info.get('marketCap', 0):,.0f}")
    col4.metric("Profit Margin", f"{round(info.get('profitMargins', 0) * 100, 2)}%")

    st.divider()

    # --- Revenue & Net Income Chart ---
    st.subheader("Revenue & Net Income (Annual)")
    try:
        financials = stock.financials.T
        if "Total Revenue" in financials.columns and "Net Income" in financials.columns:
            revenue = financials["Total Revenue"].dropna()
            net_income = financials["Net Income"].dropna()

            fig = go.Figure()
            fig.add_trace(go.Bar(x=revenue.index.astype(str), y=revenue.values, name="Revenue", marker_color="#4A90D9"))
            fig.add_trace(go.Bar(x=net_income.index.astype(str), y=net_income.values, name="Net Income", marker_color="#27AE60"))
            fig.update_layout(barmode="group", xaxis_title="Year", yaxis_title="USD", height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Revenue/Net Income data not available for this ticker.")
    except Exception as e:
        st.warning(f"Could not load financials: {e}")

    st.divider()

    # --- Balance Sheet ---
    st.subheader("Balance Sheet Snapshot")
    try:
        balance = stock.balance_sheet.T
        col1, col2 = st.columns(2)
        if "Total Debt" in balance.columns:
            col1.metric("Total Debt (latest)", f"${balance['Total Debt'].iloc[0]:,.0f}")
        if "Cash And Cash Equivalents" in balance.columns:
            col2.metric("Cash (latest)", f"${balance['Cash And Cash Equivalents'].iloc[0]:,.0f}")
    except Exception as e:
        st.warning(f"Could not load balance sheet: {e}")

    st.divider()

    # --- Raw Data ---
    with st.expander("🔍 See all raw data"):
        st.json(info)
