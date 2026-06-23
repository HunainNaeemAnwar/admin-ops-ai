# Feature Specification: Worker Dashboard + History Auto-Archive

**Feature Branch**: `003-worker-dashboard-history`
**Created**: 2026-06-23
**Status**: Draft
**Input**: User description: Worker web UI jahan normal workers login karein bina password ke, unko current month ka data dikhe date 1 se end tak, har worker apni Excel sheet download kar sake. Month khatam ho to next month ki 1st tarikh ko purane month ki Excel sheet bane aur data history mein chala jaye.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Worker Views Monthly Production Table (Priority: P1 — MVP)

Factory workers open the website and immediately see a monthly calendar table showing their daily production. No login required — anyone can view. The table shows each day of the month (1 to 30/31) as rows and each product (NUT, 10\*20, 6\*25, 6\*30, 10\*25) as columns. Absent days are clearly marked. A dropdown lets workers select which worker and month to view.

**Why this priority**: This is the core value — workers need to see their production data instantly. Without this, workers have no visibility into their recorded work.

**Independent Test**: Open the website, select a worker from dropdown, and verify the monthly table shows correct dates, quantities, and absent markings within 2 seconds.

**Acceptance Scenarios**:

1. **Given** no login is required, **When** a user opens the website, **Then** the worker monthly dashboard loads immediately with current month and first worker selected by default.
2. **Given** a worker has production data for the current month, **When** the dashboard loads, **Then** a table shows dates 1 to end-of-month as rows, product codes as columns, and quantities in each cell.
3. **Given** a worker was absent on certain days, **When** viewing the table, **Then** those days show "ABSENT" across all products instead of zeros.
4. **Given** a worker has no data for a specific day, **When** viewing the table, **Then** that day shows zeros for all products (not absent, just no work).
5. **Given** the user wants to view a different worker, **When** they select a name from the worker dropdown, **Then** the table updates to show that worker's data.
6. **Given** the user wants to view a different month, **When** they select a month/year from the dropdown, **Then** the table updates to show that month's data.

---

### User Story 2 — Worker Downloads Personal Excel Report (Priority: P1 — MVP)

Workers can download their own monthly production data as an Excel file with one click. The Excel shows the same daily breakdown as the web table — dates as rows, products as columns, totals at the bottom.

**Why this priority**: Workers need a portable record they can keep or share. Excel is the standard format in factory settings.

**Independent Test**: Select a worker and month, click "Download Excel", and verify the generated file contains correct daily production data with date rows and product columns.

**Acceptance Scenarios**:

1. **Given** a worker and month are selected in the dashboard, **When** the user clicks "Download Excel", **Then** an Excel file downloads with the worker's name, month, and daily production breakdown.
2. **Given** the Excel file is opened, **When** inspected, **Then** it shows dates as rows, product codes as columns, quantities in cells, and a total row per product.
3. **Given** the worker was absent on some days, **When** viewing the Excel, **Then** those days show "ABSENT" across all product columns.

---

### User Story 3 — Father Uses Admin Panel (Priority: P1 — MVP)

Father (contractor) accesses his management dashboard at a separate URL path with Google OAuth login. All existing features — chat with agent, record production, manages rejections/advances, generate payslips, send email reports — are available here.

**Why this priority**: Father must retain full control over the system. Worker dashboard must not interfere with father's management workflow.

**Independent Test**: Login with father's Google account, navigate to admin panel, and verify all existing management features (record production, payslip, email) are accessible.

**Acceptance Scenarios**:

1. **Given** father is logged in via Google OAuth, **When** he visits the admin URL, **Then** he sees the complete management dashboard with all features.
2. **Given** an unauthenticated user visits the admin URL, **When** the page loads, **Then** they see a "Sign in with Google" button and no management features.
3. **Given** a non-father Google account is logged in, **When** they visit the admin URL, **Then** they see a read-only view without edit/chat/email/payslip options.

---

### User Story 4 — Monthly Data Auto-Archives at Month End (Priority: P2)

When a new month starts (1st day), the system automatically archives the previous month's production data. Each worker's monthly data is aggregated and saved as a permanent record. Individual Excel files are generated for each worker and stored in the history archive.

**Why this priority**: Prevents data loss between months, provides permanent records, and ensures smooth transition to new month sheets.

**Independent Test**: On the 1st day of a new month, visit the dashboard and verify the previous month's data is archived and new month shows empty. Check the history archive for generated Excel files.

**Acceptance Scenarios**:

1. **Given** the previous month had production data, **When** someone visits the dashboard on the 1st day of the new month, **Then** the previous month's data is archived automatically.
2. **Given** auto-archive runs, **When** completed, **Then** each worker has an Excel file saved in the history archive with their previous month's data.
3. **Given** archive is complete, **When** the dashboard shows the new month, **Then** the new month table shows all zeros (no data yet) for all workers.
4. **Given** the previous month was already archived, **When** someone visits the dashboard on the 2nd day, **Then** no duplicate archive is created.

---

### User Story 5 — Worker Views Historical Months (Priority: P3)

Workers can select and view any previous month's data from the dropdown. Archived months load from the history storage instead of live data. The visual format is identical to current month view.

**Why this priority**: Workers need to compare performance across months and track their history. Completes the full visibility picture.

**Independent Test**: Select a previous month from the dropdown and verify the data matches the archived Excel file for that month.

**Acceptance Scenarios**:

1. **Given** a previous month's data is archived, **When** the user selects that month from the dropdown, **Then** the table shows the archived data in the same format as current month.
2. **Given** a month has no data at all (no production recorded), **When** the user selects that month, **Then** the table shows all zeros with a message "No production data for this month."
3. **Given** the current month is selected, **When** viewing, **Then** data loads from live system (not archive) to show latest entries.

---

### Edge Cases

- What happens when someone visits the dashboard mid-month for the first time? The dashboard shows current month with available data; no archive runs until next month's 1st day.
- How does the system handle a month with zero production for a specific worker? Table shows all zeros for that worker's entire month.
- What happens if the archive process is interrupted (server restart)? Archive should be idempotent — next visit detects incomplete archive and retries.
- How does the system handle months before the system existed (e.g., data not in live tables)? Archived months show "No data" with empty table.
- What about months with 28/29/30/31 days? Table auto-adjusts row count based on the selected month's actual days.
- Can multiple workers view the dashboard simultaneously? Yes — no login means no session conflicts; everyone sees data concurrently.
- What happens when father is using admin panel and workers are viewing dashboard simultaneously? Both work independently; no interference.
- How does archive handle months where some workers have data and others don't? Only workers with data get Excel files generated; others are skipped.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The main website URL MUST display a worker monthly production dashboard without requiring any login or authentication.
- **FR-002**: The dashboard MUST show a table with calendar days (1 to end of month) as rows and product codes as columns.
- **FR-003**: The dashboard MUST provide a worker selection dropdown listing all fixed workers.
- **FR-004**: The dashboard MUST provide a month/year selection dropdown for choosing which month to view.
- **FR-005**: The dashboard MUST default to the current month and the first worker when no selection is made.
- **FR-006**: Each cell in the table MUST display the quantity produced for that worker on that day for that product.
- **FR-007**: Absent days MUST display "ABSENT" across all product columns for that date row.
- **FR-008**: Days with no data MUST display zero (0) across all product columns.
- **FR-009**: The table MUST include a total row showing per-product quantities for the entire month.
- **FR-010**: The table MUST include a total column showing per-day quantities.
- **FR-011**: A "Download Excel" button MUST be available on the dashboard that generates and downloads the current worker+month's data as an Excel file.
- **FR-012**: The downloaded Excel MUST contain the same daily breakdown as the web table: dates as rows, products as columns, totals, absent markings.
- **FR-013**: The father's management dashboard MUST move to a separate URL path (e.g., `/admin`) protected by Google OAuth.
- **FR-014**: All existing management features (production recording, rejection, advance, payslip, email, chat) MUST be accessible from the father's admin path.
- **FR-015**: The main website URL MUST NOT expose any management features (no record/edit/email/payslip controls).
- **FR-016**: On the 1st day of a new month, the system MUST automatically archive the previous month's production data.
- **FR-017**: The archive process MUST aggregate each worker's daily_log into monthly totals per product.
- **FR-018**: The archive process MUST generate individual Excel files for each worker containing their archived month's data.
- **FR-019**: The archive MUST be idempotent — running it multiple times MUST NOT create duplicate records or files.
- **FR-020**: Archived monthly data MUST be viewable through the dashboard's month selector dropdown.
- **FR-021**: The dashboard MUST clearly distinguish between current month data (live) and archived month data (history) in visual presentation.
- **FR-022**: Previous months with no data MUST display an empty table with a "No production data" message.

### Key Entities *(include if feature involves data)*

- **Worker Dashboard**: A public web page showing a monthly calendar table of a worker's production. Key attributes: selected worker, selected month/year, daily quantities per product, absent markings, totals.
- **Monthly Archive**: A permanent record of a worker's production for a completed month. Contains aggregated daily data, per-product totals, and generated Excel files. Archived at month end automatically.
- **Worker Excel Report**: A downloadable spreadsheet file for a specific worker and month. Contains the same data as the web table in portable format. Generated on demand or automatically during archive.
- **Admin Panel**: The father's management interface at a separate URL. Contains all existing production, rejection, advance, payslip, email, and chat features. Protected by Google OAuth authentication.

## Assumptions

- Workers do not have individual accounts or passwords — the dashboard is fully public.
- Worker identity is determined by the dropdown selection (anyone can view any worker's data).
- The archive trigger runs when someone visits the dashboard on or after the 1st of a new month.
- Archive Excel files are stored in a dedicated history directory within the system's data folder.
- The father's admin panel URL is `/admin` and the worker dashboard is at the root `/`.
- Existing management features, OAuth flow, and database schema remain unchanged except for new history table.
- Month boundary detection uses the server's current date at the time of dashboard visit.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Workers can view their current month's production data within 2 seconds of opening the website.
- **SC-002**: Workers can download their personal monthly Excel report in under 3 seconds with one click.
- **SC-003**: Auto-archive completes for all 8 workers in under 10 seconds when triggered on month rollover.
- **SC-004**: The father's admin panel is fully functional with all existing features accessible after route change.
- **SC-005**: Workers can view any historical month's data within 3 seconds of selecting it from the dropdown.
- **SC-006**: An unauthorized user cannot access any management features (record/edit/email/payslip) from the main website.
- **SC-007**: Previous month archive runs exactly once — no duplicate archives are created on subsequent visits.
