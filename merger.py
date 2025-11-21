# merger.py
# Core merging logic extracted and adapted from merge_consensus_from_api.py
# Produces CSV/text outputs as strings so callers (CLI/web) can save or present them.

import csv
import io
import hashlib
import requests
from statistics import mean
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional

K_FACTOR = 2/3
ALLOWED_MIN, ALLOWED_MAX = 0, 100

OUT_COMMITS  = "merged_commits.csv"
OUT_REVEALS  = "merged_reveals.csv"
OUT_LEADER   = "class_leaderboard.csv"
OUT_RESULTS  = "class_results.txt"


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def parse_ts(ts: str):
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def get_csv_rows(url: str, timeout: int = 20) -> List[Dict[str, str]]:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))


def _write_csv_string(fieldnames: List[str], rows: List[Dict[str, Any]]) -> str:
    buf = io.StringIO()
    wr = csv.DictWriter(buf, fieldnames=fieldnames)
    wr.writeheader()
    for r in rows:
        wr.writerow({k: r.get(k, "") for k in fieldnames})
    return buf.getvalue()


def merge_from_api(base: str) -> Dict[str, Any]:
    """
    Fetches commits and reveals from base?table=commits and base?table=reveals,
    runs the same merge/verification logic as the original script, and returns:
      {
        "commits_csv": str,
        "reveals_csv": str,
        "leader_csv": str,
        "results_txt": str,
        "summary": { ... }  # metadata such as participants_counted, average, winners
      }
    Raises requests.HTTPError or requests.RequestException on network errors.
    """
    commits_url = f"{base}?table=commits"
    reveals_url = f"{base}?table=reveals"

    commits_raw = get_csv_rows(commits_url)
    reveals_raw = get_csv_rows(reveals_url)

    # Parse commits
    commits: Dict[str, List[Dict[str, Any]]] = {}
    for r in commits_raw:
        uid = (r.get("uni_id") or "").strip()
        ch  = (r.get("commit") or "").strip()
        ts  = (r.get("timestamp_utc") or "").strip()
        if not uid or not ch:
            continue
        commits.setdefault(uid, []).append({
            "timestamp_utc": ts,
            "ts_parsed": parse_ts(ts),
            "uni_id": uid,
            "commit": ch
        })

    # Parse reveals
    reveals: Dict[str, List[Dict[str, Any]]] = {}
    for r in reveals_raw:
        uid = (r.get("uni_id") or "").strip()
        num = (r.get("number") or "").strip()
        nonce = (r.get("nonce") or "").strip()
        ts  = (r.get("timestamp_utc") or "").strip()
        if not uid or not num or not nonce:
            continue
        reveals.setdefault(uid, []).append({
            "timestamp_utc": ts,
            "ts_parsed": parse_ts(ts),
            "uni_id": uid,
            "number_raw": num,
            "nonce": nonce
        })

    verified_rows: List[Dict[str, Any]] = []
    matched_commits: Dict[str, Dict[str, Any]] = {}

    for uid, rlist in reveals.items():
        # latest reveal
        rlist_sorted = sorted(rlist, key=lambda x: (x["ts_parsed"] or datetime.min))
        latest_rev = rlist_sorted[-1]
        ts_rev = latest_rev["ts_parsed"] or datetime.min

        # parse number
        try:
            num = int(latest_rev["number_raw"])
        except Exception:
            num = None

        # latest commit before or at reveal
        cands = []
        for c in commits.get(uid, []):
            ts_c = c["ts_parsed"] or datetime.min
            if ts_c <= ts_rev:
                cands.append(c)
        cands.sort(key=lambda x: (x["ts_parsed"] or datetime.min))
        chosen_commit = cands[-1] if cands else None
        if chosen_commit:
            matched_commits[uid] = chosen_commit

        reason = "ok"
        verified = False
        if chosen_commit is None:
            reason = "no_commit_before_reveal"
        elif num is None:
            reason = "number_not_int"
        elif not (ALLOWED_MIN <= num <= ALLOWED_MAX):
            reason = "out_of_range"
        else:
            pre = f"{uid}|{num}|{latest_rev['nonce']}"
            verified = (sha256(pre) == chosen_commit["commit"])
            if not verified:
                reason = "hash_mismatch"

        verified_rows.append({
            "uni_id": uid,
            "timestamp_utc": latest_rev["timestamp_utc"],
            "number": "" if num is None else str(num),
            "nonce": latest_rev["nonce"],
            "commit": chosen_commit["commit"] if chosen_commit else "",
            "preimage_hash": "" if num is None else sha256(f"{uid}|{num}|{latest_rev['nonce']}"),
            "verified": "True" if verified else "False",
            "reason": reason
        })

    # Winners from verified reveals
    valid: List[Tuple[str, int]] = [(r["uni_id"], int(r["number"])) for r in verified_rows
             if r["verified"] == "True" and r["number"] != ""]
    if valid:
        avg_val = mean(n for _, n in valid)
        target = K_FACTOR * avg_val
        distances = [(uid, n, abs(n - target)) for uid, n in valid]
        min_dist = min(d for _, _, d in distances)
        winners = [(uid, n, d) for uid, n, d in distances if abs(d - min_dist) < 1e-12]
    else:
        avg_val = target = min_dist = None
        winners = []

    # prepare CSV outputs (strings)
    commits_rows = sorted(matched_commits.values(), key=lambda r: (r["uni_id"], r["timestamp_utc"]))
    commits_csv = _write_csv_string(["timestamp_utc","uni_id","commit"], commits_rows)

    reveals_csv = _write_csv_string(
        ["timestamp_utc","uni_id","number","nonce","preimage_hash","verified"],
        sorted([r for r in verified_rows if r["verified"]=="True"],
               key=lambda r: (r["uni_id"], r["timestamp_utc"]))
    )

    for r in verified_rows:
        if r["verified"] == "True" and target is not None:
            r["distance"] = f"{abs(int(r['number']) - target):.6f}"
        else:
            r["distance"] = ""
    leader_csv = _write_csv_string(
        ["uni_id","number","verified","reason","distance","commit","nonce","timestamp_utc"],
        sorted(verified_rows, key=lambda r: (r["verified"]!="True", r.get("distance","ZZZ"), r["uni_id"]))
    )

    # results text
    buf = io.StringIO()
    buf.write("=== CLASS RESULTS (Latest-Attempt Consensus) ===\n")
    buf.write(f"k_factor = {K_FACTOR}\n")
    if valid:
        buf.write(f"participants_counted = {len(valid)}\n")
        buf.write(f"average = {avg_val:.6f}\n")
        buf.write(f"target = {target:.6f}\n")
        buf.write(f"min_distance = {min_dist:.6f}\n")
        buf.write("winners:\n")
        for uid, n, d in winners:
            buf.write(f"  - {uid} with {n} (distance {d:.6f})\n")
    else:
        buf.write("No valid verified reveals. Cannot compute winners.\n")
    results_txt = buf.getvalue()

    summary = {
        "participants_counted": len(valid),
        "average": avg_val,
        "target": target,
        "min_distance": min_dist,
        "winners": winners,
    }

    return {
        "commits_csv": commits_csv,
        "reveals_csv": reveals_csv,
        "leader_csv": leader_csv,
        "results_txt": results_txt,
        "summary": summary,
    }