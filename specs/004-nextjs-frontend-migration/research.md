# Research: Next.js Frontend Migration

**Branch**: `004-nextjs-frontend-migration` | **Date**: 2026-06-23

## Decisions

### 1. Frontend Framework: Next.js 15 App Router

| Aspect | Decision |
|--------|----------|
| **Decision** | Use Next.js 15 App Router with Tailwind CSS |
| **Rationale** | App Router is the current standard for Next.js. Provides layout system, middleware for auth, server/client component model, and strong TypeScript support. Tailwind CSS is the most popular utility-first CSS framework with excellent Next.js integration |
| **Alternatives** | Vite + React (no SSR/SSG), Remix (similar but smaller ecosystem) |

### 2. Auth Model: Backend-Issued httpOnly Cookie

| Aspect | Decision |
|--------|----------|
| **Decision** | FastAPI backend sets a Fernet-encrypted httpOnly cookie after Google OAuth. Next.js middleware checks for this cookie. A `/api/auth/me` endpoint validates the cookie and returns `{email, is_father}` |
| **Rationale** | httpOnly cookies cannot be read by JavaScript (XSS protection). The existing token infrastructure already uses Fernet encryption. No additional JWT library needed. The OAuth flow remains at FastAPI where the Google client ID/secret already live |
| **Alternatives** | JWT in localStorage (XSS-vulnerable), NextAuth.js (requires rewriting OAuth flow), session tokens in FastAPI (more complex) |

### 3. Chat Widget: Custom React Component

| Aspect | Decision |
|--------|----------|
| **Decision** | Build a custom floating chat widget using React + Tailwind CSS, inspired by ChatKit's UI patterns |
| **Rationale** | ChatKit requires either OpenAI's hosted API (client_secret pattern) or a custom ChatKit-compatible server. Our existing `/admin/chat` endpoint is a simple POST/response. A custom component is simpler, lighter (no extra dependency), and directly connects to our backend |
| **Alternatives** | ChatKit (requires protocol-level backend changes), raw WebSocket (overkill) |

### 4. State Management: React Context + useState

| Aspect | Decision |
|--------|----------|
| **Decision** | React Context for auth state. Component-local `useState` for page-level data |
| **Rationale** | The app is small (7 pages). No complex state sharing beyond auth. Context for auth is the standard pattern. Page data is fetched per-page and doesn't need to be shared |
| **Alternatives** | Zustand (good but unnecessary overhead for this scale), Redux (way too heavy) |

### 5. Data Fetching: Client-Side fetch with custom wrapper

| Aspect | Decision |
|--------|----------|
| **Decision** | Most pages are Client Components that call FastAPI with a custom `api.ts` wrapper (includes credentials, error handling, base URL) |
| **Rationale** | All data comes from an external API (FastAPI). Server Components don't add caching benefit here since data is real-time production data. Client-side fetch with `credentials: 'include'` passes the auth cookie automatically |
| **Alternatives** | SWR/React Query (good but adds deps), Server Components with fetch to FastAPI (possible but no real benefit) |

### 6. Auto-Refresh: setInterval with Page Visibility API

| Aspect | Decision |
|--------|----------|
| **Decision** | 15-second polling via `setInterval` in the worker dashboard, gated by `document.hidden` so it only polls when the tab is visible |
| **Rationale** | Agent logs data via CLI — the dashboard needs to pick it up. 15 seconds balances freshness against unnecessary network calls. Page Visibility API avoids polling when user isn't looking |
| **Alternatives** | WebSocket push (backend doesn't support it), Server-Sent Events (requires backend changes) |

### 7. Error Handling: Unified Error Boundary

| Aspect | Decision |
|--------|----------|
| **Decision** | Each page wraps data fetching in try/catch. On failure, show a "Backend unavailable" card with a retry button. A global error boundary catches rendering errors |
| **Rationale** | FastAPI runs separately — it can be down while Next.js is up. Graceful degradation is essential. The retry pattern is simple and effective |
| **Alternatives** | React Error Boundary (for render errors), error.tsx (route-level) |

### 8. Backend Changes Required

| Aspect | Decision |
|--------|----------|
| **Decision** | Three small additions to FastAPI: (1) `GET /api/auth/me` endpoint, (2) `POST /api/auth/logout` endpoint, (3) CORS middleware for `http://localhost:3000`, (4) OAuth callback sets auth cookie + redirects to FRONTEND_URL |
| **Rationale** | These are minimal, non-breaking additions. All existing API endpoints stay unchanged |
| **Alternatives** | Proxy auth through Next.js API routes (adds unnecessary hop) |
