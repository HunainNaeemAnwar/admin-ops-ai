# Feature Specification: Backend Core System — Phase 1

**Feature Branch**: `001-backend-core-system`
**Created**: 2026-06-22
**Status**: Draft
**Input**: User description: Complete backend system based on architecture plan in README.md

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Record Daily Production (Priority: P1 — MVP)

Father starts his day by telling the agent in Roman Urdu what each worker produced.
The agent understands natural language, fills in gaps intelligently, confirms before
saving, and shows a clear summary. Every worker must have a status for the day —
either production quantities or "absent".

**Why this priority**: Without recording production, none of the downstream
features (payslips, reports, tracking) have any data to work with. This is the
foundation of the entire system.

**Independent Test**: Father can say "Aj Kaleem ne 300 nut aur 150 10\*20 kiye",
receive a confirmation summary, and see the data reflected in a daily total query.

**Acceptance Scenarios**:

1. **Given** no data exists for today, **When** father says "Aj Kaleem ne 300 nut
   kiye", **Then** the agent confirms "Kaleem: NUT=300" and shows today's summary.
2. **Given** father says "Aj sab k 300 nut, 200 6\*25 thay aur kashif ki chutti thi",
   **When** the agent processes the statement, **Then** all 8 workers get NUT=300
   and 6\*25=200, except Kashif who is marked absent.
3. **Given** father says "Kaleem ne 500 nut kiye, Sajjad ne 300 6\*30", **When** the
   agent records, **Then** other workers are recorded with 0 quantities (not absent).
4. **Given** father mentions a non-existent product like "M10 bolt", **When** the
   agent responds, **Then** it says "ye item exist nhi krta" and lists available
   products.
5. **Given** father enters data for a past date, **When** the agent processes,
   **Then** the entry is saved with the correct date.

---

### User Story 2 — Track Monthly Finishes (Priority: P2)

Father manages month-end adjustments: rejection recording, advance payments,
and absent marking. Rejections are recorded at department level (e.g., "June main
1000 nut reject"), distributed equally among workers, with ability to exclude
specific workers. Advances are tracked per worker and auto-deducted from payslips.

**Why this priority**: Rejection and advance tracking directly affect paycheck
accuracy. Father needs these before generating payslips.

**Independent Test**: Father says "June k mahinay main 1000 nut reject hwa",
then says "Kaleem k rejection mat kato", and sees Kaleem excluded from
distribution.

**Acceptance Scenarios**:

1. **Given** father says "June main 1000 nut reject hwa", **When** agent records
   it, **Then** system stores 1000 NUT rejection for June, equally divided among
   8 workers (125 each).
2. **Given** a rejection exists for June, **When** father says "Kaleem k rejection
   mat kato", **Then** Kaleem is excluded and remaining 7 workers' shares
   recalculate (1000/7 ≈ 143 each).
3. **Given** father says "Kaleem ko 2000 advance diye", **When** agent records,
   **Then** the advance is stored and will be deducted from Kaleem's next payslip.
4. **Given** father says "Kashif ki 15 June ko chutti thi", **When** agent marks,
   **Then** that day is recorded as absent for Kashif.
5. **Given** a worker was absent for a month, **When** rejection is distributed,
   **Then** the absent worker can be excluded from distribution.

---

### User Story 3 — Generate Monthly Payslips (Priority: P3)

Father triggers payslip generation for one worker or all workers. Each payslip
shows product-by-product breakdown (good quantity, reject share, net quantity),
plus gross earnings, rejection deduction, advance deduction, tax deduction, and
net payable. Both PDF (printable) and Excel formats are generated.

**Why this priority**: Payslips are the final output workers need to get paid.
Father needs to print and distribute them.

**Independent Test**: Father says "Sab ki payslip banao June 2026 ki", and
receives PDF + Excel files for all 8 workers in the output directory.

**Acceptance Scenarios**:

1. **Given** a month has production data, rejections, and advances, **When**
   father says "Sab ki payslip banao", **Then** PDF and Excel files are generated
   for every worker with correct calculations.
2. **Given** father says "Kaleem ka payslip banao", **When** agent processes,
   **Then** only Kaleem's payslip is generated.
3. **Given** a payslip is generated, **When** inspected, **Then** it shows:
   product breakdown, gross total, rejection deduction, advance deduction, tax
   deduction, and net payable.
4. **Given** no data exists for a month, **When** father asks for payslips,
   **Then** agent responds with "No data found for this month."
5. **Given** a payslip was generated earlier, **When** father edits an entry and
   regenerates, **Then** the old payslip is replaced with updated values.

---

### User Story 4 — Send Reports to Manager (Priority: P4)

Father triggers production reports to be sent to the manager's email. Reports
contain department-level quantities only — no individual worker data, no financial
information. Daily reports are plain text email. Weekly and monthly reports
include Excel attachments with day-wise or month-wise totals per product.

**Why this priority**: Manager needs visibility into department production.
Father controls exactly when and what gets shared.

**Independent Test**: Father says "Manager ko daily email bhejo", and manager
receives email with only department totals per product (nothing else).

**Acceptance Scenarios**:

1. **Given** production data exists for today, **When** father says "Manager ko
   daily email bhejo", **Then** manager receives email with per-product totals
   across all workers (e.g., NUT: 2400 pcs, 10\*20: 1600 pcs).
2. **Given** father says "Manager ko weekly email bhejo", **When** processed,
   **Then** manager receives Excel attachment with day-wise breakdown.
3. **Given** father says "Manager ko monthly report bhejo", **When** processed,
   **Then** manager receives Excel attachment with monthly totals.
4. **Given** no production data exists for the requested period, **When** agent
   tries to send, **Then** it says "No production recorded for this period."
5. **Given** manager email fails to deliver, **When** agent reports, **Then**
   father sees error message with reason.

---

### User Story 5 — Access System Securely (Priority: P5)

Anyone can log in with their Google account to view the dashboard. Only father
(his email configured in the system) can chat with the agent, edit records, send
emails, and generate payslips. Other users see read-only views.

**Why this priority**: Security prevents unauthorized changes while allowing
transparency. Family members or the manager can view reports without risk of
accidental edits.

**Independent Test**: Father logs in with his Google account and sees the chat
interface. Another person logs in with a different account and sees only the
dashboard without chat or edit options.

**Acceptance Scenarios**:

1. **Given** a user is not logged in, **When** they visit the system, **Then**
   they see a "Sign in with Google" button on the dashboard.
2. **Given** a user logs in with an email matching the configured father email,
   **When** they access the system, **Then** they have full access to chat, edit,
   email, and payslip features.
3. **Given** a user logs in with a non-father email, **When** they access the
   system, **Then** they see read-only dashboard and reports.
4. **Given** father's session expires or token is revoked, **When** he tries to
   use the system, **Then** he is prompted to re-authenticate.

---

### Edge Cases

- **Empty day row prevented**: System must never allow a day without either
  production data or "absent" status for any worker. Agent enforces completeness.
- **Sunday working day**: Sunday is not a fixed holiday. Father can record
  production or mark absent on any day of the week.
- **Worker mid-month join/leave**: Rejection distribution automatically adjusts
  for workers who only worked part of the month. Father can manually override.
- **Multiple rejections same month**: Multiple rejection entries for different
  products in the same month are tracked independently and summed per product.
- **Rejection after payslip generated**: Father can record rejection after
  payslips are made and regenerate them with updated values.
- **Edit historical entry**: Father can correct any past entry. System shows
  old vs new values for audit trail.
- **Future date entry**: System rejects attempts to record production for future
  dates.
- **All workers absent**: If all workers are absent on a day, the system records
  it and reports "No production" when asked.
- **Product not yet in production**: 10\*25 started production in 2026. Months
  before 2026 have zero data for this product. System handles this gracefully.
- **Concurrent rejection and production**: Father can record multiple statements
  (production + rejection + advance) in the same conversation session.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept Roman Urdu natural language input for recording
  daily production (e.g., "Aj Kaleem ne 300 nut kiye").
- **FR-002**: System MUST support shorthand patterns: "sab k X product" applies
  quantity to all workers; "X ne Y nhi bnaya" sets zero for that product only.
- **FR-003**: System MUST support marking workers as absent via phrases like
  "X ki chutti thi".
- **FR-004**: System MUST reject non-existent product codes with a helpful error
  listing available products.
- **FR-005**: System MUST require agent to confirm with father before persisting
  any changes.
- **FR-006**: System MUST show a confirmation summary after every recording
  operation.
- **FR-007**: System MUST support recording production for past dates (not just
  today).
- **FR-008**: System MUST reject recording for future dates.
- **FR-009**: System MUST ensure every worker × day combination has either
  production data or an absent marker — no empty rows.
- **FR-010**: System MUST allow recording department-level rejections per product
  per month (quantity only, not financial).
- **FR-011**: System MUST distribute rejection quantity equally among all workers
  by default.
- **FR-012**: System MUST allow father to exclude specific workers from rejection
  distribution.
- **FR-013**: System MUST track advance payments per worker with amount, date,
  and which month to deduct from.
- **FR-014**: System MUST generate payslips in both PDF and Excel format on
  father's command.
- **FR-015**: System MUST calculate payslip as: gross earnings (rate × net
  quantity per product), minus rejection deduction (reject share × rate), minus
  advance deduction, minus tax (taxable amount × tax percentage), equals net
  payable.
- **FR-016**: System MUST support generating payslip for one specific worker or
  all workers at once.
- **FR-017**: System MUST allow father to edit any existing production entry
  with an audit trail (old vs new values).
- **FR-018**: System MUST send production reports to manager ONLY when father
  explicitly triggers via chat.
- **FR-019**: System MUST NEVER include individual worker data in manager reports
  — only department totals.
- **FR-020**: System MUST NEVER include financial information (rates, pay, tax,
  rejection, advance) in manager reports — only quantities.
- **FR-021**: System MUST send daily reports as plain text email with
  per-product total quantities.
- **FR-022**: System MUST send weekly and monthly reports as Excel attachments
  with production quantities only.
- **FR-023**: System MUST authenticate users via Google OAuth login.
- **FR-024**: System MUST restrict chat, edit, email, and payslip features to
  the configured father email address.
- **FR-025**: System MUST provide read-only dashboard access to all other
  authenticated users.
- **FR-026**: System MUST alert father when OAuth token expires and provide
  re-authentication link.
- **FR-027**: System MUST persist all data durably and recover gracefully from
  crashes without data loss.
- **FR-028**: System MUST support configuration of product rates and tax
  percentage without code changes.

### Key Entities *(include if feature involves data)*

- **Worker**: A person in the factory who polishes products. Has a name (one of
  8 fixed workers). Tracked daily for production, absence, advances, and
  rejection liability.
- **Product**: One of 5 polishable items: NUT, 10\*20, 6\*25, 6\*30, 10\*25.
  Each has a per-piece rate and tax percentage. Rates are configurable.
- **Daily Log**: A record of one worker's production for one product on one day.
  Contains quantity produced or absent status. Every worker has exactly one
  record per product per day (with quantity or zero).
- **Rejection**: A department-level record for a specific month and product.
  Contains total rejected quantity and list of workers excluded from its
  distribution. Rejection is shared equally among non-excluded workers.
- **Advance**: A payment given to a worker before month-end. Contains worker,
  amount, date, and deduction month. Deducted from that month's payslip.
- **Payslip**: Monthly earnings summary for a worker. Contains per-product
  breakdown, gross total, rejection deduction, advance deduction, tax deduction,
  and net payable. Generated as PDF and Excel.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Father can complete a full day's production recording (8 workers,
  2-3 products each) in under 2 minutes via chat.
- **SC-002**: Monthly payslips for all 8 workers are generated in under 10
  seconds total.
- **SC-003**: A daily email report is composed and sent to the manager within
  5 seconds of father's command.
- **SC-004**: Rejection distribution recalculates instantly (<1 second) when
  father adds or removes an excluded worker.
- **SC-005**: Editing a past entry reflects updated values in all downstream
  views (daily summary, payslip, report) within 2 seconds.
- **SC-006**: The system never loses data — a crash during any operation does
  not corrupt or delete previously saved records.
- **SC-007**: An unauthorized user (not father's email) cannot access chat, edit,
  or email features under any circumstances.
- **SC-008**: Father can learn the basic workflow (record → view → payslip →
  email) without external documentation within 3 attempts.
