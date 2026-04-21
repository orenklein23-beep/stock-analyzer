import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

def show(ticker):
    st.header(f"Fundamentals — {ticker}")

    try:
        stock = yf.Ticker(ticker)
        fast = stock.fast_info

        price = fast.get("lastPrice") or fast.get("regularMarketPrice", "N/A")
        if isinstance(price, float):
            price = round(price, 2)
        market_cap = fast.get("marketCap", 0)

        st.subheader("Key Stats")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Current Price", f"${price}")
        col2.metric("Market Cap", f"${market_cap:,.0f}")

        try:
            info = stock.info
            pe = info.get("trailingPE", "N/A")
            if isinstance(pe, float):
                pe = round(pe, 2)
            margin = info.get("profitMargins", None)
            margin_str = f"{round(margin * 100, 2)}%" if margin else "N/A"
            col3.metric("P/E Ratio", pe)
            col4.metric("Profit Margin", margin_str)
        except Exception:
            col3.metric("P/E Ratio", "N/A")
            col4.metric("Profit Margin", "N/A")

    except Exception as e:
        st.error(f"Error loading data: {e}")
        return

    st.divider()

    st.subheader("Revenue & Net Income (Annual)")
    try:
        financials = stock.financials.T
        if "Total Revenue" in financials.columns and "Net Income" in financials.columns:
            revenue = financials["Total Revenue"].dropna()
            net_income = financials["Net Income"].dropna()
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=revenue.index.astype(str),
                y=revenue.values,
                name="Revenue",
                marker_color="#4A90D9"
            ))
            fig.add_trace(go.Bar(
                x=net_income.index.astype(str),
                y=net_income.values,
                name="Net Income",
                marker_color="#27AE60"
            ))
            fig.update_layout(barmode="group", xaxis_title="Year", yaxis_title="USD", height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Revenue/Net Income data not available for this ticker.")
    except Exception as e:
        st.warning(f"Could not load financials: {e}")

    st.divider()

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
