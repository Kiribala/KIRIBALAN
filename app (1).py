import streamlit as st
import pandas as pd
import datetime

# ---------------------------------------------------
# PAGE CONFIG
# ---------------------------------------------------
st.set_page_config(
    page_title="International Transfer Dashboard",
    page_icon="💸",
    layout="wide"
)

# ---------------------------------------------------
# SIDEBAR
# ---------------------------------------------------
with st.sidebar:
    st.title("🌍 BlockSend")
    st.markdown("International Money Transfer")

    st.markdown("### Navigation")
    page = st.radio("", ["Dashboard", "Send Money", "Receive Money", "Transaction History"])

    st.markdown("---")
    st.write("Logged in as: **User123**")


# ---------------------------------------------------
# DASHBOARD PAGE
# ---------------------------------------------------
if page == "Dashboard":
    st.title("💹 Dashboard Overview")
    st.write("Your international transfers at a glance.")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Total Sent", "$12,450")
    with col2:
        st.metric("Total Received", "$8,320")
    with col3:
        st.metric("Pending Transactions", "3")

    st.markdown("### Recent Transfers")

    data = {
        "Date": ["2025-01-03", "2025-01-02", "2025-01-01"],
        "Type": ["Sent", "Received", "Sent"],
        "Amount": ["$350", "$420", "$150"],
        "Country": ["Canada", "UK", "Japan"],
        "Status": ["Completed", "Completed", "Completed"]
    }

    st.dataframe(pd.DataFrame(data), use_container_width=True)


# ---------------------------------------------------
# SEND MONEY PAGE
# ---------------------------------------------------
if page == "Send Money":
    st.title("💸 Send Money Internationally")

    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Recipient Name")
        country = st.selectbox("Recipient Country", ["USA", "Canada", "UK", "Germany", "Australia", "Japan", "India"])
        amount = st.number_input("Amount in USD", min_value=1, step=1)
        reason = st.text_input("Purpose of Transfer")

    with col2:
        st.markdown("**Transfer Details**")
        st.info("Your transfer will be processed in 1–5 business days.")
        exchange_rate = 0.92  # mock rate
        st.write(f"Estimated Exchange Rate: **{exchange_rate}**")
        converted = amount * exchange_rate
        st.write(f"Recipient Gets: **{converted:.2f}** (local currency)")

    if st.button("Send Money"):
        if name and amount > 0:
            st.success(f"Transaction submitted successfully to **{name}**.")
        else:
            st.error("Please fill all required fields.")


# ---------------------------------------------------
# RECEIVE MONEY PAGE
# ---------------------------------------------------
if page == "Receive Money":
    st.title("📥 Receive Money")

    st.markdown("Enter the sender information:")

    sender = st.text_input("Sender Name")
    country = st.selectbox("Sender Country", ["USA", "Canada", "UK", "Germany", "Australia", "Japan", "India"])
    amount = st.number_input("Amount Sent (USD)", min_value=1)
    
    st.write("**Your Bank Details**")
    bank = st.text_input("Bank Name")
    acc = st.text_input("Account Number")

    if st.button("Confirm Receive"):
        if sender and bank and acc:
            st.success(f"You will receive **${amount}** from **{sender}** shortly.")
        else:
            st.error("Please fill all fields.")


# ---------------------------------------------------
# TRANSACTION HISTORY
# ---------------------------------------------------
if page == "Transaction History":
    st.title("📜 Transaction History")

    history = pd.DataFrame({
        "Date": ["2025-01-05", "2025-01-02", "2024-12-29", "2024-12-27"],
        "Type": ["Received", "Sent", "Sent", "Received"],
        "Amount": ["$500", "$300", "$200", "$650"],
        "Country": ["USA", "India", "Japan", "Germany"],
        "Status": ["Completed", "Completed", "Completed", "Completed"]
    })

    st.dataframe(history, use_container_width=True)

    st.markdown("---")
    st.caption("This is a simulated dashboard for project use only.")
