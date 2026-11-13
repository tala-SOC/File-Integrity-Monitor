
import os
from datetime import datetime, timezone

from Database.database import (
    get_all_baselines,
    save_baseline,
    save_event,
    delete_baseline
)


def normalize_path(path):
    """Normalize paths to make comparisons consistent."""
    return os.path.normcase(
        os.path.realpath(os.path.abspath(path))
    )


def detect_changes(current_files, user_id):
    """
    Compare current file hashes with the authenticated user's
    saved baselines.

    current_files format:
        {
            absolute_file_path: sha256_hash
        }
    """

    timestamp = datetime.now(timezone.utc).isoformat()

    # Retrieve only this user's saved baselines.
    saved_baselines = get_all_baselines(user_id)

    baseline_map = {
        normalize_path(item["file_path"]): item
        for item in saved_baselines
    }

    current_map = {
        normalize_path(path): {
            "path": path,
            "hash": file_hash
        }
        for path, file_hash in current_files.items()
    }

    changes = []

    # -----------------------------------------------------
    # CREATED / MODIFIED FILES
    # -----------------------------------------------------

    for normalized_path, current in current_map.items():

        file_path = current["path"]
        current_hash = current["hash"]

        previous = baseline_map.get(normalized_path)

        if previous is None:
            event_type = "CREATED"

            save_baseline(
                file_path,
                current_hash,
                timestamp,
                user_id
            )

            event = {
                "type": event_type,
                "file": file_path,
                "timestamp": timestamp
            }

            save_event(event, user_id)
            changes.append(event)

        elif previous["sha256"] != current_hash:
            event_type = "MODIFIED"

            save_baseline(
                file_path,
                current_hash,
                timestamp,
                user_id
            )

            event = {
                "type": event_type,
                "file": file_path,
                "timestamp": timestamp
            }

            save_event(event, user_id)
            changes.append(event)

    # -----------------------------------------------------
    # DELETED FILES
    # -----------------------------------------------------

    for normalized_path, previous in baseline_map.items():

        if normalized_path not in current_map:

            file_path = previous["file_path"]

            event = {
                "type": "DELETED",
                "file": file_path,
                "timestamp": timestamp
            }

            save_event(event, user_id)
            delete_baseline(file_path, user_id)

            changes.append(event)

    return changes
