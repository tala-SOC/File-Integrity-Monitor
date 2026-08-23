import os
import atexit
import flask
from werkzeug.utils import secure_filename


# =========================================================
# PROJECT PATHS
# =========================================================

PROJECT_ROOT = os.path.abspath(
    os.path.dirname(__file__)
)

TEMPLATES_FOLDER = os.path.join(
    PROJECT_ROOT,
    "Flask_Dashboard",
    "templates"
)

STATIC_FOLDER = os.path.join(
    PROJECT_ROOT,
    "Flask_Dashboard",
    "static"
)

MONITORED_DIRECTORY = os.path.join(
    PROJECT_ROOT,
    "monitored_files"
)


# =========================================================
# FLASK APP
# =========================================================

app = flask.Flask(
    __name__,
    template_folder=TEMPLATES_FOLDER,
    static_folder=STATIC_FOLDER
)


# =========================================================
# SECURITY CONFIGURATION
# =========================================================

app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024


# =========================================================
# PROJECT MODULES
# =========================================================

from Database.database import (
    initialize_database,
    get_events,
    get_event_statistics
)

from Monitoring_Engine.file_metadata import (
    get_file_metadata
)

from Monitoring_Engine.file_scanner import (
    scan_directory
)

from Monitoring_Engine.detector import (
    detect_changes
)


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

try:
    initialize_database()

    print("[FIM] Database initialized successfully.")

except Exception as error:

    print(
        "[FIM] Database initialization error:",
        error
    )


# =========================================================
# MONITORED DIRECTORY
# =========================================================

os.makedirs(
    MONITORED_DIRECTORY,
    exist_ok=True
)

print(
    "[FIM] Monitoring directory:",
    MONITORED_DIRECTORY
)


# =========================================================
# REAL-TIME MONITOR
# =========================================================

observer = None

try:

    from Monitoring_Engine.realtime_monitor import (
        start_realtime_monitor
    )

    observer = start_realtime_monitor(
        MONITORED_DIRECTORY
    )

    print(
        "[FIM] Real-time monitoring started."
    )

except Exception as error:

    print(
        "[FIM] Real-time monitor could not start:",
        error
    )

    print(
        "[FIM] Flask will continue without real-time monitoring."
    )


# =========================================================
# SAFE PATH CHECK
# =========================================================

def is_safe_path(
    base_directory,
    target_path
):

    try:

        base_directory = os.path.realpath(
            base_directory
        )

        target_path = os.path.realpath(
            target_path
        )

        return os.path.commonpath(
            [
                base_directory,
                target_path
            ]
        ) == base_directory

    except (
        ValueError,
        OSError
    ):

        return False


# =========================================================
# FILE SIZE ERROR
# =========================================================

@app.errorhandler(413)
def file_too_large(error):

    return flask.jsonify({

        "success": False,

        "message":
            "File is too large. Maximum allowed size is 16 MB."

    }), 413


# =========================================================
# HOME PAGE
# =========================================================

@app.route("/")
def home():

    return flask.render_template(
        "upload.html"
    )


# =========================================================
# UPLOAD / ANALYZE FILE
# =========================================================

@app.route(
    "/upload",
    methods=["GET", "POST"]
)
def upload_file():

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    if flask.request.method == "GET":

        return flask.render_template(
            "upload.html"
        )


    # -----------------------------------------------------
    # GET UPLOADED FILE
    # -----------------------------------------------------

    uploaded_file = flask.request.files.get(
        "file"
    )

    if uploaded_file is None:

        return flask.jsonify({

            "success": False,

            "message":
                "No file selected."

        }), 400


    # -----------------------------------------------------
    # ORIGINAL FILE NAME
    # -----------------------------------------------------

    original_filename = (
        uploaded_file.filename
    )

    if not original_filename:

        return flask.jsonify({

            "success": False,

            "message":
                "Invalid file name."

        }), 400


    # -----------------------------------------------------
    # SECURE FILE NAME
    # -----------------------------------------------------

    filename = secure_filename(
        original_filename
    )

    if not filename:

        return flask.jsonify({

            "success": False,

            "message":
                "Invalid or unsafe file name."

        }), 400


    # -----------------------------------------------------
    # FILE PATH
    # -----------------------------------------------------

    file_path = os.path.abspath(
        os.path.join(
            MONITORED_DIRECTORY,
            filename
        )
    )


    # -----------------------------------------------------
    # PATH TRAVERSAL PROTECTION
    # -----------------------------------------------------

    if not is_safe_path(
        MONITORED_DIRECTORY,
        file_path
    ):

        return flask.jsonify({

            "success": False,

            "message":
                "Unsafe file path detected."

        }), 400


    # -----------------------------------------------------
    # SAVE FILE
    # -----------------------------------------------------

    try:

        uploaded_file.save(
            file_path
        )

    except (
        OSError,
        PermissionError
    ) as error:

        print(
            "[FIM] File save error:",
            error
        )

        return flask.jsonify({

            "success": False,

            "message":
                "Unable to save uploaded file."

        }), 500


    # -----------------------------------------------------
    # ANALYZE FILE METADATA
    # -----------------------------------------------------

    try:

        metadata = get_file_metadata(
            file_path
        )

    except Exception as error:

        print(
            "[FIM] Metadata error:",
            error
        )

        return flask.jsonify({

            "success": False,

            "message":
                "Metadata analysis failed."

        }), 500


    if metadata is None:

        return flask.jsonify({

            "success": False,

            "message":
                "Unable to analyze file."

        }), 500


    # -----------------------------------------------------
    # FILE SIZE
    # -----------------------------------------------------

    try:

        file_size = os.path.getsize(
            file_path
        )

    except OSError:

        file_size = metadata.get(
            "file_size",
            metadata.get(
                "size",
                0
            )
        )


    # -----------------------------------------------------
    # DEFAULT STATUS
    # -----------------------------------------------------

    file_status = "ANALYZED"

    changes = []


    # -----------------------------------------------------
    # FIND RELATED EVENTS
    # -----------------------------------------------------

    try:

        events_data = get_events()

        for event in events_data:

            # Support dictionary events
            if isinstance(event, dict):

                event_file = os.path.abspath(
                    str(
                        event.get(
                            "file_path",
                            ""
                        )
                    )
                )

                event_type = event.get(
                    "event_type",
                    "ANALYZED"
                )

                event_timestamp = event.get(
                    "timestamp",
                    ""
                )

            # Support tuple/list events
            elif isinstance(
                event,
                (tuple, list)
            ) and len(event) >= 4:

                event_file = os.path.abspath(
                    str(
                        event[2]
                    )
                )

                event_type = event[1]

                event_timestamp = event[3]

            else:

                continue


            if event_file == file_path:

                file_status = event_type

                changes.append({

                    "type":
                        event_type,

                    "file":
                        event_file,

                    "timestamp":
                        event_timestamp

                })

                break


    except Exception as error:

        print(
            "[FIM] Event lookup error:",
            error
        )


    # =====================================================
    # RESPONSE
    # =====================================================

    return flask.jsonify({

        "success": True,

        "filename":
            metadata.get(
                "filename",
                filename
            ),

        "size":
            file_size,

        "extension":
            metadata.get(
                "extension",
                ""
            ),

        "mime_type":
            metadata.get(
                "mime_type",
                ""
            ),

        "file_path":
            metadata.get(
                "file_path",
                file_path
            ),

        "created":
            metadata.get(
                "created"
            ),

        "modified":
            metadata.get(
                "modified"
            ),

        "accessed":
            metadata.get(
                "accessed"
            ),

        "md5":
            metadata.get(
                "md5"
            ),

        "sha1":
            metadata.get(
                "sha1"
            ),

        "sha256":
            metadata.get(
                "sha256"
            ),

        "signature":
            metadata.get(
                "signature"
            ),

        "entropy":
            metadata.get(
                "entropy"
            ),

        "integrity_status":
            file_status,

        "changes":
            changes

    })


# =========================================================
# MONITOR API
# =========================================================

@app.route(
    "/monitor",
    methods=["GET"]
)
def monitor():

    try:

        current_files = scan_directory(
            MONITORED_DIRECTORY
        )

        changes = detect_changes(
            current_files
        )

        return flask.jsonify({

            "success": True,

            "changes":
                changes,

            "total_changes":
                len(changes)

        })

    except Exception as error:

        print(
            "[FIM] Monitoring error:",
            error
        )

        return flask.jsonify({

            "success": False,

            "message":
                "Monitoring operation failed."

        }), 500


# =========================================================
# EVENTS API
# =========================================================

@app.route(
    "/events",
    methods=["GET"]
)
def events():

    try:

        events_data = get_events()

        return flask.jsonify({

            "success": True,

            "events":
                events_data

        })

    except Exception as error:

        print(
            "[FIM] Events error:",
            error
        )

        return flask.jsonify({

            "success": False,

            "message":
                "Unable to retrieve security events."

        }), 500


# =========================================================
# DASHBOARD PAGE
# =========================================================

@app.route("/dashboard")
def dashboard():

    return flask.render_template(
        "dashboard.html"
    )


# =========================================================
# DASHBOARD API
# =========================================================

@app.route("/api/dashboard")
def dashboard_data():

    try:

        statistics = get_event_statistics()

        events_data = get_events()

        return flask.jsonify({

            "success": True,

            "statistics":
                statistics,

            "events":
                events_data

        })

    except Exception as error:

        print(
            "[FIM] Dashboard error:",
            error
        )

        return flask.jsonify({

            "success": False,

            "message":
                "Unable to load dashboard data."

        }), 500


# =========================================================
# SHUTDOWN REAL-TIME MONITOR
# =========================================================

@atexit.register
def shutdown_monitor():

    global observer

    if observer is None:
        return

    try:

        observer.stop()

        observer.join(
            timeout=2
        )

        print(
            "[FIM] Real-time monitor stopped."
        )

    except Exception as error:

        print(
            "[FIM] Monitor shutdown error:",
            error
        )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":

    print()
    print("=" * 60)
    print(" FILE INTEGRITY MONITOR")
    print("=" * 60)
    print(
        "[FIM] Project root:",
        PROJECT_ROOT
    )
    print(
        "[FIM] Templates:",
        TEMPLATES_FOLDER
    )
    print(
        "[FIM] Static:",
        STATIC_FOLDER
    )
    print(
        "[FIM] Monitored files:",
        MONITORED_DIRECTORY
    )
    print("=" * 60)
    print()

    # جلب Port ديناميكياً من بيئة Render مع جعل 0.0.0.0 هو العنوان
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False,
        use_reloader=False
    )