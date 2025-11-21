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

# Configuration
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

# Initialize session state for convenience
if "last_commit_hash" not in st.session_state:
    st.session_state["last_commit_hash"] = ""
if "last_preimage" not in st.session_state:
    st.session_state["last_preimage"] = ""

# Page Configuration
st.set_page_config(
    page_title="Beauty Contest Game",
    page_icon="🎯",
    layout="wide"
)

# Top Banner
st.markdown(
    f"""
    <div style="display:flex; align-items:center; gap:12px;">
      <div style="font-size:48px">🎯</div>
      <div>
        <h1 style="margin:0">Decentralized Beauty Contest Game</h1>
        <div style="color:gray">Guess 2/3 of the average. Commit before the deadline, reveal after.</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.write("")  # spacing

# Sidebar for API Configuration and Timeline
with st.sidebar:
    st.header("⚙️ Configuration")
    api_url = st.text_input("API URL", value=API_DEFAULT)

    st.markdown("---")

    st.subheader("⏰ Game Timeline")
    current_time = now_utc()

    commit_open = current_time <= COMMIT_DEADLINE_UTC
    reveal_open = current_time >= REVEAL_OPEN_UTC

    st.write(f"**Current Time (UTC):**")
    st.code(format_dt(current_time), language=None)

    col_a, col_b = st.columns(2)
    col_a.metric("Commit Deadline", format_dt(COMMIT_DEADLINE_UTC))
    col_b.metric("Reveal Opens", format_dt(REVEAL_OPEN_UTC))

    st.markdown("")
    if commit_open:
        st.success("✅ Commits OPEN")
    else:
        st.error("❌ Commits CLOSED")

    if reveal_open:
        st.success("✅ Reveals OPEN")
    else:
        st.info("⏳ Reveals NOT OPEN")

    st.markdown("---")
    st.caption("API URL and timeline live in the sidebar for quick access.")

# Main Content Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📝 Commit", "🔓 Reveal", "📊 Leaderboard", "ℹ️ Instructions"])

# TAB 1: COMMIT PHASE
with tab1:
    st.header("📝 Commit Phase")
    st.write("Create a secret commitment of your chosen number. Keep your nonce safe!")

    if commit_open:
        st.info("Commit window is OPEN. Submit before the deadline.")
    else:
        st.error("⛔ The commit window is CLOSED. Deadline has passed.")

    with st.form("commit_form", clear_on_submit=False):
        st.subheader("Generate Commitment")
        c1, c2 = st.columns([2, 1])

        with c1:
            uni_id = st.text_input("University ID", help="Your unique identifier", key="commit_uni")
            number = st.number_input("Choose your number", min_value=0, max_value=100, value=50,
                                    help="Pick a number between 0 and 100", key="commit_number")
            nonce = st.text_input("Secret Nonce", type="password",
                                  help="A secret string only you know. SAVE THIS!", key="commit_nonce")
            nonce_confirm = st.text_input("Confirm Nonce", type="password", key="commit_nonce_confirm")

        with c2:
            st.markdown("### Quick Tips")
            st.write("- Use a random long nonce (e.g., `s3cure-phrase-123!`).")
            st.write("- Save the preimage and hash somewhere safe.")
            st.write("- You can generate and then submit to server in one flow.")

        submit_commit = st.form_submit_button("Generate Commitment Hash", type="primary")

        if submit_commit:
            if not uni_id or not nonce:
                st.error("❌ Please fill in all fields")
            elif nonce != nonce_confirm:
                st.error("❌ Nonces don't match!")
            elif not commit_open:
                st.error("❌ Commit window is closed!")
            else:
                preimage = f"{uni_id}|{number}|{nonce}"
                commit_hash = sha256(preimage)

                # store in session for use by submit button
                st.session_state["last_commit_hash"] = commit_hash
                st.session_state["last_preimage"] = preimage

                st.success("✅ Commitment hash generated!")
                st.write("Copy or save this data. You'll need it to reveal later.")
                st.code(commit_hash, language=None)

                with st.expander("Commit Summary (expand to copy)"):
                    st.write("Preimage (KEEP THIS SAFE):")
                    st.code(preimage, language=None)
                    st.write("Commit Hash:")
                    st.code(commit_hash, language=None)
                    st.write("If you'd like to copy the hash, click the textbox and use Ctrl/Cmd+C.")
                    st.text_area("Commit Hash (select to copy)", value=commit_hash, height=50, key="copy_commit_hash")

                # Submit to server button placed after generation so user can confirm
                if st.button("📤 Submit to Server", key="submit_commit_server"):
                    with st.spinner("Submitting..."):
                        status, response = send_commit(api_url, uni_id, commit_hash)
                        if status:
                            st.success(f"✅ Server Response ({status}): {response}")
                        else:
                            st.error(f"❌ Error: {response}")

# TAB 2: REVEAL PHASE
with tab2:
    st.header("🔓 Reveal Phase")
    st.write("After the deadline, reveal your original number and nonce to verify your commitment.")

    if not reveal_open:
        st.warning("⏳ The reveal window is NOT open yet. Wait until after the deadline.")
    else:
        st.success("✅ Reveal window is OPEN. You can now reveal your commitment!")

    with st.form("reveal_form"):
        st.subheader("Reveal Your Commitment")
        st.info("Enter EXACTLY what you committed during the commit phase")

        col1, col2 = st.columns(2)

        with col1:
            reveal_uni_id = st.text_input("University ID (same as commit)", key="reveal_uni")
            reveal_number = st.number_input("Your number (same as commit)", min_value=0, max_value=100,
                                           value=50, key="reveal_number")
            reveal_nonce = st.text_input("Your secret nonce (same as commit)", type="password",
                                         key="reveal_nonce")

        with col2:
            st.markdown("### Helpful Tools")
            st.write("- If you generated a commit here in this session, the app shows expected hash below.")
            if st.session_state.get("last_preimage"):
                st.write("Last preimage generated in this session (hidden):")
                st.text_area("Last Preimage (do not edit)", value=st.session_state["last_preimage"], height=80, key="session_preimage")

        # Show what hash this would produce
        if reveal_uni_id and reveal_nonce is not None:
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

# TAB 3: LEADERBOARD
with tab3:
    st.header("📊 Current Status & Results")

    left, right = st.columns([2, 1])

    with left:
        st.subheader("Commit and Reveal Data")
        commits_btn, reveals_btn, calc_btn = st.columns(3)
        if commits_btn.button("🔄 Refresh Commits"):
            commits_url = f"{api_url}?table=commits"
            commits = get_csv_data(commits_url)
            if commits:
                df_commits = pd.DataFrame(commits)
                st.session_state["latest_commits"] = df_commits
                st.dataframe(df_commits, use_container_width=True)
                st.caption(f"Total commits: {len(df_commits)}")
            else:
                st.info("No commits yet")

        if reveals_btn.button("🔄 Refresh Reveals"):
            reveals_url = f"{api_url}?table=reveals"
            reveals = get_csv_data(reveals_url)
            if reveals:
                df_reveals = pd.DataFrame(reveals)
                st.session_state["latest_reveals"] = df_reveals
                st.dataframe(df_reveals, use_container_width=True)
                st.caption(f"Total reveals: {len(df_reveals)}")
            else:
                st.info("No reveals yet")

        st.markdown("---")

        # Show a quick distribution chart if reveals are present in session
        if "latest_reveals" in st.session_state and not st.session_state["latest_reveals"].empty:
            df = st.session_state["latest_reveals"].copy()
            # Ensure numeric
            df["number_int"] = pd.to_numeric(df.get("number", pd.Series()), errors="coerce")
            counts = df["number_int"].dropna().astype(int).value_counts().sort_index()
            if not counts.empty:
                st.subheader("Reveal Distribution")
                st.bar_chart(counts)

    with right:
        st.subheader("Quick Stats")
        # show participants / averages if reveals present
        if "latest_reveals" in st.session_state and not st.session_state["latest_reveals"].empty:
            df = st.session_state["latest_reveals"].copy()
            df["number_int"] = pd.to_numeric(df.get("number", pd.Series()), errors="coerce")
            valid_numbers = df["number_int"].dropna().astype(int).tolist()
            if valid_numbers:
                avg = mean(valid_numbers)
                target = K_FACTOR * avg
                st.metric("Participants (revealed)", len(valid_numbers))
                st.metric("Average", f"{avg:.2f}")
                st.metric("Target (2/3 × avg)", f"{target:.2f}")
        else:
            st.write("Refresh reveals to see quick stats.")

    st.markdown("---")

    # Calculate Results Button and logic
    if st.button("🏆 Calculate Winners", type="primary"):
        with st.spinner("Calculating results..."):
            commits_url = f"{api_url}?table=commits"
            reveals_url = f"{api_url}?table=reveals"

            commits_data = get_csv_data(commits_url)
            reveals_data = get_csv_data(reveals_url)

            if not reveals_data:
                st.warning("No reveals yet to calculate winners")
            else:
                # Simple verification (you can expand this with the full logic from merge script)
                valid_numbers = []
                parsed_reveals = []
                for reveal in reveals_data:
                    try:
                        num = int(reveal.get('number', ''))
                        if 0 <= num <= 100:
                            valid_numbers.append(num)
                            parsed_reveals.append({
                                "uni_id": reveal.get("uni_id"),
                                "number": num,
                                "nonce": reveal.get("nonce", "")
                            })
                    except:
                        pass

                if valid_numbers:
                    avg = mean(valid_numbers)
                    target = K_FACTOR * avg

                    st.success("✅ Results Calculated!")

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Participants", len(valid_numbers))
                    with col2:
                        st.metric("Average", f"{avg:.2f}")
                    with col3:
                        st.metric("Target (2/3 × avg)", f"{target:.2f}")

                    # Build DataFrame of distances
                    results_df = pd.DataFrame(parsed_reveals)
                    results_df["distance"] = (results_df["number"] - target).abs()
                    results_df = results_df.sort_values("distance").reset_index(drop=True)
                    results_df.index += 1
                    results_df.index.name = "Rank"

                    st.subheader("🏆 Top 10 Closest")
                    st.table(results_df.head(10)[["number", "distance"]])

                    st.markdown("Full results:")
                    st.dataframe(results_df, use_container_width=True)
                else:
                    st.warning("No valid numeric reveals found to compute results.")

# TAB 4: INSTRUCTIONS
with tab4:
    st.header("ℹ️ How to Play")
    st.markdown("""
    ## Game Rules

    The **Beauty Contest Game** is a game theory experiment:

    1. Each player chooses a number between 0 and 100
    2. The "target" is calculated as **2/3 of the average** of all submitted numbers
    3. The player(s) closest to the target wins!

    ## Strategy

    - If everyone picks 100, the average is 100, and 2/3 × 100 = 66.67
    - If everyone realizes this and picks 66.67, then 2/3 × 66.67 = 44.44
    - This reasoning continues... where does it end?
    - The Nash equilibrium is 0!

    ## How to Participate

    ### Phase 1: Commit (Before Deadline)
    1. Choose your number (0-100)
    2. Create a secret nonce (random string)
    3. Generate your commitment hash
    4. **SAVE YOUR NUMBER AND NONCE** (you'll need them later!)
    5. Submit to the server

    ### Phase 2: Reveal (After Deadline)
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
    - Append-only: Latest reveal per student is counted

    ## Important Notes

    ⚠️ **Save your information!** If you lose your nonce, you cannot reveal your commitment.

    ⚠️ **Exact match required!** Your reveal must match your commit exactly (including number and nonce).

    ⚠️ **Timing matters!** Commits must be before deadline, reveals after.
    """)

# Footer
st.markdown("---")
st.caption("🎮 Decentralized Beauty Contest Game | Built with Streamlit")