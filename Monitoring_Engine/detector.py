from datetime import datetime

from Database.database import (
    get_all_baselines
)


# =========================================
# CURRENT TIMESTAMP
# =========================================

def get_timestamp():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


# =========================================
# DETECT FILE CHANGES
# =========================================

def detect_changes(current_files):

    changes = []

    current_paths = set(
        current_files.keys()
    )

    baselines = get_all_baselines()

    baseline_map = {
        baseline["file_path"]: baseline["sha256"]
        for baseline in baselines
    }

    baseline_paths = set(
        baseline_map.keys()
    )


    # =====================================
    # CREATED / MODIFIED
    # =====================================

    for file_path, current_hash in current_files.items():

        file_path = os_path(file_path)

        # ---------------------------------
        # CREATED
        # ---------------------------------

        if file_path not in baseline_paths:

            changes.append({

                "type": "CREATED",

                "file": file_path,

                "timestamp": get_timestamp()

            })

            continue


        # ---------------------------------
        # MODIFIED
        # ---------------------------------

        old_hash = baseline_map[file_path]

        if old_hash != current_hash:

            changes.append({

                "type": "MODIFIED",

                "file": file_path,

                "timestamp": get_timestamp()

            })


    # =====================================
    # DELETED
    # =====================================

    deleted_paths = (
        baseline_paths -
        current_paths
    )

    for file_path in deleted_paths:

        changes.append({

            "type": "DELETED",

            "file": file_path,

            "timestamp": get_timestamp()

        })


    return changes


# =========================================
# NORMALIZE PATH
# =========================================

def os_path(path):

    import os

    return os.path.abspath(
        str(path)
    )