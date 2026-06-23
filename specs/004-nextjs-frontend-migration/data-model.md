# Data Model: Frontend Types

**Branch**: `004-nextjs-frontend-migration` | **Date**: 2026-06-23

## Overview

This document defines the frontend TypeScript types. No database changes. These types mirror the FastAPI JSON responses and are used for type safety in the Next.js app.

---

## Entities

### Worker

Represents a factory worker. Read from FastAPI.

```typescript
interface Worker {
  id: number
  name: string   // e.g., "Naeem", "Kaleem", etc.
}
```

### Product

Represents a product with piece rate.

```typescript
interface Product {
  id: number
  code: string   // One of: "NUT", "10*20", "6*25", "6*30", "10*25"
  rate: number   // Per-piece rate in rupees
}
```

### DailyEntry

A single day's production data for one worker.

```typescript
interface DailyEntry {
  date: string          // ISO date "2026-06-01"
  day: number           // Day of month (1-31)
  status: "present" | "absent"
  products: Record<string, number>  // { "NUT": 50, "10*20": 30 }
  day_total: number     // Sum of all products for this day
}
```

### WorkerMonthData

The full month breakdown for one worker, returned by the API.

```typescript
interface WorkerMonthData {
  worker: string
  year: number
  month: number
  days: DailyEntry[]
  source: "live" | "archived" | "none"
}
```

### DailyTotals

Per-product totals for a specific date, across all workers.

```typescript
interface DailyTotals {
  [productCode: string]: number   // { "NUT": 200, "10*20": 150 }
}
```

### DailyReport

Full daily report for a specific date.

```typescript
interface DailyReport {
  date: string
  entries: Array<{
    worker_name: string
    product_code: string
    quantity: number
    status: string
  }>
  totals: DailyTotals
  total_pieces: number
}
```

### MonthlyWorkerSummary

One worker's totals for a month.

```typescript
interface MonthlyWorkerSummary {
  worker: string
  totals: Record<string, number>  // { "NUT": 1200, "10*20": 900 }
}
```

### MonthlyReport

Full monthly report.

```typescript
interface MonthlyReport {
  year: number
  month: number
  workers: MonthlyWorkerSummary[]
}
```

### AuthUser

User session info returned by `/api/auth/me`.

```typescript
interface AuthUser {
  email: string
  is_father: boolean
  authenticated: boolean
}
```

### ArchiveCheck

Archive status for the current month transition.

```typescript
interface ArchiveCheck {
  is_first_day: boolean
  prev_month_archived: boolean
  prev_month: { year: number; month: number }
}
```

### ChatMessage

A single message in the chat widget.

```typescript
interface ChatMessage {
  id: string
  role: "user" | "assistant"
  text: string
  timestamp: Date
}
```
