# 🛡️ File Integrity Monitor

**File Integrity Monitor (FIM)** is a web-based cybersecurity tool built with **Python and Flask** to analyze files, verify their integrity, detect changes, and maintain a record of file activity.

The project uses **cryptographic hashing, file metadata analysis, baseline comparison, change detection, SQLite event logging, and a Flask-based web interface** to provide structured file integrity analysis and security reporting.

---

## 🚀 Features

### 📁 File Upload & Analysis

File Integrity Monitor allows users to upload a file for security and integrity analysis.

The analyzer is designed to collect important file information, including:

* File name
* File extension
* File type
* File size
* Creation time
* Modification time
* Access time
* Cryptographic hashes
* File metadata
* File structure and contents where applicable

---

### 🔐 Cryptographic Hashing

The system uses cryptographic hashes to create a unique fingerprint for files.

Hash comparison can be used to determine whether a file has changed since its baseline was created.

The project uses:

* SHA-256
* MD5
* SHA-512

A change in the cryptographic fingerprint can indicate that the file content has been modified.

---

### 🧬 File Integrity Detection

File Integrity Monitor compares the current state of a file against its previously recorded baseline.

The system can identify events such as:

* 🟢 CREATED
* 🟠 MODIFIED
* 🔴 DELETED

This allows changes to monitored files to be tracked and recorded.

---

### 📊 Security Dashboard

The project includes a Flask-based dashboard designed to provide an overview of file integrity events.

The dashboard can display:

* Monitored files
* Modified files
* Created files
* Deleted files
* Recent security events
* File paths
* Event timestamps

---

### 🗄️ Event Logging

Detected file integrity events are stored in an **SQLite database**.

Each event contains information such as:

* Event ID
* Event type
* File path
* Timestamp

This allows previous integrity events to be reviewed and analyzed.

---

### 📋 Security Reports

The project is designed to generate structured file analysis reports containing information such as:

* File overview
* File metadata
* Creation and modification timestamps
* Cryptographic hashes
* Integrity status
* Detected changes
* File activity

Reports can be used to document the results of an integrity analysis.

---

## 🛠️ Technologies

* **Python**
* **Flask**
* **SQLite**
* **Watchdog**
* **Hashlib**
* **HTML5**
* **CSS3**
* **JavaScript**
* **Jinja2**

---

## 📁 Project Structure

```text
File-Integrity-Monitor/
│
├── Monitoring_Engine/
│   ├── __init__.py
│   ├── hasher.py
│   ├── file_scanner.py
│   ├── watcher.py
│   ├── baseline.py
│   └── monitor.py
│
├── Detection/
│   ├── __init__.py
│   ├── detector.py
│   └── events.py
│
├── Database/
│   ├── __init__.py
│   ├── database.py
│   └── models.py
│
├── Flask_Dashboard/
│   ├── main.py
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── upload.html
│   │   ├── loading.html
│   │   ├── report.html
│   │   └── dashboard.html
│   │
│   └── static/
│       ├── style.css
│       └── dashboard.js
│
├── monitored_files/
├── uploads/
├── Documentation/
├── fim.db
├── baseline.json
├── requirements.txt
└── README.md
