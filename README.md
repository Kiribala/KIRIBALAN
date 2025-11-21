```markdown
# Merge Consensus App

A small web app that runs the "merge_consensus_from_api.py" logic via a browser UI.

What it does
- Fetches "commits" and "reveals" CSV tables from an API base URL (the original script used Google Apps Script /exec endpoints).
- For each uni_id, takes latest reveal, matches latest prior commit, verifies SHA256(uni_id|number|nonce), computes winners based on k_factor * average.
- Produces downloadable CSVs and a results text file.

Quick start (local)
1. Create a virtualenv and activate it:
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate

2. Install dependencies:
   pip install -r requirements.txt

3. Run the app:
   python app.py

4. Open http://127.0.0.1:5000 in your browser and paste the API base URL (must end with /exec).

Docker (optional)
- Build:
  docker build -t merge-consensus-app .
- Run:
  docker run -p 5000:5000 merge-consensus-app

Notes
- In production replace the Flask secret key and consider using gunicorn behind a reverse proxy.
- The app runs the merge operation on every request; if your CSVs are large or the upstream rate-limits, add caching.
- The core logic is in merger.py so you can also import and run it from scripts or tests.

Files added
- merger.py : core logic (refactored)
- app.py : Flask web front-end
- templates/*.html : minimal UI templates
- requirements.txt, README.md, .gitignore, Dockerfile
```