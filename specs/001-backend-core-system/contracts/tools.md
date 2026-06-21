# Tools Contract: Backend Core System

**Branch**: `001-backend-core-system` | **Date**: 2026-06-22

## 10 Function Tools

### 1. log_production

**Input**: JSON array OR natural language text
**Output**: Confirmation string with per-worker breakdown
**Side effects**: INSERT/UPDATE on `daily_log`, `daily_log.is_absent`
**Auth required**: FATHER_EMAIL

### 2. log_rejection

**Input**: year, month, product_code, total_qty, excluded_workers (optional)
**Output**: Confirmation with distribution breakdown
**Side effects**: INSERT on `rejections`
**Auth required**: FATHER_EMAIL

### 3. record_advance

**Input**: worker, amount, month, year, description (optional)
**Output**: Confirmation
**Side effects**: INSERT on `advances`
**Auth required**: FATHER_EMAIL

### 4. mark_absent

**Input**: date, workers (array of names or "all")
**Output**: Confirmation
**Side effects**: INSERT or UPDATE on `daily_log` with `is_absent=TRUE`
**Auth required**: FATHER_EMAIL

### 5. get_daily_status

**Input**: date (optional, default today)
**Output**: Status message (DATA_FOUND or NO_DATA) with breakdown
**Side effects**: None (read-only)
**Auth required**: None (available to all)

### 6. get_summary

**Input**: period (daily|weekly|monthly), year, month, day (optional)
**Output**: Formatted summary string
**Side effects**: None (read-only)
**Auth required**: None (available to all)

### 7. generate_payslip

**Input**: year, month, worker (optional, null = all)
**Output**: File paths for generated PDF + Excel
**Side effects**: INSERT on `payslips`, writes files to `data/pay_slips/`
**Auth required**: FATHER_EMAIL

### 8. send_report

**Input**: period (daily|weekly|monthly), year, month, day (optional)
**Output**: Delivery status
**Side effects**: Sends email via Gmail API
**Auth required**: FATHER_EMAIL

### 9. update_entry

**Input**: entry_id, new_quantity, reason (optional)
**Output**: Old vs new values
**Side effects**: UPDATE on `daily_log`
**Auth required**: FATHER_EMAIL

### 10. list_catalog

**Input**: None
**Output**: Workers list + products list + today's date
**Side effects**: None (read-only)
**Auth required**: None (available to all)
