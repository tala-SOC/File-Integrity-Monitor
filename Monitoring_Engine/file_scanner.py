import os
from Monitoring_Engine.hasher import calculate_hash


def scan_directory(directory):
    files = {}

    if not os.path.exists(directory):
        return files

    for root, _, filenames in os.walk(directory):
        for filename in filenames:
            file_path = os.path.abspath(os.path.join(root, filename))

            file_hash = calculate_hash(file_path)

            if file_hash:
                files[file_path] = file_hash

    return files