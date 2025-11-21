"""
Streamlit Frontend for Decentralized Beauty Contest Game
Run with: streamlit run app_improved.py
"""

import streamlit as st
import hashlib
import requests
import csv
import io
from datetime import datetime, timezone
from statistics import mean

# --- App appearance and styling ---
st.set_page_config(page_title="Beauty Contest — Decentralized Game", page_icon="🎯", layout="wide")

# Custom CSS to make interface cleaner
st.markdown(
    """
    <style>
    .css-1d391kg {padding-top: 0rem;} /* adjust top padding for streamlit headers */
    .stApp {background: linear-gradient(180deg,#f7fbff, #ffffff);}    
    .big-title {font-size:32px; font-weight:700; color:#0b5394; margin-bottom:8px;}
    .subtitle {font-size:14px; color:#444444; margin-top:0;}
    .card {background:#ffffff; border-radius:12px; padding:16px; box-shadow: 0 6px 18px rgba(32,33,36,0.06);}    
    .muted {color:#6b6b6b; font-size:13px;}
    </style>
    """,
    unsafe_allow_html=True,
)

def render_header():
    col1, col2 = st.columns([6,2])
    with col1:
        st.markdown('<div class="big-title">🎯 Decentralized Beauty Contest</div>', unsafe_allow_html=True)
        st.markdown('<div class="subtitle">Commit & reveal numbers securely with SHA-256 commitments — friendly interface for students and participants.</div>', unsafe_allow_html=True)
    with col2:
        st.image("https://upload.wikimedia.org/wikipedia/commons/3/3f/Streamlit_logo_primary_color.png", width=80)
    st.markdown("---")
# --- end styling ---

# Configuration
API_DEFAULT = "https://script.google.com/macros/s/AKfycbyNZNOE1D...bd4GbGTISJsGrnJ4PYCuip0yjSw3Lr8KkD6-kadKI9mfpKNfiAHEWb0Osw/exec"
COMMIT_DEADLINE_UTC = datetime(2025, 10, 21, 21, 59, 59, tzinfo=timezone.utc)
REVEAL_OPEN_UTC = datetime(2025, 10, 21, 22, 0, 0, tzinfo=timezone.utc)

# Utility functions

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def now_utc():
    return datetime.now(timezone.utc)

def get_csv_data(url: str):
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        return list(csv.DictReader(io.StringIO(r.text)))
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return []

def send_commit(api_url, uni_id, commit_hash):
    payload = {"kind": "commit", "uni_id": uni_id, "commit": commit_hash}
    try:
        r = requests.post(api_url, json=payload, timeout=15)
        return r.status_code, r.text
    except Exception as e:
        return None, str(e)

def send_reveal(api_url, uni_id, number, nonce):
    payload = {"kind": "reveal", "uni_id": uni_id, "number": number, "nonce": nonce}
    try:
        r = requests.post(api_url, json=payload, timeout=15)
        return r.status_code, r.text
    except Exception as e:
        return None, str(e)

# Time windows
commit_open = now_utc() < COMMIT_DEADLINE_UTC
reveal_open = now_utc() >= REVEAL_OPEN_UTC

# Small helper for compact metric display

def small_metric(label, value, help_text=None):
    st.metric(label, value, help=help_text)

# Render header
render_header()

# Show quick status in a neat row
with st.container():
    c1, c2, c3 = st.columns(3)
    with c1:
        if commit_open:
            st.success("✅ Commits OPEN")
        else:
            st.error("❌ Commits CLOSED")
    with c2:
        st.markdown("**Reveal Opens:**")
        st.markdown("2025-10-21 22:00:00 UTC")
        st.markdown("(2025-10-22 00:00:00 Paris)")
    with c3:
        if reveal_open:
            st.success("✅ Reveals OPEN")
        else:
            st.warning("⏳ Reveals NOT OPEN")

# Main Content Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📝 Commit", "🔓 Reveal", "📊 Leaderboard", "ℹ️ Instructions"])

# TAB 1: COMMIT PHASE
with tab1:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📝 Commit Phase")

    if not commit_open:
        st.error("⛔ The commit window is CLOSED. Deadline has passed.")
    else:
        st.success("✅ Commit window is OPEN. Submit your commitment before the deadline!")

    with st.form("commit_form"):
        st.subheader("Create Your Commitment")
        col1, col2 = st.columns(2)
        with col1:
            uni_id = st.text_input("University ID", help="Enter your unique ID used for the contest")
            number = st.number_input("Pick a number (0-100)", min_value=0, max_value=100, value=42)
        with col2:
            nonce = st.text_input("Nonce (secret)", type="password", help="A secret string to secure your commitment")
            api_url = st.text_input("Server API URL", value=API_DEFAULT)

        if uni_id and nonce is None:
            st.info("Nonce helps prove your commitment later. Keep it safe.")

        # Show precomputed hash in a small info box
        if uni_id and nonce:
            preimage = f"{uni_id}|{number}|{nonce}"
            commit_hash = sha256(preimage)
            st.code(f"Commit hash: {commit_hash}")

        submit = st.form_submit_button("🔒 Submit Commitment")
        if submit:
            if not uni_id or not nonce:
                st.error("❌ Please fill in all fields")
            elif not commit_open:
                st.error("❌ Commit window is closed")
            else:
                with st.spinner("Submitting commit..."):
                    status, resp = send_commit(api_url, uni_id, commit_hash)
                    if status:
                        st.success(f"✅ Server Response ({status}): {resp}")
                        st.balloons()
                    else:
                        st.error(f"❌ Error: {resp}")
    st.markdown('</div>', unsafe_allow_html=True)

# TAB 2: REVEAL PHASE
with tab2:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🔓 Reveal Phase")
    st.write("When reveals are open, submit your number and nonce to prove your commit.")

    with st.form("reveal_form"):
        reveal_uni_id = st.text_input("University ID", key="reveal_uni_id")
        reveal_number = st.number_input("Your number", min_value=0, max_value=100, key="reveal_number")
        reveal_nonce = st.text_input("Nonce", type="password", key="reveal_nonce")

        if reveal_uni_id and reveal_nonce:
            check_preimage = f"{reveal_uni_id}|{reveal_number}|{reveal_nonce}"
            check_hash = sha256(check_preimage)
            st.info(f"Your commitment hash should be: `{check_hash}`")

        submit_reveal = st.form_submit_button("🔓 Reveal Commitment", type="primary")
        if submit_reveal:
            if not reveal_uni_id or not reveal_nonce:
                st.error("❌ Please fill in all fields")
            elif not reveal_open:
                st.error("❌ Reveal window is not open yet!")
            else:
                with st.spinner("Submitting reveal..."):
                    status, response = send_reveal(api_url, reveal_uni_id, reveal_number, reveal_nonce)
                    if status:
                        st.success(f"✅ Server Response ({status}): {response}")
                        st.balloons()
                    else:
                        st.error(f"❌ Error: {response}")
    st.markdown('</div>', unsafe_allow_html=True)

# TAB 3: LEADERBOARD
with tab3:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📊 Current Status")
    col1, col2 = st.columns(2)
    # Leaderboard fetching logic preserved from original app
    try:
        data = get_csv_data(API_DEFAULT)
        if data:
            st.write("Recent reveals and commits (latest entries):")
            st.dataframe(data[:10])
        else:
            st.info("No data available yet.")
    except Exception as e:
        st.error(f"Error loading leaderboard: {e}")
    st.markdown('</div>', unsafe_allow_html=True)

# TAB 4: INSTRUCTIONS
with tab4:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("ℹ️ Instructions")
    st.markdown("""
    ## How to participate
    1. Enter your University ID
    2. Enter your number (exactly as committed)
    3. Enter your nonce (exactly as committed)
    4. Submit to reveal

    ### Phase 3: Results
    1. After all reveals, winners are calculated
    2. The person(s) closest to 2/3 of the average wins!

    ## Technical Details

    - Uses cryptographic commitments (SHA-256) to prevent cheating
    - Commit before seeing others' numbers
    - Reveal after deadline to verify commitment
    - Append-only: Latest reveal per participant is used for result calculation
    """)
    st.markdown('</div>', unsafe_allow_html=True)

# Footer with quick source reminder (kept unchanged)
st.markdown("---")
st.markdown('**Backend API URL:** ' + API_DEFAULT)
