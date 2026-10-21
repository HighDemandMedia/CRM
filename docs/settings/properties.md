# Properties catalog

`/settings/custom-fields` now selects one CRM object and shows its system and custom properties, field type, required status, and records containing a value. The catalog API is admin-only and counts only the current organization's records for the selected object.

System properties are a read-only catalog of existing model fields. They are not editable custom definitions, and custom definitions cannot reserve a system field key. Existing custom definitions retain their identity and stored values. New property keys are generated once; changing a label does not change the key or field type. Turning off a custom property preserves existing values.

Usage means a saved value, not the number of times a field was edited. False and zero count; null and empty text do not. Association counts count records, not the number of links.

## Record-form integration

Contacts, Companies, Deals, Tasks and Tickets use shared property inputs in configured creation forms, stage requirements and custom-property editing. Format checks run in the UI and again in the API. Creation-form and pipeline settings determine which fields are required. Existing records are not backfilled; submitted values must meet the current format rules.

## Additional field types

The original six types remain. Added email, phone, URL, integer, percentage, money, local time and multiple selection.

API values inside `custom_fields`:
- `phone`: exactly 10 ASCII digits, without country code, spaces or punctuation. Values remain strings to preserve leading zeroes. This also applies to system phone fields.
- `email`: an email address with valid syntax; validation does not verify mailbox ownership or delivery.
- `url`: HTTP/HTTPS only; URLs without a scheme receive HTTPS.
- `text` / `textarea`: text only, up to 255 / 10,000 characters. Multiline text supports line breaks and tabs; other control characters are rejected.
- `date`: a real calendar date in YYYY-MM-DD format.
- `integer`: a JSON integer within JavaScript's safe integer range.
- `percentage`: number between 0 and 100, inclusive.
- `money`: decimal string with up to 14 integer digits and 2 decimals; normalized to two decimals to avoid binary floating-point storage. Uses the organization's currency convention; does not perform currency conversion.
- `time`: local time as `HH:MM:SS`, without date/time zone.
- `multi_select`: array of configured option values; repeats removed, unknown values rejected. Empty arrays clear optional values and fail required validation.

Selection labels can change while their option values stay stable. Formula, computed rollup, file and user/record relation custom fields are not included in this change.
