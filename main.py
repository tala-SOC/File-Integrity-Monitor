import os
import atexit
import sqlite3
import flask
from werkzeug.utils import secure_filename

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
TEMPLATES_FOLDER = os.path.join(PROJECT_ROOT, "Flask_Dashboard", "templates")
STATIC_FOLDER = os.path.join(PROJECT_ROOT, "Flask_Dashboard", "static")
MONITORED_DIRECTORY = os.path.join(PROJECT_ROOT, "monitored_files")

app = flask.Flask(
    __name__,
    template_folder=TEMPLATES_FOLDER,
    static_folder=STATIC_FOLDER
)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

from Database.database import (
    initialize_database,
    get_events,
    get_event_statistics,
)
from Monitoring_Engine.file_metadata import get_file_metadata
from Monitoring_Engine.file_scanner import scan_directory
from Monitoring_Engine.detector import detect_changes

try:
    initialize_database()
    print("[FIM] Database initialized successfully.")
except Exception as error:
    print("[FIM] Database initialization error:", error)

os.makedirs(MONITORED_DIRECTORY, exist_ok=True)

observer = None

try:
    from Monitoring_Engine.realtime_monitor import start_realtime_monitor

    observer = start_realtime_monitor(MONITORED_DIRECTORY)
    print("[FIM] Real-time monitoring started.")
except Exception as error:
    print("[FIM] Real-time monitor could not start:", error)


def is_safe_path(base_directory, target_path):
    try:
        base_directory = os.path.realpath(base_directory)
        target_path = os.path.realpath(target_path)

        return (
            os.path.commonpath([base_directory, target_path])
            == base_directory
        )
    except (ValueError, OSError):
        return False


def format_file_size(size):
    size = float(size)

    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.2f} {unit}"
        size /= 1024

    return f"{size:.2f} GB"


@app.errorhandler(413)
def file_too_large(error):
    return flask.jsonify({
        "success": False,
        "message": "File is too large. Maximum allowed size is 16 MB."
    }), 413


@app.route("/")
def home():
    return flask.render_template("upload.html")


@app.route("/upload", methods=["GET", "POST"])
def upload_file():
    if flask.request.method == "GET":
        return flask.render_template("upload.html")

    uploaded_file = flask.request.files.get("file")

    if uploaded_file is None or not uploaded_file.filename:
        return flask.render_template(
            "report.html",
            filename="No file selected",
            filesize="Unavailable",
            file_hash="Unavailable",
            integrity_status="Analysis not performed",
            metadata={}
        ), 400

    filename = secure_filename(uploaded_file.filename)

    if not filename:
        return flask.jsonify({
            "success": False,
            "message": "Invalid or unsafe file name."
        }), 400

    file_path = os.path.abspath(
        os.path.join(MONITORED_DIRECTORY, filename)
    )

    if not is_safe_path(MONITORED_DIRECTORY, file_path):
        return flask.jsonify({
            "success": False,
            "message": "Unsafe file path detected."
        }), 400

    try:
        uploaded_file.save(file_path)
        metadata = get_file_metadata(file_path)

        if not metadata:
            raise ValueError("File metadata could not be generated.")

        file_size = os.path.getsize(file_path)
        sha256 = metadata.get("sha256", "Unavailable")

        # A hash identifies the current file content.
        # It does not, by itself, prove that the file is unchanged.
        integrity_status = (
            "Analyzed — integrity not independently verified"
        )

        return flask.render_template(
            "report.html",
            filename=metadata.get("filename", filename),
            filesize=format_file_size(file_size),
            file_hash=sha256,
            integrity_status=integrity_status,
            metadata=metadata
        )

    except (OSError, ValueError) as error:
        print("[FIM] File analysis error:", error)

        return flask.jsonify({
            "success": False,
            "message": "Unable to save or analyze the uploaded file."
        }), 500


@app.route("/monitor", methods=["GET"])
def monitor():
    try:
        current_files = scan_directory(MONITORED_DIRECTORY)
        changes = detect_changes(current_files)

        return flask.jsonify({
            "success": True,
            "changes": changes,
            "total_changes": len(changes)
        })

    except Exception as error:
        print("[FIM] Monitoring error:", error)

        return flask.jsonify({
            "success": False,
            "message": "Monitoring operation failed."
        }), 500


@app.route("/events", methods=["GET"])
def events():
    try:
        return flask.render_template(
            "events.html",
            events=get_events()
        )
    except Exception as error:
        print("[FIM] Events page error:", error)
        return "Unable to load security events.", 500


@app.route("/api/events", methods=["GET"])
def events_api():
    try:
        return flask.jsonify({
            "success": True,
            "events": get_events()
        })
    except Exception as error:
        print("[FIM] Events API error:", error)
        return flask.jsonify({
            "success": False,
            "message": "Unable to retrieve security events."
        }), 500
    try:
        return flask.jsonify({
            "success": True,
            "events": get_events()
        })

    except Exception as error:
        print("[FIM] Events error:", error)

        return flask.jsonify({
            "success": False,
            "message": "Unable to retrieve security events."
        }), 500


@app.route("/dashboard")
def dashboard():
    return flask.render_template("dashboard.html")


@app.route("/api/dashboard")
def dashboard_data():
    try:
        return flask.jsonify({
            "success": True,
            "statistics": get_event_statistics(),
            "events": get_events()
        })

    except Exception as error:
        print("[FIM] Dashboard error:", error)

        return flask.jsonify({
            "success": False,
            "message": "Unable to load dashboard data."
        }), 500


@atexit.register
def shutdown_monitor():
    global observer

    if observer is None:
        return

    try:
        observer.stop()
        observer.join(timeout=2)
        print("[FIM] Real-time monitor stopped.")
    except Exception as error:
        print("[FIM] Monitor shutdown error:", error)


if __name__ == "__main__":
    print("=" * 50)
    print(" FILE INTEGRITY MONITOR")
    print(" Project root:", PROJECT_ROOT)
    print(" Templates:", TEMPLATES_FOLDER)
    print(" Static:", STATIC_FOLDER)
    print(" Monitored files:", MONITORED_DIRECTORY)
    print("=" * 50)

    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )