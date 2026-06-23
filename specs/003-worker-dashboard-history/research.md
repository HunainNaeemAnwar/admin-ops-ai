# Research: Worker Dashboard + History Auto-Archive

**Branch**: `003-worker-dashboard-history` | **Date**: 2026-06-23

## Unknowns Resolved

### 1. Worker Authentication

**Decision**: No authentication. Dashboard fully public.

**Rationale**: Workers don't have passwords or Google accounts. Production quantity data (without financials) is not sensitive. The spec defines worker identity via dropdown selection — anyone can view any worker's data.

### 2. Route Separation

**Decision**: `/` = worker dashboard (public), `/admin` = father dashboard (OAuth)

**Rationale**: Clean URL hierarchy. `/admin` is a standard convention for administrative interfaces. All existing routes move under `/admin/` prefix, keeping worker routes clean.

### 3. Archive Trigger Mechanism

**Decision**: Check on dashboard visit — no scheduler needed

**Rationale**: Piggybacking on natural traffic eliminates the need for cron/scheduler. The check is lightweight (single SELECT COUNT). If a month rolls over without any visit for days, archive simply runs on first visit — no data loss since daily_log remains the source of truth.

### 4. History Table vs Keeping in daily_log

**Decision**: Separate `worker_monthly_history` table

**Rationale**: Aggregated monthly data is faster to query (1200 rows/month × 8 workers = ~9600 rows/month in daily_log, vs 40 rows in history). Keeps current month queries fast. Daily_log can be purged for old months to keep DB small (or retained for audit).

### 5. Idempotency

**Decision**: Check `worker_monthly_history` for existing year/month records before archiving

**Rationale**: `UNIQUE(worker_id, year, month, product_id)` constraint prevents duplicates at DB level. Pre-check avoids wasted work.

### 6. Excel Generation on Archive vs On Demand

**Decision**: Both. Archive generates Excel files to `data/history/`. On-demand download from dashboard checks if file exists (use archived copy) or generates fresh.

**Rationale**: Archive produces permanent files. On-demand for the current month (not yet archived) generates on the fly.

## Dependencies

- `openpyxl` — already in project for Excel generation
- `calendar` (stdlib) — monthrange() for determining days in month
- No new external dependencies
