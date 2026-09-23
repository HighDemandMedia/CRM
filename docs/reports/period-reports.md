# CRM period reports

Reports is available at `/reports` (Sell). API: `GET /api/reports/crm/`.

## Data inventory and date meanings

| Object | Available report dates | Breakdowns | Value |
| --- | --- | --- | --- |
| Contacts | Created, last property activity, latest stage change, appointment | Stage, source, language | Record count |
| Companies | Created, last property activity, latest stage change, appointment | Stage, source, industry | Record count |
| Deals | Created, last property activity, latest stage change, expected close | Stage, source, priority | Count and current amount, separately per currency; currently won amount |
| Tasks | Created, last property activity, due | Stage, priority | Record count |
| Tickets | Created, last property activity, due, first response, resolved, closed | Stage, priority, source, category | Record count |
| Calendar events | Start, scheduled/created, cancelled | Scheduled / cancelled | Event count (not attendee count) |

All objects can filter by current owner (event host), current stage/status, and inclusive custom start/end dates. Daily, Monday-based weekly and monthly series include zero buckets. Compare record count with the immediately preceding period of equal calendar-day length. Presets: last 30 days, this month, last month, this year. Filter state is in the URL. Drill-down is paginated 20 records, aggregates cover all matches. CSV exports the entire summary, breakdown and time series, not just the displayed page. Maximum window: 3,660 days. Explicit fine-grained intervals are bounded to 366 points.

Tenant and record visibility are applied before aggregation. Member and Manager permissions use the existing own/team/organization scopes; legacy users fall back to their assigned/created records. Event access follows calendar host/creator/invitee rules. CSV requires export scope covering view scope, to keep its totals identical to the displayed report. Multi-assignee/team joins use subqueries so amounts are not multiplied. Merged contacts and tickets are excluded. Deleted records are unavailable. Date-time boundaries use the organization's timezone, including DST; date-only fields stay date-only. Null selected dates are excluded. No cross-currency conversion is assumed; a blank deal currency uses the organization default.

## Honest limits and future reporting

These are current-state cohorts selected by a date property, NOT end-of-period snapshots. Owner reassignment, rescheduling, stage changes, amount edits, merges and deletion can change old reports. Last activity is the last property-change event (or creation fallback), not a count of all actions. Last stage change represents only the latest transition. A deal's `closed_on` is EXPECTED close date, not actual won date. “Currently won” must not be called collected revenue or wins during the period. Scheduled calendar events do not prove attendance.

The CRM additionally stores custom property JSON, tags, associations, notes, attachments, property-change activities, appointment change history and ticket SLA data. These are useful foundations but are not all exposed as arbitrary report dimensions in this initial module. Notes/file content is not loaded for analytics. Existing invoice financial reports and ticket specialist analytics remain separate.

Before adding historical funnels, win-rate-by-close-period, salesperson production, time-in-stage history, attendance/no-show rates or cash flow, standardize append-only outcome events with actual timestamps, actor, prior/new stage, owner/team and amount/currency at the time; define reopen/cancel semantics and backfill only from trustworthy audit data. Tasks currently have no canonical `completed_at` on the CRM Task model (the legacy BoardTask does, and must not be mixed with it). Custom property reporting should add type-aware allowlisted filters, stable keys and bounded cardinality. Revenue attribution to contacts/companies needs an explicit allocation policy to avoid counting one associated deal twice.

## References reviewed

- HubSpot, Edit report filters: https://knowledge.hubspot.com/reports/edit-report-filters
- HubSpot, Custom report builder: https://knowledge.hubspot.com/reports/create-reports-with-the-custom-report-builder
- Pipedrive, Insights report types: https://support.pipedrive.com/en/article/insights-report-types

The implementation adopts explicit date basis, date windows, grouping and underlying-record inspection; it uses this CRM's own visual design and access rules.
