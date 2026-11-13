
import sqlite3
import os

# =========================================
# DATABASE PATH
# =========================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

DATABASE_NAME = os.environ.get(
    "FIM_DATABASE_PATH",
    os.path.join(PROJECT_ROOT, "fim.db")
)


# =========================================
# DATABASE CONNECTION
# =========================================

def get_connection():

    database_directory = os.path.dirname(DATABASE_NAME)

    if database_directory:
        os.makedirs(database_directory, exist_ok=True)

    connection = sqlite3.connect(
        DATABASE_NAME,
        timeout=10
    )

    connection.row_factory = sqlite3.Row

    return connection


# =========================================
# INITIALIZE DATABASE
# =========================================

def initialize_database():

    connection = get_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS file_baseline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                sha256 TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)

        connection.commit()

    finally:
        connection.close()


# =========================================
# SAVE SECURITY EVENT
# =========================================

def save_event(event):

    connection = get_connection()

    try:
        connection.execute("""
            INSERT INTO events (
                event_type,
                file_path,
                timestamp
            )
            VALUES (?, ?, ?)
        """, (
            event["type"],
            event["file"],
            event["timestamp"]
        ))

        connection.commit()

    finally:
        connection.close()


# =========================================
# GET ALL SECURITY EVENTS
# =========================================

def get_events():

    connection = get_connection()

    try:
        events = connection.execute("""
            SELECT
                id,
                event_type,
                file_path,
                timestamp
            FROM events
            ORDER BY id DESC
        """).fetchall()

        return [dict(event) for event in events]

    finally:
        connection.close()


# =========================================
# GET EVENT STATISTICS
# =========================================

def get_event_statistics():

    connection = get_connection()

    try:
        total = connection.execute("""
            SELECT COUNT(*) AS count
            FROM events
        """).fetchone()["count"]

        created = connection.execute("""
            SELECT COUNT(*) AS count
            FROM events
            WHERE event_type = 'CREATED'
        """).fetchone()["count"]

        modified = connection.execute("""
            SELECT COUNT(*) AS count
            FROM events
            WHERE event_type = 'MODIFIED'
        """).fetchone()["count"]

        deleted = connection.execute("""
            SELECT COUNT(*) AS count
            FROM events
            WHERE event_type = 'DELETED'
        """).fetchone()["count"]

        baseline_files = connection.execute("""
            SELECT COUNT(*) AS count
            FROM file_baseline
        """).fetchone()["count"]

        return {
            "total": total,
            "created": created,
            "modified": modified,
            "deleted": deleted,
            "baseline_files": baseline_files
        }

    finally:
        connection.close()


# =========================================
# SAVE FILE BASELINE
# =========================================

def save_baseline(file_path, sha256, timestamp):

    connection = get_connection()

    try:
        connection.execute("""
            INSERT OR REPLACE INTO file_baseline (
                file_path,
                sha256,
                timestamp
            )
            VALUES (?, ?, ?)
        """, (
            file_path,
            sha256,
            timestamp
        ))

        connection.commit()

    finally:
        connection.close()


# =========================================
# GET FILE BASELINE
# =========================================

def get_baseline(file_path):

    connection = get_connection()

    try:
        baseline = connection.execute("""
            SELECT
                file_path,
                sha256,
                timestamp
            FROM file_baseline
            WHERE file_path = ?
        """, (file_path,)).fetchone()

        return dict(baseline) if baseline else None

    finally:
        connection.close()


# =========================================
# GET ALL BASELINES
# =========================================

def get_all_baselines():

    connection = get_connection()

    try:
        baselines = connection.execute("""
            SELECT
                file_path,
                sha256,
                timestamp
            FROM file_baseline
            ORDER BY id DESC
        """).fetchall()

        return [dict(baseline) for baseline in baselines]

    finally:
        connection.close()


# =========================================
# DELETE FILE BASELINE
# =========================================

def delete_baseline(file_path):

    connection = get_connection()

    try:
        connection.execute("""
            DELETE FROM file_baseline
            WHERE file_path = ?
        """, (file_path,))

        connection.commit()

    finally:
        connection.close()
