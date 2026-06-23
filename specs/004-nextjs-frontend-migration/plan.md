# Implementation Plan: Next.js Frontend Migration

**Branch**: `004-nextjs-frontend-migration` | **Date**: 2026-06-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-nextjs-frontend-migration/spec.md`

## Summary

Migrate the web UI from FastAPI HTML templates to a dedicated Next.js frontend. The public worker dashboard (`/`) allows anyone to view monthly production data (read-only). Six admin pages (`/admin/*`) are protected behind Google OAuth — only FATHER_EMAIL can access them. A floating chat widget (toggleable, bottom-right) replaces all mutation forms (rejection, advance, payslip, email, record production), letting the father execute write operations by chatting with the AI agent. The FastAPI backend remains unchanged.

## Technical Context

**Language/Version**: TypeScript 5.x, Node.js 20+  
**Primary Dependencies**: Next.js 15 (App Router), Tailwind CSS 4, Lucide Icons, React 19  
**Storage**: N/A — all data served from existing FastAPI backend  
**Testing**: Playwright (optional), manual verification against acceptance scenarios  
**Target Platform**: Web browsers (modern Chromium, Firefox, Safari)  
**Project Type**: web frontend  
**Performance Goals**: Worker dashboard loads in <3s for a month of data (30 days × 5 products × 8 workers). Auth redirect completes in <1s  
**Constraints**: FastAPI backend MUST remain unchanged. Google OAuth redirect URI MUST stay `http://localhost:8000/oauth/callback`. Auth cookie must be httpOnly (set by FastAPI)  
**Scale/Scope**: 6 admin pages, 1 public page, 1 floating chat widget

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| **I. Father-Triggered Control** | ✅ PASS | Chat widget is father-only. All mutations require father to explicitly type a message. No auto-execution |
| **II. Manager Reporting** | ✅ PASS | No changes to manager report logic. Reports still triggered via agent chat |
| **III. Database-First** | ✅ PASS | No database changes. Frontend reads from FastAPI which reads from SQLite |
| **IV. Complete Daily Tracking** | ✅ PASS | No changes to tracking logic |
| **V. Simple Product Model** | ✅ PASS | No changes to product model |
| **VI. Auth & Access Control** | ✅ PASS | This feature fully implements this principle — father-only admin, read-only for others |
| **Phase 2 Frontend** | ✅ PASS | Constitution already defines Phase 2 as Next.js. Port 3000, port 8000 convention followed |

No violations. Feature aligns with all constitutional principles.

## Project Structure

### Documentation (this feature)

```
specs/004-nextjs-frontend-migration/
├── plan.md              # This file
├── research.md          # Phase 0 — technology decisions
├── data-model.md        # Phase 1 — frontend type definitions
├── quickstart.md        # Phase 1 — setup instructions
├── contracts/           # Phase 1 — API contracts with FastAPI
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 — task breakdown (/sp.tasks)
```

### Source Code (repository root)

```
frontend/
├── package.json
├── next.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
├── middleware.ts                    # Auth middleware
├── providers.tsx                    # AuthProvider wrapper
├── app/
│   ├── layout.tsx                   # Root layout (Inter font, metadata)
│   ├── page.tsx                     # Worker Dashboard (public, read-only)
│   ├── loading.tsx                  # Root loading skeleton
│   ├── globals.css                  # Tailwind base + global styles
│   ├── login/page.tsx               # Sign in with Google
│   ├── admin/
│   │   ├── layout.tsx               # Admin layout (sidebar + chat widget)
│   │   ├── page.tsx                 # Admin overview
│   │   ├── loading.tsx              # Admin loading skeleton
│   │   ├── daily/page.tsx           # Daily report
│   │   ├── monthly/page.tsx         # Monthly summary
│   │   ├── workers/page.tsx         # Workers list
│   │   ├── worker/[name]/page.tsx   # Worker detail + Excel download
│   │   └── products/page.tsx        # Products and rates
│   └── oauth/
│       └── callback/page.tsx        # OAuth callback receiver
├── components/
│   ├── chat-widget.tsx              # Floating chat widget (dynamic import)
│   ├── chat-widget-loader.tsx       # Auth-gated loader for chat widget
│   ├── admin-sidebar.tsx            # Sidebar navigation
│   ├── worker-month-table.tsx       # Monthly production table
│   └── ui/
│       ├── button.tsx
│       ├── card.tsx
│       ├── table.tsx
│       ├── select.tsx
│       ├── skeleton.tsx
│       └── error-boundary.tsx
├── lib/
│   ├── api.ts                       # FastAPI fetch wrapper
│   ├── auth.ts                      # Auth context + provider
│   └── types.ts                     # Frontend type definitions
└── public/
    └── favicon.ico
```

**Structure Decision**: Standalone Next.js frontend project in `frontend/` directory. This keeps the Python backend and JavaScript frontend fully separated, each with their own package management, build pipelines, and deployment.

## Complexity Tracking

No constitution violations. Complexity tracking not required.
