"""
Streamlit Frontend for Decentralized Beauty Contest Game
Run with: streamlit run app.py
"""

import streamlit as st
import hashlib
import requests
import csv
import io
from datetime import datetime, timezone
from statistics import mean
import pandas as pd

# Configuration (UNCHANGED)
API_DEFAULT = "https://script.google.com/macros/s/AKfycbyNZNOE1DYNbd4GbGTISJsGrnJ4PYCuip0yjSw3Lr8KkD6-kadKI9mfpKNfiAHEWb0Osw/exec"
COMMIT_DEADLINE_UTC = datetime(2025, 10, 21, 21, 59, 59, tzinfo=timezone.utc)
REVEAL_OPEN_UTC = datetime(2025, 10, 21, 22, 0, 0, tzinfo=timezone.utc)
K_FACTOR = 2/3

# Helper Functions
def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def now_utc():
    return datetime.now(timezone.utc)

def format_dt(dt: datetime):
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")

def time_delta_str(future_dt: datetime):
    delta = future_dt - now_utc()
    seconds = int(delta.total_seconds())
    if seconds <= 0:
        return "0s"
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if seconds:
        parts.append(f"{seconds}s")
    return " ".join(parts)

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

# Session state
if "last_commit_hash" not in st.session_state:
    st.session_state["last_commit_hash"] = ""
if "last_preimage" not in st.session_state:
    st.session_state["last_preimage"] = ""
if "latest_commits" not in st.session_state:
    st.session_state["latest_commits"] = pd.DataFrame()
if "latest_reveals" not in st.session_state:
    st.session_state["latest_reveals"] = pd.DataFrame()

# Page config
st.set_page_config(page_title="Beauty Contest Game", page_icon="🎯", layout="wide")

# Inject light CSS for nicer cards
st.markdown(
    """
    <style>
    .big-title { font-size:30px; font-weight:700; margin:0; }
    .muted { color:#6c757d; }
    .phase-card { background:#ffffff; border-radius:10px; padding:18px; box-shadow:0 1px 6px rgba(0,0,0,0.06); }
    .small { font-size:13px; color:#6c757d; }
    .highlight { background:linear-gradient(90deg,#e7f5ff,#fff); padding:8px 12px; border-radius:8px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Top header
st.markdown(
    f"""
    <div style="display:flex; align-items:center; gap:16px;">
      <div style="font-size:56px; line-height:0">🎯</div>
      <div>
        <div class="big-title">Decentralized Beauty Contest Game</div>
        <div class="muted">Guess 2/3 of the average — commit secretly, reveal later. Secure with SHA-256 commitments.</div>
      </div>
      <div style="margin-left:auto; text-align:right;">
        <div class="small">Current UTC</div>
        <div style="font-weight:600;">{format_dt(now_utc())}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")  # spacing

# Sidebar with API and timeline
with st.sidebar:
    st.header("⚙️ Configuration")
    api_url = st.text_input("API URL", value=API_DEFAULT)
    st.markdown("---")

    current_time = now_utc()
    commit_open = current_time <= COMMIT_DEADLINE_UTC
    reveal_open = current_time >= REVEAL_OPEN_UTC

    st.subheader("⏰ Timeline")
    st.write(f"Commit deadline: **{format_dt(COMMIT_DEADLINE_UTC)}**")
    st.write(f"Reveal opens: **{format_dt(REVEAL_OPEN_UTC)}**")
    st.write("")
    if commit_open:
        st.success(f"Commits OPEN — closes in {time_delta_str(COMMIT_DEADLINE_UTC)}")
    else:
        st.error("Commits CLOSED")

    if reveal_open:
        st.success(f"Reveals OPEN")
    else:
        st.info(f"Reveals open in {time_delta_str(REVEAL_OPEN_UTC)}")

    st.markdown("---")
    st.caption("API URL and timeline are shown here for quick reference.")

# Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📝 Commit", "🔓 Reveal", "📊 Leaderboard", "ℹ️ Instructions"])

# TAB 1 - Commit
with tab1:
    st.header("📝 Commit Phase")
    cols = st.columns([3, 1])
    with cols[0]:
        st.markdown('<div class="phase-card">', unsafe_allow_html=True)
        if commit_open:
            st.info("Commit window is OPEN. Generate and submit your commitment before the deadline.")
        else:
            st.error("Commit window is CLOSED. You cannot submit commits now.")

        with st.form("commit_form", clear_on_submit=False):
            st.subheader("Create Commitment")
            c1, c2 = st.columns([2, 1])
            with c1:
                uni_id = st.text_input("University ID", help="Unique identifier (e.g., student ID)", key="commit_uni")
                number = st.number_input("Your chosen number (0-100)", min_value=0, max_value=100, value=50,
                                        help="Pick an integer between 0 and 100", key="commit_number")
                nonce = st.text_input("Secret Nonce", type="password", help="A secret string only you know", key="commit_nonce")
                nonce_confirm = st.text_input("Confirm Nonce", type="password", key="commit_nonce_confirm")
            with c2:
                st.markdown("#### Tips")
                st.write("- Use a long random nonce (e.g., s3cure-phrase-XYZ).")
                st.write("- After generating, download the preimage for safekeeping.")
                st.write("- You can generate first, then submit to server.")
            submit_commit = st.form_submit_button("Generate Commitment Hash", type="primary")
            if submit_commit:
                if not uni_id or not nonce:
                    st.error("❌ Please fill in all fields")
                elif nonce != nonce_confirm:
                    st.error("❌ Nonces don't match")
                elif not commit_open:
                    st.error("❌ Commit window is closed")
                else:
                    preimage = f"{uni_id}|{number}|{nonce}"
                    commit_hash = sha256(preimage)
                    st.session_state["last_preimage"] = preimage
                    st.session_state["last_commit_hash"] = commit_hash

                    st.success("✅ Commitment hash generated")
                    st.markdown('<div class="highlight">', unsafe_allow_html=True)
                    st.write("Commit Hash:")
                    st.code(commit_hash, language=None)
                    st.markdown('</div>', unsafe_allow_html=True)

                    with st.expander("Preimage & actions"):
                        st.write("Preimage (keep this safe):")
                        st.code(preimage, language=None)
                        st.download_button("⬇️ Download Preimage", preimage, file_name=f"preimage_{uni_id}.txt")
                        st.download_button("⬇️ Download Commit Hash", commit_hash, file_name=f"commit_{uni_id}.txt")
                        st.text_area("Commit Hash (copy)", value=commit_hash, height=60, key="commit_copy_area")

                    if st.button("📤 Submit to Server", key="commit_submit_server"):
                        with st.spinner("Submitting commit..."):
                            status, response = send_commit(api_url, uni_id, commit_hash)
                            if status:
                                st.success(f"✅ Server Response ({status}): {response}")
                            else:
                                st.error(f"❌ Error: {response}")

        st.markdown('</div>', unsafe_allow_html=True)

    with cols[1]:
        # summary card
        st.markdown('<div class="phase-card">', unsafe_allow_html=True)
        st.subheader("Quick Summary")
        st.write("• Commit before the deadline.")
        st.write("• Keep your nonce & number secret until reveal.")
        st.write("• Download preimage to avoid losing it.")
        if st.session_state["last_commit_hash"]:
            st.markdown("**Last Hash (this session):**")
            st.code(st.session_state["last_commit_hash"], language=None)
        st.markdown('</div>', unsafe_allow_html=True)

# TAB 2 - Reveal
with tab2:
    st.header("🔓 Reveal Phase")
    cols = st.columns([3, 1])
    with cols[0]:
        st.markdown('<div class="phase-card">', unsafe_allow_html=True)
        if reveal_open:
            st.success("Reveal window is OPEN. Submit your reveal now.")
        else:
            st.info("Reveal window not open yet. Wait for the reveal time.")

        with st.form("reveal_form"):
            st.subheader("Reveal Your Commitment")
            st.info("Enter exactly the same University ID, number, and nonce you used during commit.")
            r1, r2 = st.columns([2, 1])
            with r1:
                reveal_uni_id = st.text_input("University ID (same as commit)", key="reveal_uni")
                reveal_number = st.number_input("Number (same as commit)", min_value=0, max_value=100, value=50, key="reveal_number")
                reveal_nonce = st.text_input("Secret Nonce (same as commit)", type="password", key="reveal_nonce")
            with r2:
                st.markdown("#### Helpful")
                st.write("- If you used this session to generate preimage, it's shown below.")
                if st.session_state.get("last_preimage"):
                    st.write("Last generated preimage (read-only):")
                    st.text_area("Session preimage", value=st.session_state["last_preimage"], height=80, key="session_preimage_area")
            # preview hash
            if reveal_uni_id and reveal_nonce is not None:
                check_preimage = f"{reveal_uni_id}|{reveal_number}|{reveal_nonce}"
                check_hash = sha256(check_preimage)
                st.info(f"Commitment hash computed from your input: `{check_hash}`")
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

    with cols[1]:
        st.markdown('<div class="phase-card">', unsafe_allow_html=True)
        st.subheader("Reveal Checklist")
        st.write("• Ensure exact match with commit (number & nonce).")
        st.write("• If you lose the nonce, reveal is impossible.")
        st.write("• Use the preview hash to verify before submitting.")
        st.markdown('</div>', unsafe_allow_html=True)

# TAB 3 - Leaderboard / Results
with tab3:
    st.header("📊 Leaderboard & Results")

    top_cols = st.columns([2, 1])
    with top_cols[0]:
        st.subheader("Commit / Reveal Data")
        action_cols = st.columns(3)
        if action_cols[0].button("🔄 Refresh Commits"):
            commits_url = f"{api_url}?table=commits"
            commits = get_csv_data(commits_url)
            if commits:
                df_commits = pd.DataFrame(commits)
                st.session_state["latest_commits"] = df_commits
                st.success(f"Loaded {len(df_commits)} commits")
            else:
                st.info("No commits found")
        if action_cols[1].button("🔄 Refresh Reveals"):
            reveals_url = f"{api_url}?table=reveals"
            reveals = get_csv_data(reveals_url)
            if reveals:
                df_reveals = pd.DataFrame(reveals)
                st.session_state["latest_reveals"] = df_reveals
                st.success(f"Loaded {len(df_reveals)} reveals")
            else:
                st.info("No reveals found")
        if action_cols[2].button("📥 Clear Session Data"):
            st.session_state["latest_commits"] = pd.DataFrame()
            st.session_state["latest_reveals"] = pd.DataFrame()
            st.info("Cleared session-stored commit/reveal tables")

        # Show commits / reveals if present
        if not st.session_state["latest_commits"].empty:
            st.subheader("Commits (latest)")
            st.dataframe(st.session_state["latest_commits"], use_container_width=True, height=240)
        if not st.session_state["latest_reveals"].empty:
            st.subheader("Reveals (latest)")
            st.dataframe(st.session_state["latest_reveals"], use_container_width=True, height=240)

    with top_cols[1]:
        st.subheader("Quick Stats")
        if not st.session_state["latest_reveals"].empty:
            df = st.session_state["latest_reveals"].copy()
            df["number_int"] = pd.to_numeric(df.get("number", pd.Series()), errors="coerce")
            valid_numbers = df["number_int"].dropna().astype(int).tolist()
            if valid_numbers:
                avg = mean(valid_numbers)
                target = K_FACTOR * avg
                st.metric("Participants (reveals)", len(valid_numbers))
                st.metric("Average", f"{avg:.2f}")
                st.metric("Target (2/3 × avg)", f"{target:.2f}")
            else:
                st.write("No valid numeric reveals yet.")
        else:
            st.write("Refresh reveals to view stats.")

    st.markdown("---")

    # distribution chart
    if not st.session_state["latest_reveals"].empty:
        df = st.session_state["latest_reveals"].copy()
        df["number_int"] = pd.to_numeric(df.get("number", pd.Series()), errors="coerce")
        counts = df["number_int"].dropna().astype(int).value_counts().sort_index()
        if not counts.empty:
            st.subheader("Reveal Distribution")
            st.bar_chart(counts)

    # Calculate winners
    st.markdown("")
    if st.button("🏆 Calculate Winners", type="primary"):
        with st.spinner("Calculating results..."):
            commits_data = get_csv_data(f"{api_url}?table=commits")
            reveals_data = get_csv_data(f"{api_url}?table=reveals")

            if not reveals_data:
                st.warning("No reveals available to calculate winners")
            else:
                valid_numbers = []
                parsed = []
                for reveal in reveals_data:
                    try:
                        num = int(reveal.get("number", ""))
                        if 0 <= num <= 100:
                            valid_numbers.append(num)
                            parsed.append({"uni_id": reveal.get("uni_id", ""), "number": num, "nonce": reveal.get("nonce", "")})
                    except:
                        continue

                if valid_numbers:
                    avg = mean(valid_numbers)
                    target = K_FACTOR * avg
                    st.success("✅ Results ready")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Participants", len(valid_numbers))
                    c2.metric("Average", f"{avg:.2f}")
                    c3.metric("Target (2/3 × avg)", f"{target:.2f}")

                    results_df = pd.DataFrame(parsed)
                    results_df["distance"] = (results_df["number"] - target).abs()
                    results_df = results_df.sort_values("distance").reset_index(drop=True)
                    results_df.index += 1
                    results_df.index.name = "Rank"

                    st.subheader("Top 10 Closest")
                    st.table(results_df.head(10)[["number", "distance", "uni_id"]])

                    st.markdown("Full results (sorted by closeness):")
                    st.dataframe(results_df, use_container_width=True)
                else:
                    st.warning("No valid numeric reveals found to compute results.")

# TAB 4 - Instructions
with tab4:
    st.header("ℹ️ How to Play & Notes")
    st.markdown("""
    - Each player chooses a number between 0 and 100.
    - The target is 2/3 of the average of all revealed numbers.
    - Closest to the target wins.

    Phase summary:
    1) Commit before deadline: generate hash sha256("uni_id|number|nonce") and submit the hash.
    2) Reveal after deadline: provide uni_id, number, and nonce so the server can verify your previous commit.
    3) Results computed from valid reveals; closest distances win.

    Tips:
    - Save your preimage (download it using the buttons after generating).
    - Exact match is required: the number and nonce must match the commit.
    - If you lose the nonce, you cannot reveal.
    """)

st.markdown("---")
st.caption("🎮 Decentralized Beauty Contest Game | Built with Streamlit")