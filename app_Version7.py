"""
Streamlit Frontend for Decentralized Beauty Contest Game
Run with: streamlit run app.py
"""

import streamlit as st
import hashlib
import requests
import csv
import io
import time
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

# Accessible color palette and improved glass styling (fixed contrast)
st.markdown(
    """
    <style>
    :root{
      --accent:#0b5cff;           /* bright blue for important text */
      --muted:#243b53;           /* darker slate for secondary text (improved contrast) */
      --card-bg: rgba(255,255,255,0.82);
      --glass-dark: rgba(4,26,43,0.82);
      --glass-light: rgba(255,255,255,0.10);
      --success:#0f9d58;
      --danger:#d63031;
      --mono: 'Courier New', monospace;
    }
    .stApp {
      background: linear-gradient(180deg,#f7fbff 0%, #ffffff 60%);
      color: #072033;
      font-family: Inter, system-ui, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    }
    .header-row { display:flex; align-items:center; gap:16px; margin-bottom:8px; }
    .title { font-size:30px; font-weight:800; color:var(--accent); margin:0; }
    .subtitle { color:var(--muted); margin-top:2px; font-size:14px; }
    .card { background: var(--card-bg); border-radius:12px; padding:18px; box-shadow: 0 8px 24px rgba(8,15,30,0.06); border:1px solid rgba(11,34,60,0.04); }
    .glass-code { background: linear-gradient(180deg, rgba(6,18,32,0.9), rgba(10,30,60,0.85)); color: #eaf5ff; border-radius:10px; padding:12px; font-family: var(--mono); font-size:13px; overflow-x:auto; border:1px solid rgba(255,255,255,0.06); box-shadow: 0 6px 20px rgba(2,6,23,0.18); }
    .muted-small { color:var(--muted); font-size:13px; }
    .badge { display:inline-block; padding:6px 10px; border-radius:999px; font-weight:700; color:white; background:var(--accent); }
    .success-badge { background: var(--success); }
    .danger-badge { background: var(--danger); }
    .tip { background: linear-gradient(90deg,#f0f8ff,#ffffff); border-radius:8px; padding:8px 12px; color:#08203a; border:1px solid rgba(4,26,43,0.04); }
    .countdown-badge { display:inline-block; padding:8px 12px; border-radius:10px; font-weight:700; color: #041223; background: linear-gradient(90deg,#ffd54a,#ffb347); }
    /* ensure all text in card is visible on card bg */
    .card * { color: #072033 !important; }
    /* make glass-code text clearly visible */
    .glass-code pre { color: #eaf5ff !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Top header
st.markdown(
    f"""
    <div class="header-row">
      <div style="font-size:46px">🎯</div>
      <div style="flex:1">
        <div class="title">Decentralized Beauty Contest Game</div>
        <div class="subtitle">Guess 2/3 of the average — commit secretly, reveal later. SHA-256 commitments.</div>
      </div>
      <div style="text-align:right">
        <div class="muted-small">Current UTC</div>
        <div style="font-weight:700">{format_dt(now_utc())}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")  # spacing

# Sidebar: configuration & timeline with countdown placeholders (JS + server fallback)
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

    # Animated countdowns via JS (best-effort). We include ISO datetimes for the script to read.
    # Also provide a server-side live option (safe fallback)
    st.markdown(
        f"""
        <div style="margin-bottom:8px;">
          <div style="font-weight:700">Commit countdown</div>
          <div id="commit-countdown" class="countdown-badge">--:--:--</div>
        </div>
        <div style="margin-bottom:8px;">
          <div style="font-weight:700">Reveal countdown</div>
          <div id="reveal-countdown" class="countdown-badge">--:--:--</div>
        </div>

        <script>
        (function() {{
          function pad(n) {{ return n < 10 ? '0'+n : n; }}
          const commitDeadline = new Date("{COMMIT_DEADLINE_UTC.isoformat()}");
          const revealOpen = new Date("{REVEAL_OPEN_UTC.isoformat()}");
          function updateOnce(id, target) {{
            const el = document.getElementById(id);
            if(!el) return;
            const now = new Date();
            let diff = Math.floor((target - now) / 1000);
            if(diff <= 0) {{
              el.textContent = "00:00:00";
              return;
            }}
            const d = Math.floor(diff / 86400);
            diff %= 86400;
            const h = Math.floor(diff / 3600);
            diff %= 3600;
            const m = Math.floor(diff / 60);
            const s = diff % 60;
            let out = "";
            if(d > 0) out += d + "d ";
            out += pad(h) + ":" + pad(m) + ":" + pad(s);
            el.textContent = out;
          }}
          function tick() {{
            updateOnce("commit-countdown", commitDeadline);
            updateOnce("reveal-countdown", revealOpen);
          }}
          // run immediately then every second
          tick();
          setInterval(tick, 1000);
        }})();
        </script>
        """,
        unsafe_allow_html=True,
    )

    st.write("")
    # Server-side live countdown fallback (user may enable; updates UI via Python loop for limited time)
    live_count = st.checkbox("Enable server live countdown (updates in-stream for 120s)", key="server_countdown_toggle")
    if live_count:
        placeholder_commit = st.empty()
        placeholder_reveal = st.empty()
        # limit to 120 seconds to avoid long blocking on server
        for _ in range(120):
            placeholder_commit.markdown(f"**Commit:** {time_delta_str(COMMIT_DEADLINE_UTC)}")
            placeholder_reveal.markdown(f"**Reveal:** {time_delta_str(REVEAL_OPEN_UTC)}")
            time.sleep(1)

    st.markdown("---")
    # show status badges
    if commit_open:
        st.markdown(f"<div style='margin-bottom:6px;'>{'<span class=\"badge\">Commits OPEN</span>'} <span class='muted-small'>closes in {time_delta_str(COMMIT_DEADLINE_UTC)}</span></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='badge danger-badge'>Commits CLOSED</div>", unsafe_allow_html=True)

    if reveal_open:
        st.markdown(f"<div class='badge success-badge' style='margin-top:6px;'>Reveals OPEN</div>", unsafe_allow_html=True)
    st.markdown("---")
    st.caption("API and timeline shown here. Colors and contrast adjusted for visibility.")

# Tabs: reveal-mode (only the active tab content displays)
tab_commit, tab_reveal, tab_board, tab_info = st.tabs(["📝 Commit", "🔓 Reveal", "📊 Leaderboard", "ℹ️ Instructions"])

# TAB: Commit
with tab_commit:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📝 Commit Phase")
    if commit_open:
        st.info("Commit window is OPEN. Generate your commitment and submit before the deadline.")
    else:
        st.error("Commit window is CLOSED. You can still generate and download your preimage locally.")

    with st.form("commit_form_tab", clear_on_submit=False):
        uni = st.text_input("University ID", help="Your unique identifier", key="commit_uni_tab_v3")
        num = st.number_input("Choose your number (0-100)", min_value=0, max_value=100, value=50, key="commit_num_tab_v3")
        nonce = st.text_input("Secret Nonce", type="password", help="A secret string only you know", key="commit_nonce_tab_v3")
        nonce_conf = st.text_input("Confirm Nonce", type="password", key="commit_nonce_confirm_tab_v3")
        generate = st.form_submit_button("✨ Generate Commitment Hash")

    # Generate action handled after form submit
    if generate:
        uni_s = (uni or "").strip()
        num_s = num
        nonce_s = nonce or ""
        if not uni_s or nonce_s == "":
            st.error("❌ Please fill in all fields")
        elif nonce_s != (nonce_conf or ""):
            st.error("❌ Nonces don't match")
        else:
            preimage = f"{uni_s}|{num_s}|{nonce_s}"
            commit_hash = sha256(preimage)
            st.session_state["last_preimage"] = preimage
            st.session_state["last_commit_hash"] = commit_hash
            st.success("✅ Commitment hash generated")

    # Show commit hash / preimage in glass panel if present
    if st.session_state.get("last_commit_hash"):
        st.markdown("<div style='margin-top:12px'><strong>Commit Hash</strong></div>", unsafe_allow_html=True)
        st.markdown(f"<div class='glass-code'><pre>{st.session_state['last_commit_hash']}</pre></div>", unsafe_allow_html=True)

        # copy buffer and downloads
        cp1, cp2 = st.columns([1, 1])
        if cp1.button("📋 Copy Hash to Buffer", key="commit_copy_buf_v3"):
            st.success("Hash placed into copy buffer. Use Ctrl/Cmd+C to copy from textarea below.")
            st.text_area("Hash copy buffer", value=st.session_state["last_commit_hash"], height=80, key="commit_hash_buffer_v3")
        if cp2.download_button("📥 Download Commit Hash", st.session_state["last_commit_hash"], file_name="commit_hash.txt", key="commit_dl_hash_v3"):
            pass
        with st.expander("Preimage (KEEP THIS SAFE) — Download recommended"):
            st.markdown(f"<div class='glass-code'><pre>{st.session_state.get('last_preimage','')}</pre></div>", unsafe_allow_html=True)
            if st.session_state.get("last_preimage"):
                st.download_button("⬇️ Download Preimage", st.session_state["last_preimage"], file_name="preimage.txt", key="commit_dl_preimage_v3")

    # Submit to server (outside form)
    if st.button("📤 Submit Commitment to Server", key="commit_submit_tab_v3"):
        if not st.session_state.get("last_commit_hash"):
            st.error("Generate a commit hash first")
        elif not commit_open:
            st.error("Commit window is closed. Cannot submit.")
        else:
            pre = st.session_state.get("last_preimage", "")
            uni_for_submit = ""
            if pre:
                parts = pre.split("|")
                if len(parts) >= 1:
                    uni_for_submit = parts[0]
            if not uni_for_submit:
                st.error("Could not determine University ID from preimage. Enter and submit manually.")
            else:
                with st.spinner("Submitting commit..."):
                    status, response = send_commit(api_url, uni_for_submit, st.session_state["last_commit_hash"])
                    if status:
                        st.success(f"✅ Server Response ({status}): {response}")
                    else:
                        st.error(f"❌ Error: {response}")

    st.markdown('</div>', unsafe_allow_html=True)

# TAB: Reveal
with tab_reveal:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("🔓 Reveal Phase")
    if reveal_open:
        st.success("Reveal window is OPEN. Submit your reveal now.")
    else:
        st.info("Reveal window not open yet. Prepare your preimage and be ready to reveal.")

    with st.form("reveal_form_tab_v3"):
        r_uni = st.text_input("University ID (same as commit)", key="reveal_uni_tab_v3")
        r_num = st.number_input("Your number (same as commit)", min_value=0, max_value=100, value=50, key="reveal_num_tab_v3")
        r_nonce = st.text_input("Secret Nonce (same as commit)", type="password", key="reveal_nonce_tab_v3")
        preview_hash_cb = st.checkbox("Preview computed hash from these inputs", key="reveal_preview_tab_v3")
        reveal_submit = st.form_submit_button("🔓 Reveal Commitment")

    # Show preview if requested
    if preview_hash_cb:
        r_uni_v = st.session_state.get("reveal_uni_tab_v3", "")
        r_num_v = st.session_state.get("reveal_num_tab_v3", 50)
        r_nonce_v = st.session_state.get("reveal_nonce_tab_v3", "")
        if r_uni_v and r_nonce_v is not None:
            check_pre = f"{r_uni_v}|{r_num_v}|{r_nonce_v}"
            st.markdown("<div class='tip'>Computed hash from these reveal inputs:</div>", unsafe_allow_html=True)
            st.code(sha256(check_pre), language=None)

    if reveal_submit:
        r_uni_s = (r_uni or "").strip()  # r_uni from form variable above may be stale; use session for reliability
        # use session state values which were set during form
        r_uni_s = st.session_state.get("reveal_uni_tab_v3", "").strip()
        r_num_s = st.session_state.get("reveal_num_tab_v3", 50)
        r_nonce_s = st.session_state.get("reveal_nonce_tab_v3", "")
        if not r_uni_s or r_nonce_s == "":
            st.error("❌ Please fill in all fields")
        elif not reveal_open:
            st.error("❌ Reveal window is not open yet!")
        else:
            with st.spinner("Submitting reveal..."):
                status, response = send_reveal(api_url, r_uni_s, r_num_s, r_nonce_s)
                if status:
                    st.success(f"✅ Server Response ({status}): {response}")
                    st.balloons()
                else:
                    st.error(f"❌ Error: {response}")

    # Show last generated preimage (read-only)
    if st.session_state.get("last_preimage"):
        st.markdown("Session preimage (read-only):")
        st.markdown(f"<div class='glass-code'><pre>{st.session_state['last_preimage']}</pre></div>", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# TAB: Leaderboard
with tab_board:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("📊 Leaderboard & Current Status")

    refresh_cols = st.columns([1,1,1])
    if refresh_cols[0].button("🔄 Refresh Commits", key="board_refresh_commits_v3"):
        commits = get_csv_data(f"{api_url}?table=commits")
        if commits:
            st.session_state["latest_commits"] = pd.DataFrame(commits)
            st.success(f"Loaded {len(st.session_state['latest_commits'])} commits")
        else:
            st.info("No commits found")

    if refresh_cols[1].button("🔄 Refresh Reveals", key="board_refresh_reveals_v3"):
        reveals = get_csv_data(f"{api_url}?table=reveals")
        if reveals:
            st.session_state["latest_reveals"] = pd.DataFrame(reveals)
            st.success(f"Loaded {len(st.session_state['latest_reveals'])} reveals")
        else:
            st.info("No reveals found")

    if refresh_cols[2].button("📥 Export Reveals CSV", key="board_export_reveals_v3"):
        if not st.session_state["latest_reveals"].empty:
            csv_data = st.session_state["latest_reveals"].to_csv(index=False)
            st.download_button("Download reveals.csv", csv_data, file_name="reveals.csv", key="board_dl_reveals_v3")
        else:
            st.info("No reveals to export")

    st.markdown("---")

    if not st.session_state["latest_commits"].empty:
        st.subheader("Commits (cached)")
        st.dataframe(st.session_state["latest_commits"], use_container_width=True, height=240)
    else:
        st.info("No commits cached — click 'Refresh Commits'")

    if not st.session_state["latest_reveals"].empty:
        st.subheader("Reveals (cached)")
        st.dataframe(st.session_state["latest_reveals"], use_container_width=True, height=240)
    else:
        st.info("No reveals cached — click 'Refresh Reveals'")

    st.markdown("---")

    # Quick stats if reveals present
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
            if st.button("📈 Show Distribution Chart", key="board_show_dist_v3"):
                counts = pd.Series(valid_numbers).value_counts().sort_index()
                st.bar_chart(counts)

    # Calculate winners
    if st.button("🏆 Calculate Winners", key="board_calc_winners_v3"):
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
                m1, m2, m3 = st.columns(3)
                m1.metric("Participants", len(valid_numbers))
                m2.metric("Average", f"{avg:.2f}")
                m3.metric("Target (2/3 × avg)", f"{target:.2f}")

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

# TAB: Instructions
with tab_info:
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("ℹ️ How to Play")
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
    st.markdown('</div>', unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("🎮 Decentralized Beauty Contest Game | Built with Streamlit")