# v24 Admin Console and Operator Workflows

The `admin_console` app is an API-first foundation for a future staff dashboard. It intentionally stays separate from Django's built-in `/admin/` so product operators can use safe, scoped workflows without giving everyone superuser-level model access.

## Goals

- Give support, billing, security, compliance, and ops teams one control plane.
- Keep sensitive bulk operations behind two-step approval.
- Make notes, tasks, saved views, and dashboard snapshots auditable.
- Avoid embedding business logic directly in UI code.

## New concepts

### Dashboard widgets

`DashboardWidget` stores declarative widget metadata and query/display configuration. It does not execute arbitrary SQL or Python.

Use widgets for:

- open fraud cases
- pending billing refunds
- overdue operator tasks
- active incidents
- pending compliance approvals

### Saved admin views

`SavedAdminView` stores filter/column/sort presets for repeatable operator workflows, such as:

- high-risk users
- overdue invoices
- unresolved fraud cases
- organizations with manual billing overrides

### Operator tasks

`OperatorTask` gives internal teams a simple task queue connected to platform objects through `target_type`, `target_id`, and `target_url`.

### Bulk action requests

`BulkActionRequest` is a safer pattern for dangerous operations. It supports draft, approval, rejection, running, completion, failure, and cancellation states. The model prevents self-approval for sensitive changes.

### Admin notes

`AdminNote` stores staff notes on users, organizations, invoices, incidents, fraud cases, or any other target object. Notes are visibility-scoped for staff/security/billing/compliance use.

### Dashboard snapshots

`DashboardSnapshot` stores precomputed summaries for fast dashboard loading and historical operations review.

## API endpoints

```http
GET  /api/v1/admin-console/summary/
GET  /api/v1/admin-console/snapshots/
POST /api/v1/admin-console/snapshots/create/

GET/POST   /api/v1/admin-console/widgets/
GET/PATCH  /api/v1/admin-console/widgets/{key}/

GET/POST          /api/v1/admin-console/views/
GET/PATCH/DELETE  /api/v1/admin-console/views/{id}/

GET/POST   /api/v1/admin-console/tasks/
GET/PATCH  /api/v1/admin-console/tasks/{id}/
POST       /api/v1/admin-console/tasks/{id}/action/

GET        /api/v1/admin-console/workspace/me/
GET/PATCH  /api/v1/admin-console/workspace/preferences/

GET/POST   /api/v1/admin-console/bulk-actions/
POST       /api/v1/admin-console/bulk-actions/{id}/action/

GET/POST          /api/v1/admin-console/notes/
GET/PATCH/DELETE  /api/v1/admin-console/notes/{id}/

GET /api/v1/admin-console/users/{user_id}/overview/
GET /api/v1/admin-console/orgs/{slug}/overview/
```

## Security guidance

- Expose these APIs only to authenticated staff users.
- Keep high-risk operations behind approval workflow.
- Do not store secrets inside dashboard widget configs.
- Prefer creating `AdminNote` records instead of changing customer data silently.
- For destructive bulk actions, require a matching compliance approval request before execution.

## Recommended v25 continuation

The next layer should add customer self-service UI/API workflows:

- personal profile page API
- security settings page API
- sessions/devices page API
- organization team management portal
- subscription/invoice portal facade
- privacy/export/delete request UI support
