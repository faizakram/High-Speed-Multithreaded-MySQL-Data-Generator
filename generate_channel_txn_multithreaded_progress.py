#!/usr/bin/env python3
"""
Multithreaded high-speed channel_txn data generator with live progress logging
------------------------------------------------------------------------------
Env-driven, thread-safe MySQL batch inserts with per-thread progress tracking.
"""

import os
import uuid
import json
import random
import time
import math
import threading
import mysql.connector
from faker import Faker
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------- ENV ----------
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "rootpassword")
MYSQL_DB = os.getenv("MYSQL_DB", "guardian")

SOURCE_TABLE = os.getenv("SOURCE_TABLE", "channel_txn")
TARGET_TABLE = os.getenv("TARGET_TABLE", "channel_txn_temp")

TOTAL_RECORDS = int(os.getenv("TOTAL_RECORDS", "17000000"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50000"))
THREADS = int(os.getenv("THREADS", "4"))  # number of parallel threads

# ---------- GLOBALS ----------
fake = Faker()
random.seed(time.time())
start_ts = int(time.time() * 1000)

# Thread-safe counters
progress_lock = threading.Lock()
global_inserted = 0

# ---------- INITIAL SETUP ----------
print(f"🔗 Connecting to MySQL {MYSQL_HOST}:{MYSQL_PORT} ...")
conn = mysql.connector.connect(
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    user=MYSQL_USER,
    password=MYSQL_PASSWORD,
    database=MYSQL_DB,
    autocommit=False
)
cur = conn.cursor(buffered=True)

print("⚙️  Preparing session for high-speed insert ...")
cur.execute("SET UNIQUE_CHECKS=0;")
cur.execute("SET FOREIGN_KEY_CHECKS=0;")
cur.execute("SET autocommit=0;")
conn.commit()

print(f"🧱 Creating copy table `{TARGET_TABLE}` (if not exists) ...")
cur.execute(f"DROP TABLE IF EXISTS `{TARGET_TABLE}`")
cur.execute(f"CREATE TABLE `{TARGET_TABLE}` LIKE `{SOURCE_TABLE}`")
conn.commit()
cur.close()
conn.close()

# ---------- Helper ----------
def generate_msg(uid, loc, ts):
    """Generate realistic JSON data."""
    first_name = fake.first_name()
    last_name = fake.last_name()
    phone = str(random.randint(6000000000, 9999999999))
    id_number = str(random.randint(10000000, 99999999))
    dob = random.randint(19600101, 20051231)
    amount = round(random.uniform(1000.0, 99999.99), 2)
    msg = {
        "entity": False,
        "entityIndividualLastName": last_name,
        "individualFirstName": first_name,
        "city": fake.city(),
        "countryCode": "US",
        "stateCode": fake.state_abbr(),
        "streetAddress": fake.street_address(),
        "zipCode": fake.zipcode(),
        "phoneNumber": phone,
        "tinIssuerCountry": "US",
        "idType": random.randint(1, 9),
        "idIssuerCountry": "US",
        "idIssuerState": fake.state_abbr(),
        "idNumber": id_number,
        "dob": dob,
        "uid": uid,
        "location": loc,
        "ts": ts,
        "ctrId": random.randint(10, 99),
        "amount": amount,
        "employeeId": str(random.randint(40000, 49999))
    }
    return json.dumps(msg, ensure_ascii=False)


# ---------- Worker ----------
def insert_worker(worker_id: int, start_index: int, end_index: int, total_all_threads: int, t0: float):
    """Each worker handles its own MySQL connection and record range."""
    global global_inserted

    conn = mysql.connector.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        autocommit=False
    )
    cur = conn.cursor(buffered=True)
    cur.execute("SET UNIQUE_CHECKS=0;")
    cur.execute("SET FOREIGN_KEY_CHECKS=0;")
    conn.commit()

    insert_sql = f"""
    INSERT INTO `{TARGET_TABLE}` (
        channel_id, unique_id, loc_detail, ts, msg, action,
        txn_id, nil_action, nil_id
    ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
    """

    loc_detail = f"ARCC{worker_id:04d}"
    total = end_index - start_index
    inserted = 0

    while inserted < total:
        batch = []
        for _ in range(min(BATCH_SIZE, total - inserted)):
            uid = str(uuid.uuid4())
            ts = start_ts + random.randint(0, 10_000_000)
            batch.append((
                worker_id,
                uid,
                loc_detail,
                ts,
                generate_msg(uid, loc_detail, ts),
                10,
                random.randint(7000, 999999),
                12,
                None
            ))

        cur.executemany(insert_sql, batch)
        conn.commit()
        inserted += len(batch)

        # Update shared global progress
        with progress_lock:
            global_inserted += len(batch)
            percent = (global_inserted / total_all_threads) * 100
            left = total_all_threads - global_inserted
            elapsed = time.time() - t0
            rate = global_inserted / elapsed if elapsed > 0 else 0
            eta = left / rate if rate > 0 else 0
            print(
                f"🧵 Worker {worker_id} | Inserted: {global_inserted:,}/{total_all_threads:,} "
                f"({percent:5.2f}%) | Left: {left:,} | "
                f"Speed: {rate:,.0f} rows/sec | ETA: {eta/60:,.2f} min"
            )

    cur.execute("SET UNIQUE_CHECKS=1;")
    cur.execute("SET FOREIGN_KEY_CHECKS=1;")
    conn.commit()
    cur.close()
    conn.close()
    print(f"✅ Worker {worker_id} completed {total:,} rows.")
    return worker_id, total


# ---------- Main ----------
def main():
    print(f"🚀 Starting multithreaded load: {TOTAL_RECORDS:,} records using {THREADS} threads (batch={BATCH_SIZE:,})")

    per_thread = math.ceil(TOTAL_RECORDS / THREADS)
    tasks = []
    t0 = time.time()

    with ThreadPoolExecutor(max_workers=THREADS) as executor:
        for i in range(THREADS):
            start_index = i * per_thread
            end_index = min((i + 1) * per_thread, TOTAL_RECORDS)
            tasks.append(executor.submit(insert_worker, i + 1, start_index, end_index, TOTAL_RECORDS, t0))

        for future in as_completed(tasks):
            wid, count = future.result()
            print(f"✅ Worker {wid} finished inserting {count:,} rows")

    elapsed = time.time() - t0
    rate = TOTAL_RECORDS / elapsed if elapsed > 0 else 0
    print(f"\n🎉 All threads done: {TOTAL_RECORDS:,} rows in {elapsed/60:.2f} min "
          f"→ {rate:,.0f} rows/sec\n")


if __name__ == "__main__":
    main()