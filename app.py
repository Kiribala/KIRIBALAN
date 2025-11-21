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

# Page Configuration
st.set_page_config(
    page_title="Beauty Contest Game",
    page_icon="🎯",
    layout="wide"
)

# Title and Description
st.title("🎯 Decentralized Beauty Contest Game")
st.markdown("""
This is a strategic game where you try to guess **2/3 of the average** of all players' guesses.
- **Commit Phase**: Choose a number (0-100) and create a secret commitment
- **Reveal Phase**: Reveal your number after the deadline
- **Winner**: Closest to 2/3 × average wins!
""")

# Sidebar for API Configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    api_url = st.text_input("API URL", value=API_DEFAULT)
    
    st.divider()
    
    current_time = now_utc()
    st.subheader("⏰ Game Timeline")
    
    commit_open = current_time <= COMMIT_DEADLINE_UTC
    reveal_open = current_time >= REVEAL_OPEN_UTC
    
    st.write(f"**Current Time (UTC):**")
    st.write(current_time.strftime("%Y-%m-%d %H:%M:%S"))
    
    st.write(f"**Commit Deadline:**")
    st.write("2025-10-21 21:59:59 UTC")
    st.write("(2025-10-21 23:59:59 Paris)")
    
    if commit_open:
        st.success("✅ Commits OPEN")
    else:
        st.error("❌ Commits CLOSED")
    
    st.write(f"**Reveal Opens:**")
    st.write("2025-10-21 22:00:00 UTC")
    st.write("(2025-10-22 00:00:00 Paris)")
    
    if reveal_open:
        st.success("✅ Reveals OPEN")
    else:
        st.warning("⏳ Reveals NOT OPEN")

# Main Content Tabs
tab1, tab2, tab3, tab4 = st.tabs(["📝 Commit", "🔓 Reveal", "📊 Leaderboard", "ℹ️ Instructions"])

# TAB 1: COMMIT PHASE
with tab1:
    st.header("📝 Commit Phase")
    
    if not commit_open:
        st.error("⛔ The commit window is CLOSED. Deadline has passed.")
    else:
        st.success("✅ Commit window is OPEN. Submit your commitment before the deadline!")
    
    with st.form("commit_form"):
        st.subheader("Create Your Commitment")
        
        col1, col2 = st.columns(2)
        
        with col1:
            uni_id = st.text_input("University ID", help="Your unique identifier")
            number = st.number_input("Choose your number", min_value=0, max_value=100, value=50, 
                                    help="Pick a number between 0 and 100")
        
        with col2:
            nonce = st.text_input("Secret Nonce", type="password", 
                                 help="A secret string only you know. SAVE THIS!")
            nonce_confirm = st.text_input("Confirm Nonce", type="password")
        
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
                
                st.success("✅ Commitment hash generated!")
                st.code(commit_hash, language=None)
                
                st.warning("⚠️ **IMPORTANT**: Save this information!")
                st.info(f"""
**Preimage:** `{preimage}`

**You will need:**
- University ID: `{uni_id}`
- Number: `{number}`
- Nonce: `{nonce}`

**Write these down NOW!** You'll need them for the reveal phase.
                """)
                
                if st.button("📤 Submit to Server"):
                    with st.spinner("Submitting..."):
                        status, response = send_commit(api_url, uni_id, commit_hash)
                        if status:
                            st.success(f"✅ Server Response ({status}): {response}")
                        else:
                            st.error(f"❌ Error: {response}")

# TAB 2: REVEAL PHASE
with tab2:
    st.header("🔓 Reveal Phase")
    
    if not reveal_open:
        st.warning("⏳ The reveal window is NOT open yet. Wait until after the deadline.")
    else:
        st.success("✅ Reveal window is OPEN. You can now reveal your commitment!")
    
    with st.form("reveal_form"):
        st.subheader("Reveal Your Commitment")
        st.info("Enter EXACTLY what you committed during the commit phase")
        
        col1, col2 = st.columns(2)
        
        with col1:
            reveal_uni_id = st.text_input("University ID (same as commit)", key="reveal_uni_id")
            reveal_number = st.number_input("Your number (same as commit)", min_value=0, max_value=100, 
                                          value=50, key="reveal_number")
        
        with col2:
            reveal_nonce = st.text_input("Your secret nonce (same as commit)", type="password", 
                                        key="reveal_nonce")
        
        # Show what hash this would produce
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

# TAB 3: LEADERBOARD
with tab3:
    st.header("📊 Current Status")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Commits")
        if st.button("🔄 Refresh Commits"):
            commits_url = f"{api_url}?table=commits"
            commits = get_csv_data(commits_url)
            if commits:
                st.dataframe(commits, use_container_width=True)
                st.caption(f"Total commits: {len(commits)}")
            else:
                st.info("No commits yet")
    
    with col2:
        st.subheader("🔓 Reveals")
        if st.button("🔄 Refresh Reveals"):
            reveals_url = f"{api_url}?table=reveals"
            reveals = get_csv_data(reveals_url)
            if reveals:
                st.dataframe(reveals, use_container_width=True)
                st.caption(f"Total reveals: {len(reveals)}")
            else:
                st.info("No reveals yet")
    
    st.divider()
    
    # Calculate Results
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
                for reveal in reveals_data:
                    try:
                        num = int(reveal.get('number', ''))
                        if 0 <= num <= 100:
                            valid_numbers.append(num)
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
                    
                    # Find closest
                    distances = [(reveal, abs(int(reveal.get('number', 0)) - target)) 
                                for reveal in reveals_data 
                                if reveal.get('number', '').isdigit()]
                    
                    if distances:
                        distances.sort(key=lambda x: x[1])
                        
                        st.subheader("🏆 Top 5 Closest")
                        for i, (reveal, dist) in enumerate(distances[:5], 1):
                            st.write(f"{i}. **{reveal.get('uni_id')}** - Number: {reveal.get('number')} - Distance: {dist:.4f}")

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
st.divider()
st.caption("🎮 Decentralized Beauty Contest Game | Built with Streamlit")