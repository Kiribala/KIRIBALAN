"""
Glass-themed Streamlit Frontend for Decentralized Beauty Contest Game
Run with: streamlit run app_glass_theme.py

This file is a polished rewrite of the original app. It keeps the same backend API URL and logic for commits/reveals but improves:
- Layout (left control panel, center main, right leaderboard)
- Glass/frosted UI with modern cards
- Better structure, error handling and comments
- Reusable utility functions and session state usage

Author: generated for user (student-friendly, simple words)
"""

import streamlit as st
import hashlib
import requests
import csv
import io
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Optional

# ---- Keep backend source unchanged ----
API_DEFAULT = "https://script.google.com/macros/s/AKfycbyNZNOE1D...bd4GbGTISJsGrnJ4PYCuip0yjSw3Lr8KkD6-kadKI9mfpKNfiAHEWb0Osw/exec"

# ---- Page setup ----
st.set_page_config(page_title="Beauty Contest — Glass UI", page_icon="🎯", layout="wide")

# ---- Glass theme CSS ----
st.markdown(
    """
    <style>
    :root{
      --glass-bg: rgba(255,255,255,0.14);
      --glass-border: rgba(255,255,255,0.25);
      --accent: rgba(11,83,148,0.9);
    }
    body {background: linear-gradient(135deg, rgba(3,37,65,0.92) 0%, rgba(7,58,92,0.9) 100%);}
    .glass-card{backdrop-filter: blur(8px) saturate(140%); -webkit-backdrop-filter: blur(8px) saturate(140%);
               background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02));
               border: 1px solid var(--glass-border); border-radius:14px; padding:18px; box-shadow: 0 8px 30px rgba(2,6,23,0.6); color: #eaf4ff}
    .muted {color: rgba(234,244,255,0.75); font-size:13px}
    .title {font-size:26px; font-weight:700; color: white}
    .small {font-size:13px}
    .wide-input input{background: transparent !important; color: white !important}
    .logo {border-radius:8px}

    /* Improve Streamlit default spacing for a compact look */
    .css-1d391kg {padding-top: 0.5rem}
    .stButton>button{border-radius:10px}

    /* Mobile responsiveness tweaks */
    @media (max-width: 768px){
      .glass-card{padding:14px}
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---- Utilities ----

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def fetch_csv(url: str, timeout: int = 12) -> List[Dict[str, str]]:
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return list(csv.DictReader(io.StringIO(resp.text)))
    except Exception as e:
        st.session_state.setdefault("last_error", str(e))
        return []


def post_json(url: str, payload: dict, timeout: int = 12) -> Tuple[Optional[int], str]:
    try:
        r = requests.post(url, json=payload, timeout=timeout)
        return r.status_code, r.text
    except Exception as e:
        return None, str(e)


# ---- Session state defaults ----
if "commit_hash" not in st.session_state:
    st.session_state.commit_hash = ""
if "api_url" not in st.session_state:
    st.session_state.api_url = API_DEFAULT

# ---- Layout: left (controls), center (main), right (info) ----
left_col, center_col, right_col = st.columns([2, 4, 2], gap="large")

with left_col:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="title">🎯 Play — Commit & Reveal</div>', unsafe_allow_html=True)
    st.markdown('<p class="muted">Use the commit & reveal flow. Keep your nonce secret.</p>', unsafe_allow_html=True)

    st.markdown('---')
    with st.form("control_form"):
        uni_id = st.text_input("University ID", placeholder="e.g. NEOMA123", max_chars=64)
        number = st.number_input("Pick a number (0–100)", min_value=0, max_value=100, value=50)
        nonce = st.text_input("Nonce (secret)", type="password", placeholder="A secret passphrase")
        api_url_input = st.text_input("API URL", value=st.session_state.api_url)
        commit_action = st.form_submit_button("Generate Commitment")

        if commit_action:
            st.session_state.api_url = api_url_input
            if not uni_id or not nonce:
                st.warning("Fill University ID and nonce to generate a proper commitment.")
            else:
                pre = f"{uni_id}|{number}|{nonce}"
                h = sha256(pre)
                st.session_state.commit_hash = h
                st.success("Commitment generated — keep your nonce safe.")

    if st.session_state.commit_hash:
        st.markdown("**Your commit hash**")
        st.code(st.session_state.commit_hash)
        if st.button("Submit commit to server"):
            payload = {"kind": "commit", "uni_id": uni_id, "commit": st.session_state.commit_hash}
            status, text = post_json(st.session_state.api_url, payload)
            if status:
                st.success(f"Server responded: {status}")
            else:
                st.error(f"Error sending commit: {text}")

    st.markdown('</div>', unsafe_allow_html=True)

with center_col:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div style="display:flex; align-items:center; justify-content:space-between"><div class="title">🔓 Reveal / Verify</div><div class="small muted">UTC time: ' + now_utc().strftime('%Y-%m-%d %H:%M:%S') + '</div></div>', unsafe_allow_html=True)
    st.markdown('<p class="muted">When reveals are open, submit your number and nonce to prove your commit.</p>', unsafe_allow_html=True)

    with st.form("reveal_form"):
        r_uni = st.text_input("University ID", key="r_uni")
        r_number = st.number_input("Number (0–100)", min_value=0, max_value=100, key="r_num")
        r_nonce = st.text_input("Nonce", type="password", key="r_nonce")
        reveal_btn = st.form_submit_button("Reveal")

        if reveal_btn:
            if not r_uni or not r_nonce:
                st.warning("Enter University ID and the nonce used when committing.")
            else:
                check = sha256(f"{r_uni}|{r_number}|{r_nonce}")
                st.info(f"Computed commitment hash: `{check}`")
                payload = {"kind": "reveal", "uni_id": r_uni, "number": int(r_number), "nonce": r_nonce}
                status, text = post_json(st.session_state.api_url, payload)
                if status:
                    st.success(f"Server responded: {status}")
                else:
                    st.error(f"Reveal failed: {text}")

    st.markdown('</div>', unsafe_allow_html=True)

with right_col:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="title">📊 Leaderboard</div>', unsafe_allow_html=True)
    st.markdown('<p class="muted">Latest reveals and simple stats</p>', unsafe_allow_html=True)

    # Fetch leaderboard (non-blocking simple call)
    with st.spinner("Loading leaderboard..."):
        rows = fetch_csv(st.session_state.api_url)

    if rows:
        # show last 12 entries nicely
        sample = rows[-12:][::-1]
        # display as simple table
        st.table([{k: v for k, v in r.items()} for r in sample])

        # compute 2/3 of average if numbers exist
        try:
            nums = [float(r.get("number", 0)) for r in rows if r.get("number") not in (None, "")]
            if nums:
                avg = sum(nums) / len(nums)
                target = 2 * avg / 3
                st.markdown(f"**Average:** {avg:.2f}")
                st.markdown(f"**2/3 of average (target):** {target:.2f}")
        except Exception:
            st.info("Not enough data to compute stats.")
    else:
        last_err = st.session_state.get("last_error", None)
        if last_err:
            st.error(f"Could not load leaderboard: {last_err}")
        else:
            st.info("No data available yet.")

    st.markdown('</div>', unsafe_allow_html=True)

# ---- Bottom: instructions and footer ----
st.markdown('<div style="height:18px"></div>', unsafe_allow_html=True)
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown('''
### How it works
- Commit: create a hash of `UniversityID|number|nonce` and send it to the server.
- Reveal: later submit `number` and `nonce` so others can verify you didn't change your number.
- Winner: closest to 2/3 of the average of revealed numbers wins.

Keep your nonce secret. If you lose the nonce you cannot prove your commit.
''')
st.markdown(f'**Backend API URL (unchanged):** {API_DEFAULT}')
st.markdown('</div>', unsafe_allow_html=True)

# ---- End of file ----
