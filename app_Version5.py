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

# Session state initialization
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

# CSS (glass theme, cards)
st.markdown(
    """
    <style>
    .stApp { background: linear-gradient(180deg, #f7fbff 0%, #ffffff 40%, #fbf7ff 100%); }
    .big-title { font-size:28px; font-weight:800; margin:0; }
    .muted { color:#61748b; margin-top:4px; }
    .card { background: rgba(255,255,255,0.6); border-radius:12px; padding:18px; box-shadow: 0 6px 20px rgba(15,23,42,0.08); border: 1px solid rgba(255,255,255,0.5); backdrop-filter: blur(6px); }
    .glass-code { background: rgba(255,255,255,0.12); border-radius:10px; padding:14px; color: #0b2b4a; font-family: monospace; overflow-x: auto; border: 1px solid rgba(255,255,255,0.14); backdrop-filter: blur(8px) saturate(130%); }
    .tip { background: linear-gradient(90deg,#f0f8ff,#ffffff); border-radius:8px; padding:8px 12px; color:#0b2545; border:1px solid rgba(4,26,43,0.04); }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header
st.markdown(
    f"""
    <div style="display:flex; align-items:center; gap:16px;">
      <div style="font-size:56px; line-height:0">🎯</div>
      <div style="flex:1">
        <div class="big-title">Decentralized Beauty Contest Game</div>
        <div class="muted">Secure commit-reveal with SHA-256 — guess 2/3 of the average.</div>
      </div>
      <div style="text-align:right;">
        <div style="font-size:12px; color:#58677b;">UTC</div>
        <div style="font-weight:600;">{format_dt(now_utc())}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")

# Sidebar config
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
        st.success("Reveals OPEN")
    else:
        st.info(f"Reveals open in {time_delta_str(REVEAL_OPEN_UTC)}")
    st.markdown("---")
    st.caption("API URL and timeline are shown here for quick reference.")

# Main layout: left actions, right live controls
left_col, right_col = st.columns([3, 1])

# LEFT: actions
with left_col:
    # Commit and Reveal cards side-by-side
    commit_card, reveal_card = st.columns(2)

    # Commit Card
    with commit_card:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("📝 Commit")
        if commit_open:
            st.info("Commit window is OPEN. Generate and submit your commitment hash.")
        else:
            st.error("Commit window is CLOSED. You can still generate and download your preimage locally.")

        # Generate form: only content + form_submit_button
        with st.form("commit_generate_form", clear_on_submit=False):
            c_uni = st.text_input("University ID", help="Unique identifier", key="commit_uni_v2")
            c_number = st.number_input("Number (0-100)", min_value=0, max_value=100, value=50, key="commit_number_v2")
            c_nonce = st.text_input("Secret Nonce", type="password", help="Keep this secret", key="commit_nonce_v2")
            c_nonce_confirm = st.text_input("Confirm Nonce", type="password", key="commit_nonce_confirm_v2")
            generated = st.form_submit_button("✨ Generate Commitment Hash")
            if generated:
                if not c_uni or not c_nonce:
                    st.error("❌ Please fill in all fields")
                elif c_nonce != c_nonce_confirm:
                    st.error("❌ Nonces don't match")
                else:
                    preimage = f"{c_uni}|{c_number}|{c_nonce}"
                    commit_hash = sha256(preimage)
                    st.session_state["last_preimage"] = preimage
                    st.session_state["last_commit_hash"] = commit_hash
                    st.success("✅ Commitment generated")

        # Show commit hash and downloads outside the form (operate on session_state)
        if st.session_state.get("last_commit_hash"):
            st.markdown("Commit Hash")
            st.markdown(f'<div class="glass-code"><pre>{st.session_state["last_commit_hash"]}</pre></div>', unsafe_allow_html=True)

            # Copy buffer and download
            if st.button("📋 Copy Hash to Buffer", key="copy_hash_btn"):
                st.success("Hash placed into copy buffer below. Use Ctrl/Cmd+C to copy.")
                st.text_area("Hash copy buffer", value=st.session_state["last_commit_hash"], height=80, key="hash_copy_buffer")

            if st.download_button("📥 Download Commit Hash", st.session_state["last_commit_hash"], file_name=f"commit_hash.txt", key="download_hash"):
                pass  # download provided by streamlit

            with st.expander("Preimage (KEEP SAFE)"):
                st.markdown(f'<div class="glass-code"><pre>{st.session_state.get("last_preimage","")}</pre></div>', unsafe_allow_html=True)
                if st.session_state.get("last_preimage"):
                    st.download_button("⬇️ Download Preimage", st.session_state["last_preimage"], file_name=f"preimage.txt", key="download_preimage")

        # Submit to server: separate action (outside generate form)
        if st.button("📤 Submit Commit to Server", key="submit_commit_server_v2"):
            if not st.session_state.get("last_commit_hash"):
                st.error("Generate a commit hash first")
            elif not commit_open:
                st.error("Commit window is closed. Cannot submit.")
            else:
                # attempt to derive uni_id from preimage for submission (if available)
                pre = st.session_state.get("last_preimage", "")
                uni_for_submit = ""
                if pre:
                    # pre format uni|number|nonce
                    parts = pre.split("|")
                    if len(parts) >= 1:
                        uni_for_submit = parts[0]
                if not uni_for_submit:
                    st.error("Could not determine University ID from preimage. Enter and submit manually using the form.")
                else:
                    with st.spinner("Submitting commit..."):
                        status, response = send_commit(api_url, uni_for_submit, st.session_state["last_commit_hash"])
                        if status:
                            st.success(f"✅ Server Response ({status}): {response}")
                        else:
                            st.error(f"❌ Error: {response}")

        st.markdown('</div>', unsafe_allow_html=True)

    # Reveal Card
    with reveal_card:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("🔓 Reveal")
        if reveal_open:
            st.success("Reveal window is OPEN. Submit your reveal now.")
        else:
            st.info("Reveal window not open yet. Prepare your preimage for later.")

        # Reveal form
        with st.form("reveal_form_v2"):
            r_uni = st.text_input("University ID", key="reveal_uni_v2")
            r_num = st.number_input("Number (0-100)", min_value=0, max_value=100, value=50, key="reveal_number_v2")
            r_nonce = st.text_input("Secret Nonce", type="password", key="reveal_nonce_v2")
            preview = st.checkbox("Preview computed hash", key="reveal_preview_cb")
            if preview and r_uni and r_nonce:
                check_preimage = f"{r_uni}|{r_num}|{r_nonce}"
                check_hash = sha256(check_preimage)
                st.markdown('<div class="tip">', unsafe_allow_html=True)
                st.write("Computed hash from your reveal inputs:")
                st.code(check_hash, language=None)
                st.markdown('</div>', unsafe_allow_html=True)
            reveal_submit = st.form_submit_button("🔓 Submit Reveal")
            if reveal_submit:
                if not r_uni or not r_nonce:
                    st.error("❌ Please fill in all fields")
                elif not reveal_open:
                    st.error("❌ Reveal window is not open yet!")
                else:
                    with st.spinner("Submitting reveal..."):
                        status, response = send_reveal(api_url, r_uni, r_num, r_nonce)
                        if status:
                            st.success(f"✅ Server Response ({status}): {response}")
                            st.balloons()
                        else:
                            st.error(f"❌ Error: {response}")

        st.markdown('</div>', unsafe_allow_html=True)

    # Quick Flow card
    st.write("")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### 🚦 Quick Flow")
    f1, f2, f3, f4 = st.columns(4)
    if f1.button("1️⃣ Commit", key="flow_commit"):
        st.info("Generate your hash, download preimage, and submit before the deadline.")
    if f2.button("2️⃣ Wait", key="flow_wait"):
        st.info("Wait until reveal opens. Keep nonce secret.")
    if f3.button("3️⃣ Reveal", key="flow_reveal"):
        st.info("Reveal number & nonce to verify your commit.")
    if f4.button("🏆 Results", key="flow_results"):
        st.info("Organizers compute winners from verified reveals.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Small preview leaderboard
    st.write("")
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📌 Quick Leaderboard Preview")
    if not st.session_state["latest_reveals"].empty:
        dfp = st.session_state["latest_reveals"].copy()
        dfp["number_int"] = pd.to_numeric(dfp.get("number", pd.Series()), errors="coerce")
        dfp = dfp.dropna(subset=["number_int"])
        if not dfp.empty:
            dfp["distance_preview"] = (dfp["number_int"] - (K_FACTOR * dfp["number_int"].mean())).abs()
            dfp = dfp.sort_values("distance_preview")
            st.table(dfp.head(5)[["uni_id", "number", "distance_preview"]].rename(columns={"distance_preview":"dist"}))
        else:
            st.write("No numeric reveals")
    else:
        st.write("Refresh reveals on the right to populate.")
    st.markdown('</div>', unsafe_allow_html=True)

# RIGHT: live controls & stats
with right_col:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Live Controls")
    if st.button("🔄 Refresh Commits", key="refresh_commits_v2"):
        commits_url = f"{api_url}?table=commits"
        commits = get_csv_data(commits_url)
        if commits:
            st.session_state["latest_commits"] = pd.DataFrame(commits)
            st.success(f"Loaded {len(st.session_state['latest_commits'])} commits")
        else:
            st.info("No commits found")

    if st.button("🔄 Refresh Reveals", key="refresh_reveals_v2"):
        reveals_url = f"{api_url}?table=reveals"
        reveals = get_csv_data(reveals_url)
        if reveals:
            st.session_state["latest_reveals"] = pd.DataFrame(reveals)
            st.success(f"Loaded {len(st.session_state['latest_reveals'])} reveals")
        else:
            st.info("No reveals found")

    if st.button("📥 Export Reveals CSV", key="export_reveals_v2"):
        if not st.session_state["latest_reveals"].empty:
            csv_data = st.session_state["latest_reveals"].to_csv(index=False)
            st.download_button("Download reveals.csv", csv_data, file_name="reveals.csv", key="dl_reveals_csv")
        else:
            st.info("No reveals to export")

    st.markdown("---")
    st.subheader("Stats")
    if not st.session_state["latest_reveals"].empty:
        df = st.session_state["latest_reveals"].copy()
        df["number_int"] = pd.to_numeric(df.get("number", pd.Series()), errors="coerce")
        valid_numbers = df["number_int"].dropna().astype(int).tolist()
        if valid_numbers:
            avg = mean(valid_numbers)
            target = K_FACTOR * avg
            st.metric("Participants (revealed)", len(valid_numbers))
            st.metric("Average", f"{avg:.2f}")
            st.metric("Target (2/3 × avg)", f"{target:.2f}")
            if st.button("📈 Show Distribution Chart", key="show_dist_v2"):
                counts = pd.Series(valid_numbers).value_counts().sort_index()
                st.bar_chart(counts)
        else:
            st.write("No valid numeric reveals yet.")
    else:
        st.write("Refresh reveals to show stats.")
    st.markdown('</div>', unsafe_allow_html=True)

# Results area
st.write("")
st.markdown('<div class="card">', unsafe_allow_html=True)
st.header("📊 Results & Calculation")

if st.button("🏆 Calculate Winners", key="calc_winners_v2"):
    with st.spinner("Calculating results..."):
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
st.markdown('</div>', unsafe_allow_html=True)

# Collapsed instructions
with st.expander("ℹ️ How to Play & Notes (expand)"):
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