# Quickstart: Next.js Frontend

**Branch**: `004-nextjs-frontend-migration` | **Date**: 2026-06-23

## Prerequisites

- Node.js 20+ installed
- FastAPI backend running on port 8000 (see main project README)
- `.env` configured with `FRONTEND_URL=http://localhost:3000`

## Setup

```bash
cd frontend
npm install
```

## Environment

No separate `.env` needed for the frontend. Configure in `next.config.ts`:

```typescript
// frontend/next.config.ts
const nextConfig = {
  // API calls go to FastAPI on port 8000
  // No proxy needed — frontend calls FastAPI directly
}

module.exports = nextConfig
```

The FastAPI base URL is configured in `frontend/lib/api.ts`.

## Development

```bash
# Start FastAPI backend (in repo root)
uv run python main.py web

# Start Next.js dev server (in frontend/)
cd frontend && npm run dev
```

- FastAPI: `http://localhost:8000`
- Next.js: `http://localhost:3000`

## Required FastAPI Changes

These are documented in `contracts/README.md`. Before running the frontend, ensure:

1. FastAPI has `GET /api/auth/me` endpoint
2. FastAPI has `POST /api/auth/logout` endpoint
3. FastAPI `/oauth/callback` sets `auth` cookie and redirects to `FRONTEND_URL`
4. CORS middleware allows `http://localhost:3000`

## Project Structure

```
frontend/
├── app/          — Next.js App Router pages
├── components/   — Reusable React components
│   └── ui/       — Base UI primitives
├── lib/          — Utilities (api, auth, types)
└── public/       — Static assets
```

## Architecture Notes

- Public user dashboard (`/`) is a Client Component with 15-second auto-refresh
- Admin pages (`/admin/*`) are Client Components, protected by middleware
- Chat widget is dynamically imported (`next/dynamic`) with `ssr: false`
- Auth state managed via React Context (`AuthProvider`)
- All API calls through `lib/api.ts` wrapper (handles cookie forwarding, errors)
