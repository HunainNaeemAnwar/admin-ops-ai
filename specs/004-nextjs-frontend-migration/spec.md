# Feature Specification: Next.js Frontend Migration

**Feature Branch**: `004-nextjs-frontend-migration`
**Created**: 2026-06-23
**Status**: Draft
**Input**: User description: "ab is plan k specs bnao"

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Worker Dashboard: Read-Only Monthly View (Priority: P1)

Any visitor (no login required) can view a worker's monthly production table. They select a worker and month from dropdowns, and the system displays a daily breakdown: dates in rows, products in columns, quantities in cells, with daily totals.

**Why this priority**: This is the primary interface of the system. Workers and management check production data daily. It replaces the existing HTML template with zero downtime.

**Independent Test**: A user opens the website, selects "Naeem" and "June 2026", and sees a table with 30 rows showing quantities for NUT, 10\*20, 6\*25, 6\*30, 10\*25. No login prompt appears. All interactions are read-only.

**Acceptance Scenarios**:

1. **Given** the worker dashboard page is loaded, **When** the user selects "Akbar" from the worker dropdown and "May 2026" from the month selector, **Then** a table appears showing each day of May as a row with product quantity columns and daily totals.
2. **Given** a worker/month with no production data, **When** the user selects that worker and month, **Then** the table shows "No data for this period" message instead of an empty table.
3. **Given** the user changes the worker or month selection, **When** the new selection is made, **Then** the table updates within 2 seconds without a full page reload.
4. **Given** the current month is selected, **When** production data is logged via the agent, **Then** the data appears in the table within 30 seconds (auto-refresh).

---

### User Story 2 — Father Login: Google OAuth to Access Admin (Priority: P1)

The factory father signs in with Google to access admin pages. Non-father users who sign in are redirected to the worker dashboard (read-only). The login state persists across browser sessions.

**Why this priority**: Without authentication, no admin functionality is accessible. This is the gate for all father-only features.

**Independent Test**: A user clicks "Sign in with Google", completes the Google consent flow, and is redirected to the admin dashboard if their email matches FATHER_EMAIL, or to the worker dashboard if it does not.

**Acceptance Scenarios**:

1. **Given** an unauthenticated user visits `/admin`, **Then** they are redirected to `/login` showing a "Sign in with Google" button.
2. **Given** the user clicks "Sign in with Google" and completes consent with FATHER_EMAIL, **Then** they are redirected to `/admin` and see the admin dashboard.
3. **Given** the user clicks "Sign in with Google" and completes consent with a non-father email, **Then** they are redirected to `/` (worker dashboard) and do not see any admin navigation or chat widget.
4. **Given** an authenticated father closes and reopens the browser, **Then** their session persists and they remain on `/admin` without re-authenticating.

---

### User Story 3 — Admin Dashboard: Father-Only Overview (Priority: P2)

The father sees an admin overview page showing today's production statistics: number of workers present, total pieces produced, per-product totals. This is the landing page after login.

**Why this priority**: Provides the father with a quick daily snapshot. It's the first thing he sees after login and replaces the existing admin HTML template.

**Independent Test**: The father navigates to `/admin` and sees today's date, the count of workers who logged production, and total pieces per product. All data reads from the existing backend API.

**Acceptance Scenarios**:

1. **Given** the father is authenticated and visits `/admin`, **Then** they see today's date, the number of workers who worked today, and a breakdown of pieces per product code.
2. **Given** today has no production data yet, **Then** the dashboard shows zeros and a "No data yet today" indicator.
3. **Given** the father is not authenticated and navigates to `/admin`, **Then** they are redirected to `/login`.

---

### User Story 4 — Admin Reports: Daily and Monthly Views (Priority: P2)

The father can view detailed daily and monthly production reports. The daily report shows all workers and their production per product on a selected date. The monthly report shows each worker's totals per product for a selected month.

**Why this priority**: These reports are the core analytical tools for the father to monitor factory output. They replace the existing admin daily/monthly templates.

**Independent Test**: The father navigates to `/admin/daily`, selects a date, and sees a table of all workers with their product-wise quantities. Navigating to `/admin/monthly` shows a month-level summary.

**Acceptance Scenarios**:

1. **Given** the father is on the daily report page, **When** they select a date from the date picker, **Then** a table displays each worker's production per product for that date.
2. **Given** the father is on the monthly report page, **When** they select a month and year, **Then** a summary table shows each worker's total quantities per product for that month.
3. **Given** the selected date/month has no data, **Then** the page shows "No data for this period" rather than an empty table.

---

### User Story 5 — Workers List and Worker Detail Pages (Priority: P3)

The father can view a list of all fixed workers and click into any worker to see their monthly production detail with an option to download an Excel export.

**Why this priority**: Useful for per-worker performance review and payroll preparation. Lower priority because the overview reports already show aggregate data.

**Independent Test**: The father navigates to `/admin/workers`, sees all 8 worker names, clicks one, and sees their monthly breakdown with an "Download Excel" button.

**Acceptance Scenarios**:

1. **Given** the father visits `/admin/workers`, **Then** all 8 fixed workers are listed with their names.
2. **Given** the father clicks a worker name, **Then** the worker detail page shows a monthly table (same format as the public dashboard) with an "Download Excel" button.
3. **Given** the father clicks "Download Excel" on the worker detail page, **Then** a `.xlsx` file downloads with that worker's data for the selected month.

---

### User Story 6 — Products Page: View Product Codes and Rates (Priority: P3)

The father can view the 5 product codes and their current per-piece rates.

**Why this priority**: Simple informational page. Useful for verifying rates before using the chat for related actions.

**Independent Test**: The father navigates to `/admin/products` and sees a table of the 5 product codes (NUT, 10\*20, 6\*25, 6\*30, 10\*25) with their rates.

**Acceptance Scenarios**:

1. **Given** the father visits `/admin/products`, **Then** all 5 product codes and their configured per-piece rates are displayed in a table.

---

### User Story 7 — Floating Chat Widget: Father-Specific AI Assistant (Priority: P2)

A chat widget appears as a floating button at the bottom-right corner of all admin pages (only when the father is logged in). Clicking it opens a chat panel where the father can type messages to the AI agent. The agent can perform mutations: log production, record rejection, manage advances, generate payslips, and send email reports.

**Why this priority**: This replaces all mutation forms (rejection, advance, payslip, email, record production). It is the single interface through which the father performs all write operations. Without it, the father would have no way to submit data from the web UI.

**Independent Test**: The father logs in, navigates to any admin page, sees a chat button at bottom-right, clicks it, types "log 50 NUT for Naeem today", and receives a confirmation response. The data appears in the daily report.

**Acceptance Scenarios**:

1. **Given** the father is authenticated and on any admin page, **Then** a floating chat button (💬) is visible at the bottom-right corner.
2. **Given** the father clicks the chat button, **Then** a chat panel opens (approximately 380×520px) with message history and a text input at the bottom.
3. **Given** the father types "log 50 NUT for Naeem" and presses Enter, **Then** the message appears in the chat, a loading indicator shows, and the agent's response appears confirming the production was logged.
4. **Given** the father is not authenticated or is a non-father user, **Then** the chat button is not visible on any page.
5. **Given** the father closes the chat panel and navigates to a different admin page, **Then** the chat history is preserved (does not reset on page navigation).

---

### Edge Cases

- What happens when the FastAPI backend is unreachable? All pages show a "Backend unavailable" error with a retry button. The login page cannot function; the user must wait for the backend to be available.
- How does the system handle session expiry? If the father's auth cookie expires while on an admin page, the next API call returns 401, and the page redirects to `/login`.
- What happens when the father opens the chat widget but no agent response comes (timeout)? The widget shows "Request timed out. Please try again." with a retry option.
- How does the public dashboard behave with multiple simultaneous visitors? No special handling needed — all data is read-only and served from cache-less API calls.
- What happens if the chat widget is open and the father navigates to a different admin page? The widget stays open and retains its state (messages, scroll position). It only closes on explicit toggle (clicking ✕ or the chat button again).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The public worker dashboard (`/`) MUST display a worker selection dropdown, a month/year selector, and a monthly production table without requiring any authentication.
- **FR-002**: The monthly production table MUST show days as rows, products as columns, and quantities in cells. Each row MUST include a daily total. An "ABSENT" indicator MUST appear for workers marked absent on a date.
- **FR-003**: The table MUST auto-refresh every 15 seconds when the current month is selected and the browser tab is visible, so agent-logged data appears without manual refresh.
- **FR-004**: The login page (`/login`) MUST provide a "Sign in with Google" button that initiates the Google OAuth flow via the existing backend endpoint.
- **FR-005**: After Google OAuth completes, the backend MUST set a secure httpOnly cookie containing the user's email and father status, then redirect to the appropriate destination (father → `/admin`, non-father → `/`).
- **FR-006**: All `/admin/*` routes MUST be protected by middleware that checks for a valid auth cookie. Unauthenticated visitors MUST be redirected to `/login`. Authenticated non-father users MUST be redirected to `/`.
- **FR-007**: The admin overview page (`/admin`) MUST display today's date, count of present workers, total pieces produced, and per-product totals, fetched from the existing backend API.
- **FR-008**: The daily report page (`/admin/daily`) MUST allow date selection and display a table of all workers with their per-product quantities for that date.
- **FR-009**: The monthly report page (`/admin/monthly`) MUST allow month/year selection and display a summary of each worker's total quantities per product.
- **FR-010**: The workers list page (`/admin/workers`) MUST display all 8 fixed worker names. Each name MUST link to the worker's detail page.
- **FR-011**: The worker detail page (`/admin/worker/[name]`) MUST show a monthly production table (same format as the public dashboard) and provide an "Download Excel" button that downloads the worker's `.xlsx` file from the backend.
- **FR-012**: The products page (`/admin/products`) MUST display the 5 product codes and their configured per-piece rates in a table.
- **FR-013**: A floating chat widget MUST appear at the bottom-right of all admin pages when the authenticated user is the father. It MUST NOT appear on any public pages or to non-father users.
- **FR-014**: The chat widget MUST be toggleable: clicking the button opens the panel, clicking ✕ or the button again closes it. The widget MUST preserve its state (messages, scroll position) across admin page navigations.
- **FR-015**: The chat widget MUST connect to the existing `/admin/chat` backend endpoint. The father types a message, presses Enter or clicks Send, a loading indicator appears, and the agent's response is displayed as a message bubble.
- **FR-016**: The admin sidebar navigation MUST include links to all admin pages (Overview, Daily, Monthly, Workers, Products) and a logout option. The current page MUST be visually highlighted.
- **FR-017**: The application MUST handle backend unavailability gracefully: all pages display a "Backend unavailable" message with a retry option when API calls fail.
- **FR-018**: When the auth cookie expires or is invalid, the next authenticated API call MUST trigger a redirect to `/login` with a "Session expired" message.

### Key Entities *(include if feature involves data)*

- **Worker**: A factory worker entity. Identified by name. Exactly 8 fixed workers configured via environment variables. Has no authentication — workers are tracked, not users.
- **Product**: A product entity identified by a code (NUT, 10\*20, 6\*25, 6\*30, 10\*25) with a per-piece rate. Configured via environment variables. No user-facing CRUD.
- **Production Record**: A daily entry linking a worker, product, date, and quantity. The core data displayed in all tables and reports.
- **User Session**: Represented by an httpOnly auth cookie containing email and father status. Set by the backend after Google OAuth. Validated by the `/api/auth/me` endpoint.
- **Chat Message**: A transient entity. Messages are displayed in the chat widget and sent to the backend for processing. Not persisted in the frontend — history is maintained by the backend's conversation memory.

## Assumptions

- The existing FastAPI backend remains unchanged. All API endpoints, auth logic, and business rules stay as-is.
- The `auth` cookie format uses Fernet encryption (matching the existing token encryption approach), containing `{email, is_father}`.
- The FRONTEND_URL env var (`http://localhost:3000`) is used by the backend's OAuth callback to redirect after login.
- CORS is enabled on the FastAPI backend to allow requests from the Next.js frontend origin.
- The chat widget is not responsible for maintaining conversation history across server restarts — the backend's SQLiteSession memory handles that.
- The `.env` file already contains all required configuration (FATHER_EMAIL, OAUTH_REDIRECT_URI, FRONTEND_URL, etc.).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A visitor can load the worker dashboard and view production data without any login or authentication step, within 3 seconds of page load.
- **SC-002**: The father can complete the Google OAuth login flow (click sign-in, consent, land on admin dashboard) in under 30 seconds.
- **SC-003**: Unauthenticated users are blocked from all `/admin/*` pages and redirected to `/login` within 1 second.
- **SC-004**: Authenticated non-father users are blocked from all `/admin/*` pages and redirected to `/` within 1 second.
- **SC-005**: The father can open the chat widget, type a message, and receive an agent response within 10 seconds (including backend processing time).
- **SC-006**: The floating chat widget is visible on every admin page and only on admin pages. It is never visible to non-father users or on public pages.
- **SC-007**: The worker dashboard and admin report pages load their data within 3 seconds for a standard month (30 days, 5 products, 8 workers).
- **SC-008**: All admin navigation links work correctly and highlight the current page. The sidebar is accessible and functional on screens as narrow as 375px.
- **SC-009**: Backend unavailability does not cause blank pages or browser crashes. Users see a descriptive error message with a retry button.
