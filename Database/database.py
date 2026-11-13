
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)

DATABASE_NAME = os.environ.get(
    "FIM_DATABASE_PATH",
    os.path.join(PROJECT_ROOT, "fim.db")
)


def get_connection():
    database_directory = os.path.dirname(DATABASE_NAME)

    if database_directory:
        os.makedirs(database_directory, exist_ok=True)

    connection = sqlite3.connect(
        DATABASE_NAME,
        timeout=10
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")

    return connection


# =========================================================
# DATABASE INITIALIZATION AND MIGRATION
# =========================================================

def initialize_database():
    connection = get_connection()

    try:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                file_path TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_id INTEGER
            )
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS file_baseline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT UNIQUE NOT NULL,
                sha256 TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                user_id INTEGER
            )
        """)

        # Add user_id to existing databases if necessary.
        event_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(events)"
            ).fetchall()
        }

        if "user_id" not in event_columns:
            connection.execute(
                "ALTER TABLE events ADD COLUMN user_id INTEGER"
            )

        baseline_columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(file_baseline)"
            ).fetchall()
        }

        if "user_id" not in baseline_columns:
            connection.execute(
                "ALTER TABLE file_baseline ADD COLUMN user_id INTEGER"
            )

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_events_user
            ON events(user_id, id DESC)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_baseline_user
            ON file_baseline(user_id)
        """)

        connection.commit()

    finally:
        connection.close()


# =========================================================
# USER ACCOUNT FUNCTIONS
# =========================================================

def create_user(username, email, password):
    connection = get_connection()

    try:
        from datetime import datetime, timezone

        normalized_email = email.strip().lower()
        normalized_username = username.strip()

        password_hash = generate_password_hash(password)

        cursor = connection.execute("""
            INSERT INTO users (
                username,
                email,
                password_hash,
                created_at
            )
            VALUES (?, ?, ?, ?)
        """, (
            normalized_username,
            normalized_email,
            password_hash,
            datetime.now(timezone.utc).isoformat()
        ))

        connection.commit()

        return cursor.lastrowid

    except sqlite3.IntegrityError:
        return None

    finally:
        connection.close()


def get_user_by_email(email):
    connection = get_connection()

    try:
        user = connection.execute("""
            SELECT id, username, email, password_hash, created_at
            FROM users
            WHERE email = ?
        """, (email.strip().lower(),)).fetchone()

        return dict(user) if user else None

    finally:
        connection.close()


def get_user_by_id(user_id):
    connection = get_connection()

    try:
        user = connection.execute("""
            SELECT id, username, email, created_at
            FROM users
            WHERE id = ?
        """, (user_id,)).fetchone()

        return dict(user) if user else None

    finally:
        connection.close()


def verify_user_password(user, password):
    if not user:
        return False

    return check_password_hash(
        user["password_hash"],
        password
    )


# =========================================================
# SECURITY EVENT FUNCTIONS
# =========================================================

def save_event(event, user_id):
    connection = get_connection()

    try:
        connection.execute("""
            INSERT INTO events (
                event_type,
                file_path,
                timestamp,
                user_id
            )
            VALUES (?, ?, ?, ?)
        """, (
            event["type"],
            event["file"],
            event["timestamp"],
            user_id
        ))

        connection.commit()

    finally:
        connection.close()


def get_events(user_id):
    connection = get_connection()

    try:
        events = connection.execute("""
            SELECT
                id,
                event_type,
                file_path,
                timestamp
            FROM events
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,)).fetchall()

        return [dict(event) for event in events]

    finally:
        connection.close()


def get_event_statistics(user_id):
    connection = get_connection()

    try:
        total = connection.execute("""
            SELECT COUNT(*) AS count
            FROM events
            WHERE user_id = ?
        """, (user_id,)).fetchone()["count"]

        created = connection.execute("""
            SELECT COUNT(*) AS count
            FROM events
            WHERE user_id = ? AND event_type = 'CREATED'
        """, (user_id,)).fetchone()["count"]

        modified = connection.execute("""
            SELECT COUNT(*) AS count
            FROM events
            WHERE user_id = ? AND event_type = 'MODIFIED'
        """, (user_id,)).fetchone()["count"]

        deleted = connection.execute("""
            SELECT COUNT(*) AS count
            FROM events
            WHERE user_id = ? AND event_type = 'DELETED'
        """, (user_id,)).fetchone()["count"]

        baseline_files = connection.execute("""
            SELECT COUNT(*) AS count
            FROM file_baseline
            WHERE user_id = ?
        """, (user_id,)).fetchone()["count"]

        return {
            "total": total,
            "created": created,
            "modified": modified,
            "deleted": deleted,
            "baseline_files": baseline_files
        }

    finally:
        connection.close()


# =========================================================
# FILE BASELINE FUNCTIONS
# =========================================================

def save_baseline(file_path, sha256, timestamp, user_id):
    connection = get_connection()

    try:
        connection.execute("""
            INSERT INTO file_baseline (
                file_path,
                sha256,
                timestamp,
                user_id
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(file_path)
            DO UPDATE SET
                sha256 = excluded.sha256,
                timestamp = excluded.timestamp,
                user_id = excluded.user_id
        """, (
            file_path,
            sha256,
            timestamp,
            user_id
        ))

        connection.commit()

    finally:
        connection.close()


def get_baseline(file_path, user_id):
    connection = get_connection()

    try:
        baseline = connection.execute("""
            SELECT file_path, sha256, timestamp
            FROM file_baseline
            WHERE file_path = ? AND user_id = ?
        """, (
            file_path,
            user_id
        )).fetchone()

        return dict(baseline) if baseline else None

    finally:
        connection.close()


def get_all_baselines(user_id):
    connection = get_connection()

    try:
        baselines = connection.execute("""
            SELECT file_path, sha256, timestamp
            FROM file_baseline
            WHERE user_id = ?
            ORDER BY id DESC
        """, (user_id,)).fetchall()

        return [dict(item) for item in baselines]

    finally:
        connection.close()


def delete_baseline(file_path, user_id):
    connection = get_connection()

    try:
        connection.execute("""
            DELETE FROM file_baseline
            WHERE file_path = ? AND user_id = ?
        """, (
            file_path,
            user_id
        ))

        connection.commit()

    finally:
        connection.close()
