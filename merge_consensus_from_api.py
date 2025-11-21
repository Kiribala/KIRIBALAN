# -*- coding: utf-8 -*-
"""
Created on Sat Sep 20 08:14:54 2025

@author: s.balasubramaniam
"""

"""
Merge script for decentralized beauty contest (append-only version).

Rules:
  - Each student can have multiple commits and reveals.
  - For each uni_id, take the LATEST reveal (by timestamp).
  - Match it to the LATEST commit whose timestamp <= that reveal.
  - Verify SHA256(uni_id|number|nonce) == commit.
  - If verified and number ∈ [0,100], include in scoring.
  - Score = distance from target, where target = k_factor * class average.
"""

import csv, io, hashlib, requests
from statistics import mean
from datetime import datetime

# Parameters
K_FACTOR = 2/3
ALLOWED_MIN, ALLOWED_MAX = 0, 100

# Output files
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

def get_csv(url: str):
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return list(csv.DictReader(io.StringIO(r.text)))

def write_csv(path, fieldnames, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=fieldnames)
        wr.writeheader()
        for r in rows:
            wr.writerow({k: r.get(k, "") for k in fieldnames})

def main():
    base = input("Paste API base (ends with /exec): ").strip()
    commits_url = f"{base}?table=commits"
    reveals_url = f"{base}?table=reveals"

    commits_raw = get_csv(commits_url)
    reveals_raw = get_csv(reveals_url)

    # Parse commits
    commits = {}
    for r in commits_raw:
        uid = (r.get("uni_id") or "").strip()
        ch  = (r.get("commit") or "").strip()
        ts  = (r.get("timestamp_utc") or "").strip()
        if not uid or not ch: continue
        commits.setdefault(uid, []).append({
            "timestamp_utc": ts,
            "ts_parsed": parse_ts(ts),
            "uni_id": uid,
            "commit": ch
        })

    # Parse reveals
    reveals = {}
    for r in reveals_raw:
        uid = (r.get("uni_id") or "").strip()
        num = (r.get("number") or "").strip()
        nonce = (r.get("nonce") or "").strip()
        ts  = (r.get("timestamp_utc") or "").strip()
        if not uid or not num or not nonce: continue
        reveals.setdefault(uid, []).append({
            "timestamp_utc": ts,
            "ts_parsed": parse_ts(ts),
            "uni_id": uid,
            "number_raw": num,
            "nonce": nonce
        })

    verified_rows = []
    matched_commits = {}

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
    valid = [(r["uni_id"], int(r["number"])) for r in verified_rows
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

    # Outputs
    write_csv(
        OUT_COMMITS, ["timestamp_utc","uni_id","commit"],
        sorted(matched_commits.values(), key=lambda r: (r["uni_id"], r["timestamp_utc"]))
    )
    write_csv(
        OUT_REVEALS, ["timestamp_utc","uni_id","number","nonce","preimage_hash","verified"],
        sorted([r for r in verified_rows if r["verified"]=="True"],
               key=lambda r: (r["uni_id"], r["timestamp_utc"]))
    )
    for r in verified_rows:
        if r["verified"] == "True" and target is not None:
            r["distance"] = f"{abs(int(r['number']) - target):.6f}"
        else:
            r["distance"] = ""
    write_csv(
        OUT_LEADER,
        ["uni_id","number","verified","reason","distance","commit","nonce","timestamp_utc"],
        sorted(verified_rows, key=lambda r: (r["verified"]!="True", r.get("distance","ZZZ"), r["uni_id"]))
    )

    with open(OUT_RESULTS, "w", encoding="utf-8") as f:
        f.write("=== CLASS RESULTS (Latest-Attempt Consensus) ===\n")
        f.write(f"k_factor = {K_FACTOR}\n")
        if valid:
            f.write(f"participants_counted = {len(valid)}\n")
            f.write(f"average = {avg_val:.6f}\n")
            f.write(f"target = {target:.6f}\n")
            f.write(f"min_distance = {min_dist:.6f}\n")
            f.write("winners:\n")
            for uid, n, d in winners:
                f.write(f"  - {uid} with {n} (distance {d:.6f})\n")
        else:
            f.write("No valid verified reveals. Cannot compute winners.\n")

    print(f"Wrote: {OUT_COMMITS}, {OUT_REVEALS}, {OUT_LEADER}, {OUT_RESULTS}")
    if valid:
        print(f"Average={avg_val:.4f}, Target={target:.4f}, Winners={', '.join(uid for uid,_,_ in winners)}")

if __name__ == "__main__":
    main()
