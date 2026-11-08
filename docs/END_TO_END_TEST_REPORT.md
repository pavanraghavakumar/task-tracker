# End-to-End Test Report

## Scope and environment

The integrated application was exercised locally with the Angular development server at `http://127.0.0.1:4200`, its `/api` proxy, Flask at `http://127.0.0.1:5001`, and SQLite on the same machine. No deployment, external API, or cloud hosting was used.

## Automated cases

| Area | Cases | Expected result |
| --- | --- | --- |
| Registration and login | Valid registration, duplicate/invalid registration, valid login, password storage | Account is created, duplicate and malformed data are rejected, login returns a signed token, password is hashed |
| Authorization | Missing token and cross-user task access | Protected routes reject missing authentication; users cannot read another user's tasks |
| Categories | Create, rename/color update, delete | Category changes persist; deletion leaves associated tasks uncategorized |
| Tasks | Create, retrieve, edit, delete | All CRUD operations persist through Flask to SQLite |
| Task attributes | Category, Low/Medium/High priority, due date, Pending/In Progress/Completed status | Values round-trip correctly; completion timestamps are set and cleared with status |
| Search/filter/sort | Search, status, priority, category, due-date bounds, supported sort fields and orders | API returns only matching tasks in requested order with pagination metadata |
| Progress/dashboard | Total, pending, in-progress, completed, overdue, percentage, upcoming deadlines | Counts and percentage reflect current SQLite records; completed overdue tasks are excluded from overdue |
| Activity | Creation and update history | Activity rows are recorded and returned newest first |
| Database | Migrations, constraints, CRUD, user isolation, seed idempotence, integrity check | Migrations are repeatable; foreign keys and checks hold; sample data is not duplicated |
| Cross-workstream contract | Angular proxy, PATCH methods, shared schema values | Client methods match Flask routes and both schemas agree on critical constraints |

## Resolved integration issues

1. **Task update method mismatch:** Angular used `PUT`, while Flask exposed `PATCH`. The integrated contract now uses `PATCH` for partial and complete task updates.
2. **Category update method mismatch:** Angular used `PUT`, while Flask exposed `PATCH`. The client and contract now use `PATCH`.
3. **Dashboard response mismatch:** Flask returns nested `counts` and `completion_percentage`; the Angular adapter now maps that response to the dashboard view model.
4. **Missing API routing:** Angular used relative `/api/v1` URLs without a local proxy. A checked-in development proxy now routes those calls to Flask.
5. **Schema drift:** the reusable migration differed from the runtime schema for name limits and category deletion. Limits now match backend validation and category deletion uses `ON DELETE SET NULL` so tasks survive uncategorized.
6. **Repository-wide test import:** backend tests imported `app` only when run from `backend`. The backend is now a package, allowing one root-level test command.
7. **Local port collision:** another local service occupied port 5000 and returned unrelated 404 responses. The application now supports `PORT` and the integrated setup uses 5001 consistently.

## Results

- Root Python suite: **PASS — 14 tests**.
- Angular production build: **PASS**.
- Desktop browser workflow: **PASS** for registration, login, category creation, task creation, task listing, status completion, dashboard counts, and 100% progress; page health reported no application errors on the final screens.
- Phone browser workflow: **PASS** for authenticated dashboard and completed task management; no horizontal overflow, clipping, or covered controls were visible in the final screenshots.
- Desktop WCAG 2.2 A/AA automated scans: **PASS** on dashboard, task creation, and task management.
- Browser-observed performance note: development-mode LCP was 3.8 seconds on the phone dashboard and 3.0 seconds on the phone task list; the task-creation interaction measured 232 ms INP. These do not affect functional results but are optimization opportunities.
- Dependency installation reported 21 moderate npm audit findings in the resolved Angular toolchain. No forced or breaking dependency rewrite was applied during integration.

Screenshots are intentionally retained by Nexgile outside the repository rather than committed. They cover the empty and completed dashboards, populated task creation, task management, task completion, and responsive phone workflow.
