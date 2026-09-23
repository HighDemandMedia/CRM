# Properties catalog

`/settings/custom-fields` now selects one CRM object and shows its system and custom properties, field type, required status, and records containing a value. The catalog API is admin-only and counts only the current organization's records for the selected object.

System properties are a read-only catalog of existing model fields. They are not editable custom definitions, and custom definitions cannot reserve a system field key. Existing custom definitions retain their identity and stored values. New property keys are generated once; changing a label does not change the key or field type. Turning off a custom property preserves existing values.

Usage means a saved value, not the number of times a field was edited. False and zero count; null and empty text do not. Association counts count records, not the number of links.

## Remaining record-form integration

This change implements property administration. The backend validates and persists custom values, and Leads already exposes custom fields. The adapted Contacts, Companies, Deals, Tasks and Tickets interfaces still need dynamic rendering and submission of these properties in their create forms and editable/read-only property sections. Required custom definitions already apply to backend creation validation; do not mark a field required for those interfaces until that integration is complete. Existing records are not backfilled.

## Additional field types

The original six types remain. Added email, phone, URL, integer, percentage, money, local time and multiple selection.

API values inside `custom_fields`:
- `email`, `phone`, `url`: strings; phone separators are removed, URLs without a scheme receive HTTPS. Only HTTP/HTTPS URLs are accepted. Country codes are not inferred.
- `integer`: a JSON integer within JavaScript's safe integer range.
- `percentage`: number between 0 and 100, inclusive.
- `money`: decimal string with up to 14 integer digits and 2 decimals; normalized to two decimals to avoid binary floating-point storage. Uses the organization's currency convention; does not perform currency conversion.
- `time`: local time as `HH:MM:SS`, without date/time zone.
- `multi_select`: array of configured option values; repeats removed, unknown values rejected. Empty arrays clear optional values and fail required validation.

Selection labels can change while their option values stay stable. Formula, computed rollup, file and user/record relation custom fields are not included in this change. The record-form integration limitation above still applies.
