# Quickstart: Worker Dashboard + History Auto-Archive

**Branch**: `003-worker-dashboard-history` | **Date**: 2026-06-23

## What Changed

1. **Worker Dashboard** at `/` — public monthly calendar table with worker/month dropdowns
2. **Father Admin Panel** at `/admin` — existing management features moved here (OAuth-protected)
3. **Auto-Archive** — month rollover automatically archives previous month's data to history table + Excel files
4. **Worker Excel Download** — one-click per-worker monthly Excel report

## For Users

- **Workers**: Open the website → see your monthly production table. Use dropdowns to change worker/month. Click "Download Excel" for a spreadsheet copy.
- **Father**: Go to `/admin` and login with Google → same management dashboard as before.
- **Everyone**: Previous months are available via the month dropdown — archived automatically.

## For Developers

### Key Files Modified/Created

| File | Change |
|------|--------|
| `web_ui/routes.py` | `/` → worker dashboard, `/admin` → father panel, new API routes |
| `web_ui/templates/worker_dashboard.html` | **New** — monthly calendar table UI |
| `web_ui/templates/index.html` | Updated for `/admin` path |
| `tools/database.py` | New `worker_monthly_history` table + `get_worker_daily_breakdown()` |
| `tools/export_tools.py` | New `generate_worker_excel()` |
| `config.py` | Added `HISTORY_DIR` path |

### Directory Changes

| Directory | Purpose |
|-----------|---------|
| `data/history/` | Archived monthly Excel files |

### Testing

```bash
# Worker dashboard
open http://localhost:8000
# → Should show monthly table for current month, first worker selected

# Father admin panel
open http://localhost:8000/admin
# → Should show Google OAuth login

# Excel download
# Select worker + month, click "Download Excel"
# → Should download .xlsx file

# Auto-archive
# Set server date to 1st of next month, visit dashboard
# → Previous month should be archived

# Regression: father features
open http://localhost:8000/admin
# Login → all management features accessible
```
