import sys
import random
from calendar import monthrange, weekday
from datetime import date

from services.database import get_db, get_all_workers, get_all_products
from services.database import log_production, mark_absent, record_advance as db_record_advance


def seed_dummy(year: int, month: int):
    random.seed(year * 100 + month)
    conn = get_db()
    workers = get_all_workers()
    products = get_all_products()

    start = f"{year}-{month:02d}-01"
    days_in_month = monthrange(year, month)[1]
    end = f"{year}-{month:02d}-{days_in_month:02d}"

    conn.execute("DELETE FROM daily_log WHERE entry_date BETWEEN ? AND ?", (start, end))
    conn.execute("DELETE FROM advances WHERE year = ? AND month = ?", (year, month))
    conn.commit()

    specializations = {
        "Naeem":   {"primary": "NUT",   "secondary": "10*20"},
        "Kaleem":  {"primary": "10*20", "secondary": "6*25"},
        "Akbar":   {"primary": "6*25",  "secondary": "6*30"},
        "Suny":    {"primary": "6*30",  "secondary": "NUT"},
        "Sajjad":  {"primary": "10*25", "secondary": "10*20"},
        "Irfan":   {"primary": None,    "secondary": None},
        "Kashif":  {"primary": None,    "secondary": None},
        "Gulmast": {"primary": "NUT",   "secondary": "10*25"},
    }

    product_codes = [p["code"] for p in products]
    worker_dict = {w["name"]: w["id"] for w in workers}
    product_dict = {p["code"]: p["id"] for p in products}
    product_code_set = set(product_codes)

    total_entries = 0
    total_absences = 0
    saturdays = 0
    sundays = 0

    worker_absence_days = {w["name"]: 0 for w in workers}

    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        wd = weekday(year, month, day)

        if wd == 6:
            sundays += 1
            for w in workers:
                mark_absent(w["id"], date_str, "Sunday - factory off")
                total_absences += 1
            continue

        is_saturday = (wd == 5)
        if is_saturday:
            saturdays += 1

        present = []
        for w in workers:
            name = w["name"]
            target_absences = random.randint(2, 3)
            if worker_absence_days[name] >= target_absences:
                present.append(w)
            else:
                absent_chance = 0.4 if is_saturday else 0.18
                if random.random() < absent_chance:
                    reasons = ["Sick", "Personal work", "Family function", "Not feeling well"]
                    if is_saturday:
                        reasons.append("Half day")
                    mark_absent(w["id"], date_str, random.choice(reasons))
                    worker_absence_days[name] += 1
                    total_absences += 1
                else:
                    present.append(w)

        if not present:
            continue

        for w in present:
            name = w["name"]
            spec = specializations.get(name, {"primary": None, "secondary": None})

            if is_saturday:
                prod_code = spec["primary"] if spec["primary"] in product_code_set else random.choice(product_codes)
                qty = random.randint(50, 150)
                log_production(w["id"], product_dict[prod_code], qty, date_str)
                total_entries += 1
            else:
                chosen = set()
                if spec["primary"] and spec["primary"] in product_code_set:
                    chosen.add(spec["primary"])
                    log_production(w["id"], product_dict[spec["primary"]], random.randint(200, 500), date_str)
                    total_entries += 1

                num_additional = random.randint(1, 2)
                available = [c for c in product_codes if c not in chosen]
                random.shuffle(available)
                for i in range(min(num_additional, len(available))):
                    code = available[i]
                    if spec["secondary"] and code == spec["secondary"]:
                        qty = random.randint(150, 350)
                    else:
                        qty = random.randint(80, 250)
                    log_production(w["id"], product_dict[code], qty, date_str)
                    chosen.add(code)
                    total_entries += 1

    advance_workers = [w["name"] for w in workers if worker_absence_days[w["name"]] < 2]
    if not advance_workers:
        advance_workers = [w["name"] for w in workers]
    advance_candidates = random.sample(advance_workers, min(4, len(advance_workers)))
    advance_count = 0
    advance_total = 0
    for name in advance_candidates:
        amount = random.choice([1000, 2000, 2500, 3000, 4000, 5000])
        advance_total += amount
        db_record_advance(worker_dict[name], amount, year, month, f"Advance - {date(year, month, 1).strftime('%B')}")
        advance_count += 1

    conn.commit()

    month_name = date(year, month, 1).strftime("%B")
    print(f"Seeded {year}-{month:02d}:")
    print(f"  Month: {month_name} {year} ({days_in_month} days, {sundays} Sundays off, {saturdays} Saturdays half)")
    print(f"  Production entries: {total_entries}")
    print(f"  Absences: {total_absences}")
    print(f"  Advances: {advance_count} ({advance_total:,} total)")
    for w in workers:
        if worker_absence_days[w["name"]] > 0:
            print(f"    {w['name']}: {worker_absence_days[w['name']]} absent days")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: uv run python -m tools.seed_dummy_data <year> <month>")
        print("  Example: uv run python -m tools.seed_dummy_data 2026 5")
        sys.exit(1)

    try:
        year = int(sys.argv[1])
        month = int(sys.argv[2])
        if month < 1 or month > 12:
            raise ValueError("Month must be 1-12")
        if year < 2020 or year > 2099:
            raise ValueError("Year must be 2020-2099")
    except ValueError as e:
        print(f"Invalid arguments: {e}")
        sys.exit(1)

    seed_dummy(year, month)
