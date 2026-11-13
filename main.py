
import os
import re
import uuid
import tempfile
from functools import wraps
from datetime import datetime, timezone
from flask_wtf.csrf import CSRFProtect 

import flask
from werkzeug.utils import secure_filename

from Database.database import (
    initialize_database,
    create_user,
    get_user_by_email,
    get_user_by_id,
    save_event,
    verify_user_password,
    save_baseline,
    get_events,
    get_event_statistics,
)

from Monitoring_Engine.file_metadata import get_file_metadata
from Monitoring_Engine.file_scanner import scan_directory
from Monitoring_Engine.detector import detect_changes


# =========================================================
# PATHS AND APPLICATION CONFIGURATION
# =========================================================

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

TEMPLATES_FOLDER = os.path.join(
    PROJECT_ROOT, "Flask_Dashboard", "templates"
)

STATIC_FOLDER = os.path.join(
    PROJECT_ROOT, "Flask_Dashboard", "static"
)

DATA_ROOT = os.environ.get(
    "FIM_DATA_DIRECTORY",
    os.path.join(PROJECT_ROOT, "user_data")
)

os.makedirs(DATA_ROOT, exist_ok=True)

app = flask.Flask(
    __name__,
    template_folder=TEMPLATES_FOLDER,
    static_folder=STATIC_FOLDER
)

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
csrf = CSRFProtect(app) 

secret_key = os.environ.get("SECRET_KEY")

if not secret_key:
    if os.environ.get("FLASK_ENV") == "production":
        raise RuntimeError(
            "SECRET_KEY must be configured in production."
        )

    secret_key = "local-development-key-change-before-deployment"

app.config["SECRET_KEY"] = secret_key
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = (
    os.environ.get("COOKIE_SECURE", "false").lower() == "true"
)
app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 8

initialize_database()

print("[FIM] Database initialized.")


# =========================================================
# USER HELPERS
# =========================================================

def get_user_directory(user_id):
    directory = os.path.realpath(
        os.path.join(DATA_ROOT, str(user_id))
    )

    os.makedirs(directory, exist_ok=True)

    return directory


def get_current_user():
    user_id = flask.session.get("user_id")

    if not user_id:
        return None

    return get_user_by_id(user_id)


@app.context_processor
def inject_user():
    return {
        "current_user": get_current_user()
    }


def login_required(route_function):
    @wraps(route_function)
    def wrapper(*args, **kwargs):
        if not flask.session.get("user_id"):
            flask.flash("Please log in to access your workspace.", "warning")
            return flask.redirect(flask.url_for("login"))

        user = get_current_user()

        if not user:
            flask.session.clear()
            return flask.redirect(flask.url_for("login"))

        return route_function(*args, **kwargs)

    return wrapper


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


def valid_email(email):
    return bool(
        re.fullmatch(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            email
        )
    )


# =========================================================
# PUBLIC AUTHENTICATION ROUTES
# =========================================================

@app.route("/")
def home():
    return flask.render_template("upload.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if flask.session.get("user_id"):
        return flask.redirect(flask.url_for("dashboard"))

    if flask.request.method == "POST":
        username = flask.request.form.get("username", "").strip()
        email = flask.request.form.get("email", "").strip().lower()
        password = flask.request.form.get("password", "")
        confirm_password = flask.request.form.get(
            "confirm_password", ""
        )

        if not username or not email or not password:
            flask.flash("Please complete all required fields.", "error")
            return flask.render_template("register.html")

        if len(username) > 50:
            flask.flash("Username must be 50 characters or fewer.", "error")
            return flask.render_template("register.html")

        if not valid_email(email):
            flask.flash("Please enter a valid email address.", "error")
            return flask.render_template("register.html")

        if len(password) < 12:
            flask.flash(
                "Password must contain at least 12 characters.",
                "error"
            )
            return flask.render_template("register.html")

        if password != confirm_password:
            flask.flash("Passwords do not match.", "error")
            return flask.render_template("register.html")

        user_id = create_user(username, email, password)

        if user_id is None:
            flask.flash(
                "An account with this email already exists.",
                "error"
            )
            return flask.render_template("register.html")

        flask.session.clear()
        flask.session["user_id"] = user_id
        flask.session.permanent = True

        get_user_directory(user_id)

        flask.flash("Your account has been created successfully.", "success")

        return flask.redirect(flask.url_for("dashboard"))

    return flask.render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if flask.session.get("user_id"):
        return flask.redirect(flask.url_for("dashboard"))

    if flask.request.method == "POST":
        email = flask.request.form.get("email", "").strip().lower()
        password = flask.request.form.get("password", "")

        user = get_user_by_email(email)

        if not verify_user_password(user, password):
            flask.flash("Invalid email or password.", "error")
            return flask.render_template("login.html")

        flask.session.clear()
        flask.session["user_id"] = user["id"]
        flask.session.permanent = True

        get_user_directory(user["id"])

        return flask.redirect(flask.url_for("dashboard"))

    return flask.render_template("login.html")


@app.route("/logout", methods=["POST"])
@login_required
def logout():
    flask.session.clear()
    flask.flash("You have been logged out.", "success")

    return flask.redirect(flask.url_for("login"))


# =========================================================
# FILE UPLOAD
# =========================================================

@app.route("/upload", methods=["GET", "POST"])
def upload_file():

    if flask.request.method == "GET":
        return flask.render_template("upload.html")

    uploaded_file = flask.request.files.get("file")

    if uploaded_file is None or not uploaded_file.filename:
        flask.flash("Please select a file first.", "error")
        return flask.redirect(flask.url_for("home"))

    original_filename = secure_filename(uploaded_file.filename)

    if not original_filename:
        flask.flash("Invalid file name.", "error")
        return flask.redirect(flask.url_for("home"))

    user_id = flask.session.get("user_id")

    try:
        # -------------------------------------------------
        # LOGGED-IN USER: SAVE FILE PERMANENTLY
        # -------------------------------------------------

        if user_id:
            user_directory = get_user_directory(user_id)

            stored_filename = (
                f"{uuid.uuid4().hex}_{original_filename}"
            )

            file_path = os.path.abspath(
                os.path.join(user_directory, stored_filename)
            )

            if not is_safe_path(user_directory, file_path):
                flask.abort(400)

            uploaded_file.save(file_path)

            metadata = get_file_metadata(file_path)

            if not metadata:
                raise ValueError("File metadata could not be generated.")

            file_size = os.path.getsize(file_path)
            sha256 = metadata.get("sha256")

            if not sha256:
                raise ValueError("SHA-256 hash is unavailable.")

            timestamp = datetime.now(timezone.utc).isoformat()

            save_baseline(
                file_path,
                sha256,
                timestamp,
                user_id
            )
            save_event({
                 "type": "CREATED",
                 "file": file_path,
                  "timestamp": timestamp
                      }, user_id)

            metadata["filename"] = original_filename

            return flask.render_template(
                "report.html",
                filename=original_filename,
                filesize=format_file_size(file_size),
                file_hash=sha256,
                integrity_status="Baseline saved to your account",
                metadata=metadata
            )

        # -------------------------------------------------
        # GUEST USER: TEMPORARY ANALYSIS ONLY
        # -------------------------------------------------

        with tempfile.TemporaryDirectory(
            prefix="fim_guest_"
        ) as temporary_directory:

            stored_filename = (
                f"{uuid.uuid4().hex}_{original_filename}"
            )

            file_path = os.path.abspath(
                os.path.join(temporary_directory, stored_filename)
            )

            if not is_safe_path(temporary_directory, file_path):
                flask.abort(400)

            uploaded_file.save(file_path)

            metadata = get_file_metadata(file_path)

            if not metadata:
                raise ValueError("File metadata could not be generated.")

            file_size = os.path.getsize(file_path)
            sha256 = metadata.get("sha256", "Unavailable")

            metadata["filename"] = original_filename

            # Render the report before the temporary directory
            # is automatically deleted.
            response = flask.render_template(
                "report.html",
                filename=original_filename,
                filesize=format_file_size(file_size),
                file_hash=sha256,
                integrity_status="Guest analysis — not saved",
                metadata=metadata
            )

        return response

    except (OSError, ValueError) as error:
        print("[FIM] Upload analysis error:", error)

        flask.flash(
            "Unable to analyze this file.",
            "error"
        )

        return flask.redirect(flask.url_for("home"))

# =========================================================
# EVENTS
# =========================================================

@app.route("/events", methods=["GET"])
@login_required
def events():
    user_id = flask.session["user_id"]

    try:
        return flask.render_template(
            "events.html",
            events=get_events(user_id)
        )

    except Exception as error:
        print("[FIM] Events page error:", error)
        return "Unable to load security events.", 500


@app.route("/api/events", methods=["GET"])
@login_required
def events_api():
    user_id = flask.session["user_id"]

    try:
        return flask.jsonify({
            "success": True,
            "events": get_events(user_id)
        })

    except Exception as error:
        print("[FIM] Events API error:", error)

        return flask.jsonify({
            "success": False,
            "message": "Unable to retrieve security events."
        }), 500


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    return flask.render_template("dashboard.html")


@app.route("/api/dashboard", methods=["GET"])
@login_required
def dashboard_data():
    user_id = flask.session["user_id"]

    try:
        return flask.jsonify({
            "success": True,
            "statistics": get_event_statistics(user_id),
            "events": get_events(user_id)
        })

    except Exception as error:
        print("[FIM] Dashboard error:", error)

        return flask.jsonify({
            "success": False,
            "message": "Unable to load dashboard data."
        }), 500


# =========================================================
# ERROR HANDLERS
# =========================================================

@app.errorhandler(413)
def file_too_large(error):
    return flask.jsonify({
        "success": False,
        "message": "File is too large. Maximum allowed size is 16 MB."
    }), 413


# =========================================================
# APPLICATION START
# =========================================================

if __name__ == "__main__":
    print("=" * 50)
    print(" FILE INTEGRITY MONITOR")
    print(" Project root:", PROJECT_ROOT)
    print(" Templates:", TEMPLATES_FOLDER)
    print(" Static:", STATIC_FOLDER)
    print(" User data:", DATA_ROOT)
    print("=" * 50)

    port = int(os.environ.get("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )
