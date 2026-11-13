
# File Integrity Monitor (FIM)

A real-time file integrity monitoring system built with Python, Flask, SQLite, and Watchdog.

The system monitors a designated directory for file creation, modification, and deletion events. It uses SHA-256 hashing and file baselines to detect integrity changes and records security events in a local SQLite database.

---

## Overview

File Integrity Monitoring (FIM) is a security mechanism used to detect unauthorized or unexpected changes to files.

This project provides a lightweight FIM implementation capable of:

- Monitoring files in real time
- Detecting file creation
- Detecting file modification
- Detecting file deletion
- Comparing SHA-256 file hashes
- Maintaining file integrity baselines
- Recording security events
- Extracting detailed file metadata
- Calculating file entropy
- Detecting file signatures using magic bytes
- Providing a web-based security dashboard

---

## Features

### Real-Time Monitoring

The system uses the Watchdog library to monitor the target directory in real time.

It detects:

- `CREATED`
- `MODIFIED`
- `DELETED`

events as they occur.

---

### File Integrity Detection

Each monitored file is associated with a SHA-256 baseline.

When a file changes, its current hash is compared with the stored baseline.

```text
Current File
     |
     v
SHA-256 Hash
     |
     v
Compare with Baseline
     |
     +---- Same ------> No Integrity Change
     |
     +---- Different -> MODIFIED