import streamlit as st
import hashlib
import requests
import io
import csv
import pandas as pd
from datetime import datetime, timezone
from statistics import mean

# --- Configuration & Helpers (from all 3 scripts) ---

st.set_page_config(page_title="Keynesian Beauty Contest", layout="wide", page_icon="⛓️")

# Default API URL from info.txt
API_DEFAULT = "https://script.google.com/macros/s/AKfycbyNZNOE1DYNbd4GbGTISJsGrnJ4PYCuip0yjSw3Lr8KkD6-kadKI9mfpKNfiAHEWb0Osw/exec"

# Parameters from merge_consensus.py
K_FACTOR = 2/3
ALLOWED_MIN, ALLOWED_MAX = 0, 100

# --- Helper Functions (from clients & merge scripts) ---

def sha256(s):
    """Computes the SHA-256 hash of a string."""
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def now_utc():
    """Returns the current time in UTC."""
    return datetime.now(timezone.utc)

def parse_ts(ts):
    """Parses an ISO timestamp string (robust to 'Z' suffix)."""
    try:
        # Handle Google Sheet's 'Z' suffix for UTC
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None

@st.cache_data(ttl=60) # Cache API data for 60 seconds
def get_csv(url):
    """Fetches and parses a CSV from a URL."""
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        # Use io.StringIO to treat the text as a file
        csv_data = list(csv.DictReader(io.StringIO(r.text)))
        return csv_data
    except Exception as e:
        st.error("Failed to fetch data from {}: {}".format(url, e))
        return None

# --- Core Consensus Logic (from merge_consensus.py) ---

def run_consensus(base):
    """
    Fetches all commits and reveals, runs the consensus algorithm,
    and returns the results for display in Streamlit.
    """
    commits_url = "{}?table=commits".format(base)
    reveals_url = "{}?table=reveals".format(base)

    commits_raw = get_csv(commits_url)
    reveals_raw = get_csv(reveals_url)

    if commits_raw is None or reveals_raw is None:
        return None, None, None  # Error state

    # 1. Parse commits into a dict by uni_id
    commits = {}
    for r in commits_raw:
        uid = (r.get("uni_id") or "").strip()
        ch = (r.get("commit") or "").strip()
        ts = (r.get("timestamp_utc") or "").strip()
        if not uid or not ch or not ts:
            continue
        commits.setdefault(uid, []).append({
            "timestamp_utc": ts,
            "ts_parsed": parse_ts(ts),
            "uni_id": uid,
            "commit": ch
        })

    # 2. Parse reveals into a dict by uni_id
    reveals = {}
    for r in reveals_raw:
        uid = (r.get("uni_id") or "").strip()
        num = (r.get("number") or "").strip()
        nonce = (r.get("nonce") or "").strip()
        ts = (r.get("timestamp_utc") or "").strip()
        if not uid or not num or not ts: # Nonce can be empty, but not uid/num/ts
            continue
        reveals.setdefault(uid, []).append({
            "timestamp_utc": ts,
            "ts_parsed": parse_ts(ts),
            "uni_id": uid,
            "number_raw": num,
            "nonce": nonce
        })

    verified_rows = []
    matched_commits = {}

    # 3. Run matching logic for each student
    for uid, rlist in reveals.items():
        # Rule: take the LATEST reveal
        rlist_sorted = sorted(rlist, key=lambda x: (x["ts_parsed"] or datetime.min))
        latest_rev = rlist_sorted[-1]
        ts_rev = latest_rev["ts_parsed"] or datetime.min

        # Parse number
        try:
            num = int(latest_rev["number_raw"])
        except Exception:
            num = None

        # Rule: take the LATEST commit whose timestamp <= that reveal
        cands = []
        for c in commits.get(uid, []):
            ts_c = c["ts_parsed"] or datetime.min
            if ts_c <= ts_rev:
                cands.append(c)
        
        chosen_commit = None
        if cands:
            cands.sort(key=lambda x: (x["ts_parsed"] or datetime.min))
            chosen_commit = cands[-1]
            matched_commits[uid] = chosen_commit # For debug/output

        # 4. Verify the reveal against the commit
        reason = "ok"
        verified = False
        preimage_hash = ""
        
        if chosen_commit is None:
            reason = "no_commit_before_reveal"
        elif num is None:
            reason = "number_not_int"
        elif not (ALLOWED_MIN <= num <= ALLOWED_MAX):
            reason = "out_of_range"
        else:
            preimage = "{}|{}|{}".format(uid, num, latest_rev['nonce'])
            preimage_hash = sha256(preimage)
            verified = (preimage_hash == chosen_commit["commit"])
            if not verified:
                reason = "hash_mismatch"

        # Add to leaderboard data
        verified_rows.append({
            "uni_id": uid,
            "timestamp_utc": latest_rev["timestamp_utc"],
            "number": "" if num is None else str(num),
            "nonce": latest_rev["nonce"],
            "commit": chosen_commit["commit"] if chosen_commit else "",
            "preimage_hash": preimage_hash,
            "verified": "True" if verified else "False",
            "reason": reason
        })

    # 5. Calculate winners from verified reveals
    valid = [(r["uni_id"], int(r["number"])) for r in verified_rows
             if r["verified"] == "True" and r["number"] != ""]
    
    avg_val = target = min_dist = None
    winners = []
    
    if valid:
        avg_val = mean(n for _, n in valid)
        target = K_FACTOR * avg_val
        distances = [(uid, n, abs(n - target)) for uid, n in valid]
        min_dist = min(d for _, _, d in distances)
        # Handle ties by checking for near-zero difference
        winners = [(uid, n, d) for uid, n, d in distances if abs(d - min_dist) < 1e-12]

    # 6. Prepare outputs for Streamlit
    
    # Leaderboard DataFrame
    leaderboard_data = []
    for r in verified_rows:
        dist = None
        if r["verified"] == "True" and r["number"] != "" and target is not None:
            try:
                dist = abs(int(r['number']) - target)
            except ValueError:
                dist = None # Should not happen if verified
        r["distance"] = dist
        leaderboard_data.append(r)
        
    leaderboard_df = pd.DataFrame(leaderboard_data)
    # Re-order columns for clarity
    cols = ["uni_id", "number", "verified", "reason", "distance", "commit", "nonce", "timestamp_utc"]
    # Ensure all columns exist before reindexing
    for c in cols:
        if c not in leaderboard_df.columns:
            leaderboard_df[c] = None
            
    leaderboard_df = leaderboard_df.reindex(columns=cols)
    leaderboard_df = leaderboard_df.sort_values(
        by=["verified", "distance", "uni_id"],
        ascending=[False, True, True]
    )

    # Results summary dict
    results_summary = {
        "k_factor": K_FACTOR,
        "participants": len(valid),
        "average": avg_val,
        "target": target,
        "min_distance": min_dist,
        "winners": winners
    }

    return leaderboard_df, results_summary, (commits_raw, reveals_raw)

# --- Streamlit UI ---

st.title("⛓️ Keynesian Beauty Contest (Blockchain-style)")
st.write("Cette application fournit une interface utilisateur pour le jeu de 'Beauté' décentralisé, en utilisant les scripts fournis.")

api_url = st.text_input(
    "API Base URL (Google Apps Script)",
    value=API_DEFAULT,
    help="L'URL de base /exec pour l'API Google Sheet."
)

tab_about, tab_commit, tab_reveal, tab_consensus = st.tabs([
    "📖 À Propos",
    "1️⃣ Phase de Commit",
    "2️⃣ Phase de Reveal",
    "🏆 Consensus & Résultats"
])

# --- About Tab ---
with tab_about:
    st.header("À Propos de ce Jeu")
    st.markdown("""
    Cette application implémente un jeu de **Concours de Beauté Keynesien** (Keynesian Beauty Contest), géré de manière décentralisée, similaire à une blockchain.
    
    - **Objectif :** Deviner un nombre entre 0 et 100. Le(s) gagnant(s) sont ceux dont le nombre est le plus proche des **2/3 de la moyenne de la classe**.
    - **Principes de la Blockchain :**
        - **Commit-Reveal :**
            1.  Vous "commettez" d'abord un *hash* (une empreinte cryptographique) de votre choix. Cela prouve que vous avez choisi votre numéro à un moment donné, sans le révéler.
            2.  Après la date limite, vous "révélez" votre numéro et un `nonce` (un mot de passe secret).
        - **Registre Append-Only :** Tous les commits et reveals sont envoyés à un Google Sheet public qui agit comme notre "blockchain" (registre public et non modifiable).
        - **Consensus Décentralisé :** N'importe qui peut exécuter le script de "fusion" (l'onglet 'Consensus' de cette app) pour télécharger toutes les données publiques, appliquer les règles et vérifier indépendamment le gagnant. Aucune autorité centrale n'est nécessaire.
    """)
    st.subheader("Comment jouer")
    st.markdown("""
    1.  **Phase de Commit :** Allez à l'onglet 1, entrez votre ID, votre choix (0-100), et un `nonce` secret. Cliquez sur "Submit Commit".
    2.  **Phase de Reveal :** Allez à l'onglet 2, entrez les *mêmes* ID, numéro et `nonce`. Cliquez sur "Submit Reveal".
    3.  **Phase de Consensus :** Allez à l'onglet 3 et cliquez sur "Lancer le Consensus" pour voir le classement et les résultats en direct.
    """)
    st.image("https://i.imgur.com/830XG2O.png", caption="Schéma du flux Commit-Reveal", use_column_width=True)


# --- Commit Tab ---
with tab_commit:
    st.header("1️⃣ Phase de Commit")
    st.write("Soumettez votre choix *haché* au registre. Vous devez sauvegarder votre `preimage` (ID|Numéro|Nonce) pour l'utiliser lors de la phase de reveal.")
    
    with st.form("commit_form"):
        commit_uni_id = st.text_input("Votre ID Universitaire")
        commit_number = st.number_input(
            "Choisissez votre numéro (0-100)",
            min_value=ALLOWED_MIN,
            max_value=ALLOWED_MAX,
            step=1
        )
        commit_nonce = st.text_input(
            "Choisissez un 'nonce' secret (gardez-le !)",
            type="password",
            help="Ex: 'abc123' ou 'mon_secret_1984'"
        )
        
        submitted_commit = st.form_submit_button("Submit Commit")
        
        if submitted_commit:
            if not commit_uni_id or not commit_nonce:
                st.error("L'ID Universitaire et le Nonce ne peuvent pas être vides.")
            else:
                # Logique de commit_client.py
                preimage = "{}|{}|{}".format(commit_uni_id, commit_number, commit_nonce)
                commit_hash = sha256(preimage)
                
                st.code("Preimage: {}".format(preimage), language="text")
                st.code("Commit Hash: {}".format(commit_hash), language="text")
                st.warning("⚠️ **SAUVEGARDEZ VOTRE PREIMAGE !** Vous en aurez besoin pour le 'reveal'.")
                
                payload = {"kind": "commit", "uni_id": commit_uni_id, "commit": commit_hash}
                try:
                    with st.spinner("Soumission au registre..."):
                        r = requests.post(api_url, json=payload, timeout=15)
                    st.info("Réponse du serveur (Status {}):".format(r.status_code))
                    st.json(r.text)
                except Exception as e:
                    st.error("Erreur réseau : {}".format(e))

# --- Reveal Tab ---
with tab_reveal:
    st.header("2️⃣ Phase de Reveal")
    st.write("Soumettez votre choix *en clair* et votre nonce. Ils seront vérifiés par rapport à votre 'commit' précédent.")
    
    with st.form("reveal_form"):
        reveal_uni_id = st.text_input("Votre ID Universitaire")
        reveal_number = st.number_input(
            "Votre numéro (0-100)",
            min_value=ALLOWED_MIN,
            max_value=ALLOWED_MAX,
            step=1
        )
        reveal_nonce = st.text_input(
            "Votre 'nonce' secret (le même qu'au commit)",
            type="password"
        )
        
        submitted_reveal = st.form_submit_button("Submit Reveal")
        
        if submitted_reveal:
            if not reveal_uni_id or not reveal_nonce:
                st.error("L'ID Universitaire et le Nonce ne peuvent pas être vides.")
            else:
                # Logique de reveal_client.py
                payload = {
                    "kind": "reveal",
                    "uni_id": reveal_uni_id,
                    "number": reveal_number,
                    "nonce": reveal_nonce
                }
                try:
                    with st.spinner("Soumission au registre..."):
                        r = requests.post(api_url, json=payload, timeout=15)
                    st.info("Réponse du serveur (Status {}):".format(r.status_code))
                    st.json(r.text)
                except Exception as e:
                    st.error("Erreur réseau : {}".format(e))

# --- Consensus Tab ---
with tab_consensus:
    st.header("🏆 Consensus & Résultats")
    st.write("Lancez l'algorithme de consensus pour récupérer toutes les données publiques et déterminer le gagnant.")
    
    if st.button("Lancer le Consensus"):
        with st.spinner("Récupération des données et exécution du consensus..."):
            leaderboard, results, raw_data = run_consensus(api_url)
            
            if leaderboard is None:
                st.error("Échec de l'exécution du consensus. Vérifiez l'URL de l'API.")
            else:
                st.subheader("Résultats du Jeu")
                col1, col2, col3 = st.columns(3)
                col1.metric("Participants (Vérifiés)", results.get("participants", 0))
                col2.metric("Moyenne de la Classe", "{:.4f}".format(results.get("average", 0)))
                col3.metric("Cible (2/3 de la Moyenne)", "{:.4f}".format(results.get("target", 0)))
                
                st.subheader("🏆 Gagnant(s) 🏆")
                winners = results.get("winners", [])
                if not winners:
                    st.warning("Aucun gagnant trouvé (ou aucun participant valide).")
                else:
                    for uid, n, d in winners:
                        st.success("**{}** avec le choix **{}** (Distance : {:.6f})".format(uid, n, d))
                
                st.subheader("Classement Complet (Leaderboard)")
                st.dataframe(leaderboard, use_container_width=True)
                
                with st.expander("Voir les données brutes du registre (JSON)"):
                    st.json({"commits": raw_data[0], "reveals": raw_data[1]})