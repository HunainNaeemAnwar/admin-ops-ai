# REST Endpoints Contract: Backend Core System

**Branch**: `001-backend-core-system` | **Date**: 2026-06-22

## Endpoints

### Public (No Auth Required)

| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| GET | `/` | Dashboard HTML page | HTML |
| GET | `/login` | Initiate Google OAuth | Redirect to Google |
| GET | `/oauth/callback` | OAuth callback handler | Redirect to FRONTEND_URL |
| GET | `/daily` | Daily summary JSON | `{date, workers_count, entries_count, total_pieces, total_gross, total_net}` |
| GET | `/monthly` | Monthly summary JSON | `{year, month, total_workers, total_entries, worker_breakdown[]}` |
| GET | `/workers` | Workers list JSON | `{workers: [{id, name}], year, month}` |
| GET | `/worker/{name}` | Worker detail JSON | `{worker, entries[], payslip}` |
| GET | `/products` | Product catalog JSON | `{products: [{id, name, rate, tax_pct}]}` |

### Father-Only (FATHER_EMAIL Required)

| Method | Path | Purpose | Input | Response |
|--------|------|---------|-------|----------|
| POST | `/record` | Record production | `{worker, product_code, quantity, date?}` | `{status, net, gross}` |
| POST | `/record-text` | NLP production entry | `{text}` | `{worker, entries, total_net, details}` |
| POST | `/absent` | Mark worker absent | `{date, workers[]}` | `{status}` |
| POST | `/rejection` | Record rejection | `{year, month, product_code, total_qty, excluded_workers?}` | `{status, distribution}` |
| POST | `/advance` | Record advance | `{worker, amount, month, year}` | `{status}` |
| PUT | `/products/{code}` | Update product rate | `{rate}` | `{status, old_rate, new_rate}` |
| POST | `/payslip` | Generate payslip | `{year, month, worker?}` | `{files: {pdf, excel}}` |
| POST | `/email` | Send manager report | `{period, year?, month?, day?}` | `{status, message_id?}` |
| PUT | `/entry/{id}` | Edit production entry | `{quantity, reason?}` | `{old, new}` |
| POST | `/chat` | Agent chat message | `{message, session_id?}` | `{response}` |

## Authentication

- **Method**: Google OAuth 2.0 PKCE
- **Token storage**: Encrypted (Fernet) on disk at `data/tokens/`
- **Father check**: Compare authenticated email against `FATHER_EMAIL` env var
- **Session**: Stateless (token checked on each request)
- **Expiry**: Auto-refresh via `google-auth` library
