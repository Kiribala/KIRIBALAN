# app.py
# Simple Flask web application that exposes a form to run the merge against an API base URL.
# Uses merger.merge_from_api to fetch and compute results, and returns CSV/text for download.

from flask import Flask, request, render_template, send_file, Response, redirect, url_for, flash
import io
import merger
import traceback

app = Flask(__name__)
app.secret_key = "replace-me-with-secure-key-in-prod"  # for flash messages


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        base = request.form.get("base", "").strip()
        if not base:
            flash("Please provide the API base URL (must end with /exec).", "warning")
            return redirect(url_for("index"))
        try:
            result = merger.merge_from_api(base)
            # store in session-like temporary store - in this simple app we pass via query param by creating
            # an identifier would be more robust; for simplicity we'll render result directly.
            return render_template("results.html", base=base, result=result)
        except Exception as e:
            tb = traceback.format_exc()
            flash(f"Error while fetching/processing: {e}", "danger")
            # show stack trace on page for debugging (useful for development)
            return render_template("index.html", error=tb, base=base)
    return render_template("index.html")


@app.route("/download/<kind>", methods=["GET"])
def download(kind):
    # kind: commits | reveals | leader | results
    base = request.args.get("base", "")
    if not base:
        flash("Missing base parameter for download.", "warning")
        return redirect(url_for("index"))
    try:
        result = merger.merge_from_api(base)
    except Exception as e:
        flash(f"Error during merge: {e}", "danger")
        return redirect(url_for("index"))
    if kind == "commits":
        data = result["commits_csv"]
        mimetype = "text/csv"
        filename = merger.OUT_COMMITS
    elif kind == "reveals":
        data = result["reveals_csv"]
        mimetype = "text/csv"
        filename = merger.OUT_REVEALS
    elif kind == "leader":
        data = result["leader_csv"]
        mimetype = "text/csv"
        filename = merger.OUT_LEADER
    elif kind == "results":
        data = result["results_txt"]
        mimetype = "text/plain"
        filename = merger.OUT_RESULTS
    else:
        flash("Unknown download kind.", "warning")
        return redirect(url_for("index"))

    return Response(
        data,
        mimetype=mimetype,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)