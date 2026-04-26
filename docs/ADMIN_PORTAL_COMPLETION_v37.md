# v37 Admin and Customer Portal Completion

v37 continues completion mode. It does not add a new platform area. It finishes operational readiness around the existing admin console and customer portal modules.

## Completed areas

- Staff-only admin-console readiness report.
- Staff-only customer-portal readiness report.
- Support-request escalation from customer portal to admin-console operator tasks.
- Operational acceptance checklists for dashboard widgets, snapshots, staff operators, bulk approvals, support requests, activity logs, and billing visibility.
- Clear separation between customer-visible data and staff/operator-only data.

## New endpoints

```text
GET  /api/v1/admin-console/readiness/
GET  /api/v1/portal/readiness/
POST /api/v1/portal/support-requests/{id}/escalate/
```

## Production acceptance checklist

1. Create at least one staff operator with MFA enabled.
2. Seed admin dashboard widgets for auth, billing, support, security, fraud, and ops.
3. Create a dashboard snapshot after staging data is loaded.
4. Verify customer users can view only organizations where they are members.
5. Verify billing summaries expose subscription/invoice state but not raw payment credentials.
6. Create a support request from the portal and escalate it into an operator task.
7. Confirm customer activity logs never include secrets, tokens, raw API keys, or payment-card data.
8. Run one low-risk bulk-action approval drill with different requester and approver accounts.

## Boundary

The admin console remains API-first. A React/HTMX UI can consume these endpoints, but v37 does not add a full frontend dashboard.
