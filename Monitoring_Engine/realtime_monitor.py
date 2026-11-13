import os
import time

from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from Database.database import (
    save_event,
    save_baseline,
    get_baseline,
    delete_baseline
)

from Monitoring_Engine.hasher import (
    calculate_hash
)


# =========================================
# EVENT DEBOUNCE
# =========================================

DEBOUNCE_SECONDS = 1.0


# =========================================
# REAL-TIME FILE EVENT HANDLER
# =========================================

class FIMEventHandler(
    FileSystemEventHandler
):

    def __init__(self):

        super().__init__()

        self.recent_events = {}

        self.created_files = {}


    # =====================================
    # TIMESTAMP
    # =====================================

    def get_timestamp(self):

        return datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )


    # =====================================
    # CHECK DUPLICATE EVENT
    # =====================================

    def is_duplicate(
        self,
        file_path,
        event_type
    ):

        key = (
            file_path,
            event_type
        )

        now = time.time()

        previous_time = self.recent_events.get(
            key
        )

        if previous_time is not None:

            if (
                now - previous_time
                < DEBOUNCE_SECONDS
            ):

                return True

        self.recent_events[key] = now

        return False


    # =====================================
    # CREATED
    # =====================================

    def on_created(self, event):

        if event.is_directory:
            return

        file_path = os.path.abspath(
            event.src_path
        )

        self.handle_created(
            file_path
        )


    # =====================================
    # MODIFIED
    # =====================================

    def on_modified(self, event):

        if event.is_directory:
            return

        file_path = os.path.abspath(
            event.src_path
        )

        self.handle_modified(
            file_path
        )


    # =====================================
    # DELETED
    # =====================================

    def on_deleted(self, event):

        if event.is_directory:
            return

        file_path = os.path.abspath(
            event.src_path
        )

        self.handle_deleted(
            file_path
        )


    # =====================================
    # CREATED HANDLER
    # =====================================

    def handle_created(
        self,
        file_path
    ):

        if not os.path.isfile(
            file_path
        ):

            return


        if self.is_duplicate(
            file_path,
            "CREATED"
        ):

            return


        try:

            current_hash = calculate_hash(
                file_path
            )

        except Exception as error:

            print(
                "[FIM] Created hash error:",
                error
            )

            return


        if not current_hash:
            return


        existing_baseline = get_baseline(
            file_path
        )


        # Already monitored
        if existing_baseline:

            return


        timestamp = self.get_timestamp()


        event_data = {

            "type":
                "CREATED",

            "file":
                file_path,

            "timestamp":
                timestamp

        }


        save_event(
            event_data
        )


        save_baseline(
            file_path,
            current_hash,
            timestamp
        )


        self.created_files[
            file_path
        ] = time.time()


        print(
            f"[FIM] CREATED: {file_path}"
        )


    # =====================================
    # MODIFIED HANDLER
    # =====================================

    def handle_modified(
        self,
        file_path
    ):

        if not os.path.isfile(
            file_path
        ):

            return


        # ---------------------------------
        # Ignore modification immediately
        # after file creation
        # ---------------------------------

        created_time = self.created_files.get(
            file_path
        )

        if created_time is not None:

            if (
                time.time() - created_time
                < DEBOUNCE_SECONDS
            ):

                return


            del self.created_files[
                file_path
            ]


        if self.is_duplicate(
            file_path,
            "MODIFIED"
        ):

            return


        try:

            current_hash = calculate_hash(
                file_path
            )

        except Exception as error:

            print(
                "[FIM] Modified hash error:",
                error
            )

            return


        if not current_hash:
            return


        old_baseline = get_baseline(
            file_path
        )


        # ---------------------------------
        # File not monitored yet
        # ---------------------------------

        if old_baseline is None:

            self.handle_created(
                file_path
            )

            return


        old_hash = old_baseline[
            "sha256"
        ]


        # ---------------------------------
        # No real content change
        # ---------------------------------

        if old_hash == current_hash:

            return


        timestamp = self.get_timestamp()


        event_data = {

            "type":
                "MODIFIED",

            "file":
                file_path,

            "timestamp":
                timestamp

        }


        save_event(
            event_data
        )


        save_baseline(
            file_path,
            current_hash,
            timestamp
        )


        print(
            f"[FIM] MODIFIED: {file_path}"
        )


    # =====================================
    # DELETED HANDLER
    # =====================================

    def handle_deleted(
        self,
        file_path
    ):

        if self.is_duplicate(
            file_path,
            "DELETED"
        ):

            return


        old_baseline = get_baseline(
            file_path
        )


        # File was not monitored
        if old_baseline is None:

            return


        timestamp = self.get_timestamp()


        event_data = {

            "type":
                "DELETED",

            "file":
                file_path,

            "timestamp":
                timestamp

        }


        save_event(
            event_data
        )


        delete_baseline(
            file_path
        )


        self.created_files.pop(
            file_path,
            None
        )


        print(
            f"[FIM] DELETED: {file_path}"
        )


# =========================================
# START REAL-TIME MONITOR
# =========================================

def start_realtime_monitor(
    monitored_directory
):

    event_handler = FIMEventHandler()

    observer = Observer()


    observer.schedule(
        event_handler,
        monitored_directory,
        recursive=True
    )


    observer.start()


    print(
        "[FIM] Real-time monitoring started."
    )

    print(
        f"[FIM] Monitoring: {monitored_directory}"
    )

    return observer