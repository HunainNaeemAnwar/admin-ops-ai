from config import FIXED_WORKERS, RATE_NUT, RATE_10X20, RATE_6X25, RATE_6X30, RATE_10X25, TAX_PERCENTAGE
from tools.database import get_db, init_db


def seed():
    init_db()
    conn = get_db()
    cursor = conn.cursor()

    for name in FIXED_WORKERS:
        cursor.execute(
            "INSERT OR IGNORE INTO workers (name) VALUES (?)",
            (name,),
        )

    products = [
        ("NUT", "Nut pieces", RATE_NUT),
        ("10*20", "10x20 bolt", RATE_10X20),
        ("6*25", "6x25 bolt", RATE_6X25),
        ("6*30", "6x30 bolt", RATE_6X30),
        ("10*25", "10x25 bolt", RATE_10X25),
    ]
    for code, desc, rate in products:
        cursor.execute(
            "UPDATE products SET rate = ?, description = ?, tax_pct = ? WHERE code = ?",
            (rate, desc, TAX_PERCENTAGE, code),
        )
        if cursor.rowcount == 0:
            cursor.execute(
                "INSERT INTO products (code, description, rate, tax_pct) VALUES (?, ?, ?, ?)",
                (code, desc, rate, TAX_PERCENTAGE),
            )

    conn.commit()
    conn.close()

    conn2 = get_db()
    worker_count = conn2.execute("SELECT COUNT(*) FROM workers").fetchone()[0]
    product_count = conn2.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    conn2.close()
    print(f"Database initialized: {worker_count} workers, {product_count} products")


if __name__ == "__main__":
    seed()
