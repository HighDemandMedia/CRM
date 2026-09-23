# Contact merging

Implemented through **Actions → Merge** in a contact's Properties and in the Contacts list. The list menu also offers Open and Edit; Edit keeps the existing drawer flow.

Only organization admins (including the creator/Super Admin) can merge contacts. Both records must belong to that organization. This is enforced by the backend, independently of menu visibility.

## Review and confirm

Search for the secondary contact by name, email or phone. The current contact is the default primary; the comparison lets you switch the primary. Choose between differing names, contact details, company, stage and custom property values. Empty primary values default to the secondary value. Tags, owners and teams are combined.

Confirmation states the consequences and requires acknowledging that the records represent the same contact. The primary keeps its UUID and creation date. There is no automatic undo.

## Data preservation

- Transfer companies, deals, tickets, tasks, calendar attendance and other contact links without recreating related objects or sending invitations.
- Retain notes, attachments, activity authors and original timestamps. Portal comment authors remain linked to the original author.
- Repoint invoice and estimate contact links without changing financial or legal snapshot values.
- Archive the secondary contact with a snapshot of both original records. Hide it from ordinary lists, searches and pickers. Old profile links resolve to the surviving contact, subject to its access permissions.
- Revoke the secondary's pending portal login codes. Existing portal sessions cease working because the archived contact is no longer active/available.
- Record the actor, time and both IDs in Activity.

Selected email and phone become the primary contact details. Other values remain in the archived snapshots; this version does not expose an alternate-email/phone editor or automatic unmerge.

The comparison expires after 30 minutes. A changed record requires a fresh comparison. Merge uses one database transaction and locks both contacts in stable ID order. Failed stage-entry rules roll back the whole merge. Repeated submission of the same completed merge is idempotent.

## API

- `GET /api/contacts/{primary_id}/merge/?q=...`: search up to 15 matching contacts.
- `GET /api/contacts/{primary_id}/merge/?secondary={id}`: comparison and signed review token.
- `POST /api/contacts/{primary_id}/merge/`: `token`, `choices` mapping property keys to `primary` or `secondary`, and `confirm: true`.

Internal IDs remain immutable. Archived records cannot be updated through the ordinary contact endpoint.
