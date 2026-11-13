from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class FileChangeHandler(FileSystemEventHandler):

    def on_created(self, event):
        if not event.is_directory:
            print(f"[CREATED] {event.src_path}")

    def on_modified(self, event):
        if not event.is_directory:
            print(f"[MODIFIED] {event.src_path}")

    def on_deleted(self, event):
        if not event.is_directory:
            print(f"[DELETED] {event.src_path}")


def start_watching(directory):
    event_handler = FileChangeHandler()

    observer = Observer()
    observer.schedule(event_handler, directory, recursive=True)
    observer.start()

    print(f"[*] Monitoring started: {directory}")

    try:
        while True:
            pass
    except KeyboardInterrupt:
        observer.stop()

    observer.join()