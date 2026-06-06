import sqlite3
import os
import pandas as pd

DB_PATH = "health_insight.db"
CSV_PATH = "patients.csv"

USERS = [
    ("Raj_analyst", "healthinR12"),
    ("pharmacist",   "pharma120"),
    ("Doctor_li",    "doc321"),
    ("manangement",  "hin234"),
]


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS patient_records (
            Patient_ID  TEXT PRIMARY KEY,
            Name        TEXT NOT NULL,
            Age         INTEGER,
            Gender      TEXT,
            Disease     TEXT,
            Medicine    TEXT,
            Dosage      TEXT,
            Reaction    TEXT,
            Recovery    TEXT,
            Visit_Date  TEXT,
            Doctor      TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)
    conn.commit()


def seed_if_empty(conn: sqlite3.Connection) -> None:
    row_count = conn.execute("SELECT COUNT(*) FROM patient_records").fetchone()[0]

    if row_count == 0:
        # patient.csv load
        if os.path.exists(CSV_PATH):
            df = pd.read_csv(CSV_PATH)

            # Patient_ID numeric Plus P add
            if df["Patient_ID"].dtype in ["int64", "float64"]:
                df["Patient_ID"] = "P" + df["Patient_ID"].astype(int).astype(str)

            df.to_sql("patient_records", conn, if_exists="append", index=False)
            print(f"[DB] patients.csv {len(df)} records load")
        else:
            print("[DB] patients.csv not found — koi data load nahi hua.")

    for username, password in USERS:
        conn.execute(
            "INSERT OR IGNORE INTO users (username, password) VALUES (?, ?)",
            (username, password)
        )
    conn.commit()
    print(f"[DB] {len(USERS)} authorized users ready.")


def verify_user(username: str, password: str) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT password FROM users WHERE username = ?", (username,)
        ).fetchone()
    if row is None:
        return False
    return row["password"] == password


def init_db() -> None:
    os.makedirs("static/charts", exist_ok=True)
    with get_connection() as conn:
        create_schema(conn)
        seed_if_empty(conn)
    print("[DB] Initialisation complete.")