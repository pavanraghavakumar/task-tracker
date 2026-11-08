# TaskFlow Angular Frontend

TaskFlow is the Angular workstream for the Personal Task Tracker. It is a standalone, responsive client designed to integrate with the local Flask API through the contract in `API_CONTRACT.md`.

## Features

- Responsive authenticated shell with desktop sidebar and mobile navigation
- Registration and login with reactive validation and Bearer-token authentication
- Dashboard metrics for total, pending, in-progress, completed, and overdue tasks
- Completion-rate progress visualization and upcoming deadlines
- Task creation, editing, deletion, and inline status changes
- Categories, Low/Medium/High priorities, due dates, and all requested statuses
- Debounced search, combined filters, server-side sorting, and pagination
- Category creation, editing, and deletion
- Reusable badges and loading state components
- Accessible labels, focus indicators, status announcements, and reduced-motion support

## Local setup

Requirements: Node.js 20.19+ and npm 10+.

```bash
cd frontend
npm install
npm start
```

The frontend runs at `http://127.0.0.1:4200`. The checked-in development proxy sends `/api/v1` to the local Flask backend at `http://127.0.0.1:5001`. The production build is created with:

```bash
npm run build
```

Authentication state is kept in browser local storage under `taskflow_access_token` and `taskflow_user`. This is a local-only application; no cloud services or deployment configuration are included.

## Structure

- `src/app/core`: typed API client, models, auth state, interceptor, and route guards
- `src/app/features`: lazy-loaded auth, dashboard, task, and category screens
- `src/app/layout`: responsive authenticated application shell
- `src/app/shared`: reusable presentational and state components

## Workstream execution summary

The frontend was developed independently from unfinished backend code against a versioned REST contract. The workstream established strict Angular configuration and typed domain models first, then added guarded routing and authentication, built reusable responsive layout primitives, implemented dashboard and complete task/category workflows, and documented every expected request and response for integration. Backend-specific assumptions are isolated in `ApiService`, primarily the `/api/v1` base path and standard response envelope, so integration changes remain localized.
