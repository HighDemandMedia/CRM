# CRM users, roles and teams

Users & Teams manages invitations, active/inactive organization membership,
role assignment and team membership. Roles & Permissions defines CRM policies.
Only organization administrators can manage either section.

## Initial roles

| Role | View/edit | Create | Delete | Export | Assign owner |
| --- | --- | --- | --- | --- | --- |
| Admin | Entire organization | Yes | Entire organization | Organization | Organization |
| Manager | Team records | Yes | No | No by default | Team |
| Member | Own records | Yes | No | No | No |

Admin is protected. Manager and Member permissions can be edited; their names
remain fixed. Custom permission sets can be created from scratch or duplicated from a role, edited and assigned in Users & Teams. Each user has one effective permission set; sets are not additive. Changes apply to all
members assigned to that role on their next request.

Permissions cover Contacts, Companies, Deals, Tasks and Tickets independently.
Create is allowed/denied. View, edit, delete and export support no access,
own records, team records and entire organization. Edit/delete/export/reassignment cannot
exceed view access. Organization administration remains Admin-only.

Own means currently assigned to the organization profile. Historical creation does not grant access after reassignment. New records default to the creating member when no assignee is supplied.
Team includes own records, records explicitly assigned to their teams, and
records assigned to other members of those teams. Membership in
multiple teams combines those teams. All scopes remain within the current
organization. Deactivation removes organization access while retaining records.

Invitation acceptance applies the selected role. Teams are assigned after
acceptance. Self-role changes and removal of the last active admin are blocked.

## Implementation / validation

Policies are enforced on backend requests and scoped root-model querysets;
exports request their separate export scope. The confirmation deletion endpoint
checks all collected CRM records, including explicitly selected associations.
The PostgreSQL crm_role table uses organization row-level security.

Automated coverage: common/tests/test_crm_roles.py, test_access_onboarding.py,
and test_teams.py. Frontend CSV tests cover the export query flags. These tests
run with the repository's isolated test database, not live customer records.

The other legacy modules (including Leads, Invoices and Timesheet) retain their
existing access rules; this matrix does not define new permissions for them.

The initial recommendation migration disables delete and export on Member and
Manager without rewriting custom sets. An admin can explicitly enable export
on a custom set or Manager afterward. Owner assignment has its own per-module
scope. Existing assignments are preserved; unassigned records need assignment
by an admin (or are visible to a manager through an explicitly assigned team).

Separate permissions for imports, bulk operations, deduplication, calendar
delegation and email access are not part of this CRM object matrix.

## Single access level per set

Only Admin can create or edit permission sets. A custom set selects Personal,
Team or Organization once, then enables actions with per-module checkboxes.
All enabled scoped actions use that same level. Member is fixed to Personal;
Manager is fixed to Team. These restrictions are checked by the API as well
as the UI. Duplicating a built-in creates a custom set with an editable level.
The level is retained even when every action is disabled. Migration 0054
normalizes any previously mixed custom set to its narrowest enabled scope.

## Organization Super Admin

The organization's creator owns a protected Super Admin membership. Normal
Admin is assignable through Users & Teams and invitations. Both have full
organization administration, but an Admin cannot change or remove the creator's
account. Super Admin cannot be assigned through a role or invitation, demoted,
deactivated or removed. It is organization-specific and does not grant Django
platform superuser access or access to other organizations. Existing creators
are backfilled from recorded authorship only; missing authorship requires an
explicit owner designation. There is no ownership-transfer UI in this version.

## Removing users and administrator hierarchy

Only Super Admin can invite, promote, demote, deactivate or remove an Admin.
Admin can manage non-administrators. Neither role can remove the organization
creator or change its own access. These rules apply to legacy user endpoints,
role assignment and invitations as well as the UI.

Users & Teams > Remove opens a preview of assigned Contacts, Companies, Deals,
Tasks and Tickets. Type the exact email and optionally select a replacement.
Other assignees remain. Without a replacement, the departing user's assignment
is removed; some records may become unassigned. The server rechecks permissions,
organization, confirmation expiry and assignment counts before applying changes.

Removal marks the organization membership removed/inactive, revokes its personal
access tokens, cancels outstanding invitations and removes team/board membership.
It retains the global user, audit authorship, notes and meetings. Other
organizations are unaffected. The old direct deletion route no longer deletes
profiles. Returning requires a fresh invitation and acceptance; reactivation
alone cannot restore a removed membership. No users are removed by deployment.
