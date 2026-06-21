import os
import tempfile

os.environ["DATABASE_URL"] = tempfile.mktemp(suffix=".db")
os.environ["FIXED_WORKERS"] = "Naeem,Kaleem,Akbar,Suny,Sajjad,Irfan,Kashif,Gulmast"
os.environ["RATE_NUT"] = "0.5"
os.environ["RATE_10X20"] = "0.75"
os.environ["RATE_6X25"] = "0.60"
os.environ["RATE_6X30"] = "0.65"
os.environ["RATE_10X25"] = "0.80"
os.environ["TAX_PERCENTAGE"] = "3.0"
os.environ["MANAGER_EMAIL"] = "manager@test.com"
os.environ["FATHER_EMAIL"] = "father@test.com"

import config
from config import FIXED_WORKERS
from tools.database import get_db, init_db


def seed_test_db():
    init_db()
    conn = get_db()
    for name in FIXED_WORKERS:
        conn.execute("INSERT OR IGNORE INTO workers (name) VALUES (?)", (name,))
    products_data = [
        ("NUT", "Nut", 0.5),
        ("10*20", "10x20", 0.75),
        ("6*25", "6x25", 0.60),
        ("6*30", "6x30", 0.65),
        ("10*25", "10x25", 0.80),
    ]
    for code, desc, rate in products_data:
        conn.execute(
            "INSERT OR IGNORE INTO products (code, description, rate) VALUES (?, ?, ?)",
            (code, desc, rate),
        )
    conn.commit()
    conn.close()


seed_test_db()


def clear_tables():
    conn = get_db()
    for table in ["daily_log", "rejections", "advances", "payslips"]:
        conn.execute(f"DELETE FROM {table}")
    conn.execute("DELETE FROM workers")
    for name in FIXED_WORKERS:
        conn.execute("INSERT OR IGNORE INTO workers (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()


import pytest


@pytest.fixture(autouse=True)
def clean_db():
    clear_tables()
    yield
    clear_tables()


@pytest.fixture
def worker_ids():
    conn = get_db()
    rows = conn.execute("SELECT id, name FROM workers ORDER BY name").fetchall()
    conn.close()
    return {r["name"]: r["id"] for r in rows}


@pytest.fixture
def product_ids():
    conn = get_db()
    rows = conn.execute("SELECT id, code FROM products ORDER BY code").fetchall()
    conn.close()
    return {r["code"]: r["id"] for r in rows}
