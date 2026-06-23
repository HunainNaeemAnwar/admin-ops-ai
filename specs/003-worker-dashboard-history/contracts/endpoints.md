# Contract: Worker Dashboard + History Auto-Archive

## New/Modified Routes

### Public (No Auth Required)

| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| GET | `/` | Worker dashboard HTML | HTML page with calendar table |
| GET | `/api/workers` | Workers list JSON | `{workers: [{id, name}]}` |
| GET | `/api/products` | Products list JSON | `{products: [{id, code}]}` |
| GET | `/api/worker/{name}/month/{year}/{month}` | Worker month daily breakdown JSON | `{worker, year, month, days: [{date, status, products: {code: qty}}]}` |
| GET | `/api/worker/{name}/excel/{year}/{month}` | Download worker Excel file | Binary `.xlsx` download |

### Father-Only (OAuth Required — /admin prefix)

All existing routes from contract move under `/admin/` prefix:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/admin` | Father dashboard HTML |
| POST | `/admin/record` | Record production |
| POST | `/admin/rejection` | Record rejection |
| POST | `/admin/advance` | Record advance |
| POST | `/admin/payslip` | Generate payslip |
| POST | `/admin/email` | Send email report |
| POST | `/admin/chat` | Agent chat |
| GET | `/admin/daily` | Daily summary JSON |
| GET | `/admin/monthly` | Monthly summary JSON |
| GET | `/admin/workers` | Workers list JSON |
| GET | `/admin/worker/{name}` | Worker detail JSON |
| GET | `/admin/products` | Product catalog JSON |
| PUT | `/admin/products/{code}` | Update product rate |

### New API Contracts

#### GET /api/worker/{name}/month/{year}/{month}

```json
{
  "worker": "Kaleem",
  "year": 2026,
  "month": 6,
  "days": [
    {
      "date": "2026-06-01",
      "status": "present",
      "products": {
        "NUT": 300,
        "10*20": 150,
        "6*25": 0,
        "6*30": 0,
        "10*25": 0
      }
    },
    {
      "date": "2026-06-03",
      "status": "absent",
      "products": {}
    }
  ]
}
```

**Status values**: `"present"` (has production data), `"absent"` (marked absent), `"no_data"` (day exists but no entries).

#### GET /api/worker/{name}/excel/{year}/{month}

- **Response**: Binary Excel file (application/vnd.openxmlformats-officedocument.spreadsheetml.sheet)
- **Content-Disposition**: `attachment; filename="{Worker}_{Year}_{Month:02d}.xlsx"`
- **Error**: 404 if no data for that worker+month

#### GET /api/workers

```json
{
  "workers": [
    {"id": 1, "name": "Naeem"},
    {"id": 2, "name": "Kaleem"}
  ]
}
```

#### GET /api/products

```json
{
  "products": [
    {"id": 1, "code": "NUT"},
    {"id": 2, "code": "10*20"}
  ]
}
```

### Data Queries

#### get_worker_daily_breakdown(worker_id, year, month)

**Input**: worker_id (int), year (int), month (int)
**Output**: List of dicts with daily breakdown per worker

```python
# Current month → from daily_log
SELECT dl.entry_date, dl.status, p.code AS product_code, dl.quantity
FROM daily_log dl
JOIN products p ON p.id = dl.product_id
WHERE dl.worker_id = ? AND dl.entry_date BETWEEN ? AND ?
ORDER BY dl.entry_date, p.code

# Archived months → from worker_monthly_history
# Returns total per product (daily granularity not stored in history)
```

#### is_month_archived(year, month)

**Input**: year (int), month (int)
**Output**: bool

```sql
SELECT COUNT(*) > 0 AS is_archived
FROM worker_monthly_history
WHERE year = ? AND month = ?
LIMIT 1
```
