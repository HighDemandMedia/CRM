# Permissions and roles

Verified against the active CRM on 2026-10-07. Review/Preview modules remain in the
separate laboratory and are not destinations or permission grants in the main CRM.

## Identity and organization boundaries

- `User` is the sign-in identity; `Profile` is membership in one organization.
- `Profile.role` is `ADMIN` or `USER`. Use `common.permissions.is_org_admin` for
  organization administration. The legacy `is_organization_admin` field is derived
  on save and **must not be treated as an independent grant**.
- `Profile.is_super_admin` identifies the organization owner (`Org.owner_id`). This
  protected member remains active and ADMIN. An initial customer administrator
  receives ownership when accepting the CRM owner's ownership invitation.
- The **CRM owner** is an active `User.is_superuser`, explicitly granted through
  trusted administration, never inferred from an email/domain. This is distinct
  from a customer organization's Super Admin. Only the CRM owner creates customer
  organizations. Platform access still operates in an explicitly selected tenant.
- `common.member_access.assert_member_management` protects the owner, denies
  self-access changes and cross-organization targets, and prevents ordinary
  administrators from appointing/changing administrators. Super Admin and CRM owner
  can manage other administrators; customer admins cannot manage platform access.

Public registration is closed. Team invitations are issued by organization admins;
admin invitations require the protected owner's or CRM owner's authority. Invitations
expire in seven days. New memberships complete profile setup; the initial customer
administrator also completes organization setup. See
[personal preferences and setup](../settings/personal-preferences-and-uploads.md).

## Record permission sets

`CRMRole` belongs to an organization and is assigned through `Profile.access_role`.
`common/rbac.py` owns the schema, validation, defaults, scope filtering and action
checks. Member defaults to Personal (`own`); Manager defaults to Team (`team`).
Custom sets can use Personal, Team or Organization scope. Organization scope is
record visibility, **not** administrative access to Settings.

The active record modules are Contacts, Companies, Deals, Tasks and Tickets. Their
schema includes View, Create, Edit properties, Change stage, Manage notes, Upload
attachments, Delete attachments, Associations, Delete, Export and Reassign. Calendar
separately controls View, Create, Reschedule, Cancel, Reassign, Override conflicts and
Export. Reports has View and Export.

Actions cannot exceed View; stage, notes, upload, associations and reassign cannot
exceed Edit. Boolean actions still require View. Delete attachments is separate from
uploading and is denied by default in ordinary permission sets. Calendar attendance
can permit viewing without permitting edits. Report exports also require export
access to the underlying objects. Admins have full access within the selected org.
Existing legacy memberships without a permission set retain their existing access
paths; do not assume a displayed default has retroactively migrated every membership.

## Settings access

| Destination | Member / Custom | Manager | Admin / Super Admin |
| --- | --- | --- | --- |
| Profile, notifications, personal Google connections | Own only | Own only | Own only |
| Organization, Properties, Pipelines, Tags, Web forms | No access | Explicit Read only or Manage per section | Manage |
| Users & Teams, Roles & Permissions | No access | No access | Manage, subject to protected-admin rules |

`CRMRole.settings_access` defaults to an empty map. Only the built-in Manager set
can receive grants; all members assigned that set share them. Record scopes never
imply Settings access. Only organization administrators can edit permission sets.
`common/settings_access.py` validates grants and calculates effective access from
active membership, tenant and role. Missing/invalid grants fail closed. Delegated
Managers cannot grant themselves access or manage users, roles or administrators.

Settings APIs enforce read/manage separately, as do direct frontend destinations.
The navigation and editor consume fresh `/org/ui-context/` permissions. Revoking a
grant takes effect on the next request, without issuing a new login token.

Minimal runtime configuration remains available to record screens: active tags,
field definitions, property order, stage labels and the ticket cascade default.
It does not open Settings, grant mutation rights or expose tag/property aggregate
counts to ordinary members. Web forms Read only permits configuration/analytics;
submission history and publishing require Manage. Record-level permissions still
apply independently, including records moved when changing a pipeline.

## Gmail, activity and internal comments

Personal Google connections are per profile and organization. Even administrators
cannot read another profile's mailbox through the CRM. Email text retrieval rechecks
record visibility and mailbox ownership. Company mail includes only visible contacts.

Sending, replying and forwarding require the record's Edit permission plus an active
personal Gmail connection with `gmail.send`. Internal email comments require Notes
and use the existing shared internal record-note model. They reference the subject;
they do not grant mailbox access or automatically copy the message body. Teammates
with record access can read the comments. Automated CRM notifications use the separate
system sender. See [Google integrations](../self-hosting/google-connected-accounts.md).

Contact/Company Activity combines shared meaningful record history with the viewer's
private email projection. Opening records, downloading files and unchanged saves do
not add audit noise. Actors display their saved user name, falling back to email;
existing linked activity uses the current user name. Historical unaudited changes
cannot be reconstructed.

## Enforcement and verification

Use `IsAuthenticated` + `HasOrgContext` for organization APIs, adding `IsOrgAdmin` or
an explicit Settings read/manage check where required. These coarse checks do not replace
scoped queries or `require_record` for record actions. Resolve related IDs inside the
selected org and check both sides of associations. UI hiding never secures a direct
request. API errors must retain the correct forbidden/not-found behavior.

Regression coverage includes `test_crm_roles.py`, `test_expanded_permissions.py`,
`test_settings_access.py`, `test_platform_access.py`, `test_invite_only_access.py`,
`test_invitation_setup.py`, `test_attachment_permissions.py`, and the record-mail tests.
Frontend tests cover the Settings matrix and fresh role changes in the application
shell. This document describes verified current boundaries, not a blanket security
audit of every historical endpoint.
