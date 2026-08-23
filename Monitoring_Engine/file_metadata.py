
import os
import hashlib
import mimetypes
import math
from datetime import datetime


# =========================================
# HASH CALCULATION
# =========================================

def calculate_file_hashes(file_path):

    md5 = hashlib.md5()
    sha1 = hashlib.sha1()
    sha256 = hashlib.sha256()

    try:

        with open(file_path, "rb") as file:

            while True:

                chunk = file.read(4096)

                if not chunk:
                    break

                md5.update(chunk)
                sha1.update(chunk)
                sha256.update(chunk)

        return {
            "md5": md5.hexdigest(),
            "sha1": sha1.hexdigest(),
            "sha256": sha256.hexdigest()
        }

    except (FileNotFoundError, PermissionError, OSError):

        return None


# =========================================
# FILE ENTROPY
# =========================================
def calculate_entropy(file_path):

    try:

        # Read only a 1 MB sample
        # to keep analysis fast for large files
        max_sample_size = 1024 * 1024

        with open(file_path, "rb") as file:

            data = file.read(
                max_sample_size
            )


        # Empty file
        if not data:

            return 0.0


        # Frequency table for all
        # possible byte values
        frequency = [0] * 256


        for byte in data:

            frequency[byte] += 1


        data_length = len(data)

        entropy = 0.0


        # Shannon Entropy
        for count in frequency:

            if count == 0:

                continue


            probability = (
                count / data_length
            )


            entropy -= (
                probability *
                math.log2(probability)
            )


        return round(
            entropy,
            4
        )


    except (
        FileNotFoundError,
        PermissionError,
        OSError
    ):

        return None

# =========================================
# FILE SIGNATURE
# =========================================

def detect_file_signature(file_path):

    signatures = {

        b"%PDF": "PDF Document",

        b"\x89PNG\r\n\x1a\n": "PNG Image",

        b"\xff\xd8\xff": "JPEG Image",

        b"GIF87a": "GIF Image",

        b"GIF89a": "GIF Image",

        b"PK\x03\x04": "ZIP Archive",

        b"PK\x05\x06": "ZIP Archive",

        b"PK\x07\x08": "ZIP Archive",

        b"MZ": "Windows Executable",

        b"\x7fELF": "ELF Executable",

    }

    try:

        with open(file_path, "rb") as file:

            header = file.read(16)

        for signature, file_type in signatures.items():

            if header.startswith(signature):

                return file_type

        return "Unknown"

    except (FileNotFoundError, PermissionError):

        return None


# =========================================
# FILE METADATA
# =========================================

def get_file_metadata(file_path):

    try:

        if not os.path.isfile(file_path):

            return None


        # Absolute path

        absolute_path = os.path.abspath(
            file_path
        )


        # File name

        filename = os.path.basename(
            absolute_path
        )


        # Extension

        extension = os.path.splitext(
            filename
        )[1].lower()


        # File size

        file_size = os.path.getsize(
            absolute_path
        )


        # MIME type

        mime_type, _ = mimetypes.guess_type(
            filename
        )

        if mime_type is None:

            mime_type = "Unknown"


        # Timestamps

        created_timestamp = os.path.getctime(
            absolute_path
        )

        modified_timestamp = os.path.getmtime(
            absolute_path
        )

        accessed_timestamp = os.path.getatime(
            absolute_path
        )


        # Convert timestamps

        created_time = datetime.fromtimestamp(
            created_timestamp
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        modified_time = datetime.fromtimestamp(
            modified_timestamp
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        )

        accessed_time = datetime.fromtimestamp(
            accessed_timestamp
        ).strftime(
            "%Y-%m-%d %H:%M:%S"
        )


        # Hashes

        hashes = calculate_file_hashes(
            absolute_path
        )


        # File signature

        signature = detect_file_signature(
            absolute_path
        )


        # Entropy

        entropy = calculate_entropy(
            absolute_path
        )


        # Return complete metadata

        return {

            "filename":
                filename,

            "extension":
                extension,

            "file_path":
                absolute_path,

            "file_size":
                file_size,

            "mime_type":
                mime_type,

            "created":
                created_time,

            "modified":
                modified_time,

            "accessed":
                accessed_time,

            "md5":
                hashes["md5"] if hashes else None,

            "sha1":
                hashes["sha1"] if hashes else None,

            "sha256":
                hashes["sha256"] if hashes else None,

            "signature":
                signature,

            "entropy":
                entropy

        }


    except (
        FileNotFoundError,
        PermissionError,
        OSError
    ):

        return None