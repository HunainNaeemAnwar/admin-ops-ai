# API Contracts: Next.js ↔ FastAPI

**Branch**: `004-nextjs-frontend-migration` | **Date**: 2026-06-23

## Overview

All API contracts between the Next.js frontend and the FastAPI backend. Existing endpoints remain unchanged. New auth endpoints are added for cookie-based session management.

## Base URL

```
http://localhost:8000
```

CORS must allow `http://localhost:3000` origin with `credentials: true`.

---

## Auth Endpoints (NEW)

### GET /api/auth/me

Validate the auth cookie and return user info.

**Request**: Cookie `auth` (httpOnly, Fernet-encrypted `{email, is_father}`)

**Response 200**:
```json
{
  "email": "father@example.com",
  "is_father": true,
  "authenticated": true
}
```

**Response 401** (no cookie or invalid):
```json
{
  "email": "",
  "is_father": false,
  "authenticated": false
}
```

### POST /api/auth/logout

Clear the auth cookie.

**Response 200**:
```json
{
  "status": "ok"
}
```

---

## Worker Endpoints (UNCHANGED)

### GET /api/workers

List all workers.

**Response**:
```json
{
  "workers": [
    { "id": 1, "name": "Naeem" },
    { "id": 2, "name": "Kaleem" }
  ]
}
```

### GET /api/products

List all products with rates.

**Response**:
```json
{
  "products": [
    { "id": 1, "code": "NUT", "rate": 0.5 }
  ]
}
```

### GET /api/worker/{worker_name}/month/{year}/{month}

Monthly breakdown for a single worker.

**Parameters**:
- `worker_name`: string (e.g., "Naeem")
- `year`: int (e.g., 2026)
- `month`: int (1-12)

**Response**:
```json
{
  "worker": "Naeem",
  "year": 2026,
  "month": 6,
  "days": [
    {
      "date": "2026-06-01",
      "day": 1,
      "status": "present",
      "products": { "NUT": 50, "10*20": 30 },
      "day_total": 80
    }
  ],
  "source": "live"
}
```

**Errors**: 404 if worker not found, 400 if invalid month.

### GET /api/worker/{worker_name}/excel/{year}/{month}

Download Excel file for a worker's month.

**Response**: File download (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)

**Errors**: 404 if worker not found or no data.

---

## Report Endpoints (UNCHANGED)

### GET /api/archive/check

Check if auto-archiving should run (first day of month).

**Response**:
```json
{
  "is_first_day": true,
  "prev_month_archived": false,
  "prev_month": { "year": 2026, "month": 5 }
}
```

### GET /api/history/months

List all archived months.

**Response**:
```json
{
  "months": [
    { "year": 2026, "month": 5 },
    { "year": 2026, "month": 4 }
  ]
}
```

---

## Admin Endpoints (AUTH-REQUIRED, UNCHANGED)

All admin endpoints require the auth cookie. FastAPI's `require_father()` on POST endpoints provides backend enforcement.

### GET /admin/daily

Daily report.

**Parameters**: `year`, `month`, `day` (optional, defaults to today)

**Response**:
```json
{
  "date": "2026-06-23",
  "entries": [
    { "worker_name": "Naeem", "product_code": "NUT", "quantity": 50, "status": "present" }
  ],
  "totals": { "NUT": 200, "10*20": 150 },
  "total_pieces": 350
}
```

### GET /admin/monthly

Monthly summary.

**Parameters**: `year`, `month` (optional, defaults to current)

**Response**:
```json
{
  "year": 2026,
  "month": 6,
  "workers": [
    { "worker": "Naeem", "totals": { "NUT": 1200, "10*20": 900 } }
  ]
}
```

### GET /admin/workers

List all workers (admin format).

**Response**:
```json
{
  "workers": ["Naeem", "Kaleem", "Akbar", "Suny", "Sajjad", "Irfan", "Kashif", "Gulmast"]
}
```

### GET /admin/worker/{worker}

Worker detail.

**Parameters**: `year`, `month` (optional, defaults to current)

**Response**:
```json
{
  "worker": "Naeem",
  "year": 2026,
  "month": 6,
  "entries": [
    { "product_code": "NUT", "quantity": 1200, "product_id": 1, "worker_id": 1 }
  ]
}
```

### GET /admin/products

List all products (admin format).

**Response**:
```json
{
  "products": [
    { "id": 1, "code": "NUT", "rate": 0.5 },
    { "id": 2, "code": "10*20", "rate": 0.75 }
  ]
}
```

### POST /admin/chat

Chat with AI agent. Only father can access.

**Request**: `application/x-www-form-urlencoded` with field `text`

**Response**:
```json
{
  "status": "ok",
  "response": "Logged 50 NUT for Naeem on 2026-06-23."
}
```

---

## Auth Flow (Cookie Protocol)

```
1. User visits /admin/*
2. Next.js middleware checks for "auth" cookie
3. If absent → redirect to /login
4. /login has link to FastAPI /admin/login → Google OAuth
5. Google consent → callback at FastAPI /oauth/callback?code=...
6. FastAPI:
   a. Exchanges code for tokens
   b. Checks email against FATHER_EMAIL
   c. Creates Fernet-encrypted cookie {email, is_father}
   d. Sets cookie "auth" with httpOnly, secure, SameSite=Lax
   e. Redirects to FRONTEND_URL + /admin (if father) or / (if not)
7. Next.js middleware sees cookie → allows /admin/*
8. Admin layout calls /api/auth/me → confirms is_father=true
9. If cookie expired/invalid → /api/auth/me returns 401 → redirect to /login
```
