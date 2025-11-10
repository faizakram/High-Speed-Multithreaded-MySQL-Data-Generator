# 🚀 High-Speed Multithreaded MySQL Data Generator  
### Generate and Insert Millions of Records Efficiently

This document explains how to configure, run, and optimize the **`generate_channel_txn_multithreaded_progress.py`** script to generate and insert **large-scale test data (e.g., 17 million rows)** into MySQL efficiently.

---

## 📘 Table of Contents
1. [Overview](#overview)  
2. [Prerequisites](#prerequisites)  
3. [Folder Setup](#folder-setup)  
4. [Environment Variables](#environment-variables)  
5. [Installing Dependencies](#installing-dependencies)  
6. [Database Preparation](#database-preparation)  
7. [Script Execution](#script-execution)  
8. [Example Logs](#example-logs)  
9. [Performance Tuning Tips](#performance-tuning-tips)  
10. [Optional Enhancements](#optional-enhancements)

---

## 🧠 Overview
The script creates **synthetic JSON-based records** and inserts them into MySQL using **multithreading** for speed.  
It is built for performance testing, ETL simulation, and database benchmarking.

Each thread:
- Uses its own MySQL connection.  
- Generates and inserts data in configurable batches.  
- Logs real-time progress: inserted count, remaining, % complete, rows/sec, and ETA.

---

## ⚙️ Prerequisites

| Requirement | Minimum Version | Notes |
|--------------|----------------|-------|
| **Python** | 3.9+ | Required for `concurrent.futures` and modern MySQL connector |
| **MySQL Server** | 8.0+ | Should allow local or external connections |
| **pip** | latest | For dependency management |
| **Privileges** | CREATE / INSERT / DROP | Required for table creation and inserts |

---

## 📂 Folder Setup
Recommended project layout:
```
/path/to/project/
│
├── generate_channel_txn_multithreaded_progress.py
├── .env
```

---

## 🔐 Environment Variables
You can configure these using either a `.env` file or direct `export` commands.

### `.env` example
```bash
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=rootpassword
MYSQL_DB=guardian
SOURCE_TABLE=channel_txn
TARGET_TABLE=channel_txn_temp
TOTAL_RECORDS=17000000
BATCH_SIZE=50000
THREADS=6
```

### Shell exports (alternative)
```bash
export MYSQL_HOST=127.0.0.1
export MYSQL_USER=root
export MYSQL_PASSWORD=rootpassword
export MYSQL_DB=guardian
export SOURCE_TABLE=channel_txn
export TARGET_TABLE=channel_txn_temp
export TOTAL_RECORDS=17000000
export BATCH_SIZE=50000
export THREADS=6
```

---

## 📦 Installing Dependencies

### 1️⃣ Create and activate a virtual environment
```bash
cd /path/to/project
python3 -m venv venv
source venv/bin/activate
```

### 2️⃣ Add dependencies
`requirements.txt`
```txt
mysql-connector-python
Faker
```

### 3️⃣ Install
```bash
sudo apt update
sudo apt install -y python3 python3-pip
pip3 install mysql-connector-python faker
```

---

## 🧱 Database Preparation

1. Start MySQL and ensure connection access.
2. Create a source table `channel_txn`.  
   The script will automatically **clone** it to `channel_txn_temp`.

Example schema:
```sql
CREATE DATABASE guardian;
USE guardian;

CREATE TABLE channel_txn (
    channel_id INT NOT NULL,
    unique_id VARCHAR(64) NOT NULL,
    loc_detail VARCHAR(16) NOT NULL,
    ts BIGINT NOT NULL,
    msg TEXT NOT NULL,
    action TINYINT NOT NULL DEFAULT '0',
    txn_id INT DEFAULT NULL,
    nil_action TINYINT NOT NULL DEFAULT '0',
    nil_id INT DEFAULT NULL,
    PRIMARY KEY (channel_id, unique_id),
    KEY action_nil (nil_action, channel_id, ts),
    KEY action_txn (action, channel_id, ts),
    KEY txn_id (txn_id),
    KEY nil_id (nil_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

---

## ▶️ Script Execution
Run the script after activating your virtual environment.

```bash
python3 generate_channel_txn_multithreaded_progress.py
```

---

## 🧾 Example Logs
```
🔗 Connecting to MySQL 127.0.0.1:3306 ...
⚙️  Preparing session for high-speed insert ...
🧱 Creating copy table `channel_txn_temp` (if not exists) ...
🚀 Starting multithreaded load: 17,000,000 records using 6 threads (batch=50,000)

🧵 Worker 1 | Inserted: 200,000/17,000,000 (1.18%) | Left: 16,800,000 | Speed: 95,000 rows/sec | ETA: 2.9 min
🧵 Worker 2 | Inserted: 400,000/17,000,000 (2.35%) | Left: 16,600,000 | Speed: 108,000 rows/sec | ETA: 2.4 min
...
✅ Worker 6 completed 2,833,333 rows.
🎉 All threads done: 17,000,000 rows in 4.8 min → 59,000 rows/sec
```

---

## 📊 Log Field Reference

| Field | Description |
|--------|-------------|
| **Inserted** | Total rows inserted so far (across all threads) |
| **Left** | Remaining records to reach target |
| **% Complete** | Percentage progress |
| **Speed** | Average insert rate (rows/sec) |
| **ETA** | Estimated time remaining (minutes) |

---

## ⚡ Performance Tuning Tips

### 🔹 MySQL Runtime Settings
Run inside MySQL before loading:
```sql
SET GLOBAL max_allowed_packet = 512M;
SET GLOBAL innodb_flush_log_at_trx_commit = 2;
SET GLOBAL sync_binlog = 0;
SET GLOBAL local_infile = 1;
```

### 🔹 Disable and Rebuild Indexes
For faster inserts:
```sql
ALTER TABLE channel_txn_temp
DROP INDEX action_nil, DROP INDEX action_txn, DROP INDEX txn_id, DROP INDEX nil_id;
```
After inserts:
```sql
ALTER TABLE channel_txn_temp
ADD KEY action_nil (nil_action, channel_id, ts),
ADD KEY action_txn (action, channel_id, ts),
ADD KEY txn_id (txn_id),
ADD KEY nil_id (nil_id);
```

### 🔹 Adjust Thread Count
| Threads | Recommended for |
|----------|----------------|
| 2–4 | Laptops or dual-core systems |
| 6–8 | Servers (8-core CPU) |
| 10+ | Only if MySQL I/O can handle the concurrency |

---

## 🧩 Optional Enhancements

| Feature | Description |
|----------|--------------|
| **File-based Logging** | Add Python’s `logging` module to persist progress in a log file. |
| **Multiprocessing** | Replace `ThreadPoolExecutor` with `ProcessPoolExecutor` for CPU-heavy workloads. |
| **Connection Pooling** | Use `mysql.connector.pooling.MySQLConnectionPool` for efficient reuse. |
| **Dockerized Run** | Use a container linked to your MySQL instance. |

---

## 🧠 Typical Performance Metrics

| Scale | Threads | Duration | Throughput |
|--------|----------|-----------|-------------|
| 1 M rows | 4 | ~30 s | ~33 k rows/s |
| 10 M rows | 6 | ~3–4 min | ~55–60 k rows/s |
| 17 M rows | 8 | ~4–5 min | ~60–70 k rows/s |

---

## 🏁 Summary

✅ **Key Benefits**
- Environment-driven configuration  
- Fully automated data generation  
- Real-time progress logging  
- Multithreaded inserts for speed  
- Session-level optimization  

✅ **Ideal Use Cases**
- Load testing  
- ETL and ingestion simulation  
- Data warehouse stress tests  
- Application performance benchmarking  

---

### 💬 Author’s Note
This script provides a repeatable, tunable framework for testing MySQL performance at scale.  
Easily adaptable for PostgreSQL or MongoDB pipelines.

---

**End of Document**
