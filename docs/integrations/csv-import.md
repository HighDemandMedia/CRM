# CSV import

Administrators can select **Add [object] → Import [objects]** in Contacts, Companies,
Deals, Tasks and Tickets, in either list or pipeline view.
Export CSV remains a separate bottom-bar action, shown only with export permission.
The Add menu also offers the existing single-record creation form.

1. Download the CSV template. Headers reflect the organization's current properties,
   creation-form order and required fields, including active custom properties.
2. Fill the file and upload it. Open **Column guide** for formats and allowed values.
3. Review counts of total, valid and rejected records. Download an error-only CSV,
   or choose **Import valid records** to skip rejected rows. Correct the error file
   and reupload it to import the remaining records.

The import creates new records; it never updates existing ones. Files are committed in batches of 100. Each batch is atomic: if it fails, that batch
is rolled back, while earlier completed batches remain saved. Progress is visible
and retry resumes the same import without duplicating completed batches. Existing domain validation, organization
limits, audit history and normal assignment notifications apply. The preview is
read-only. A successful preview is bound to the file, actor, organization, object
and creation-form revision for 30 minutes. Repeating the same confirmed request
returns its existing result rather than creating duplicates.

## File format

- UTF-8 CSV, with optional BOM. Comma or semicolon delimiters are accepted.
- At most **1,000 records / 2 MB** per file. Split larger files into batches.
- Keep template column names. Optional columns can be omitted; unknown or duplicate
  headers and malformed rows are rejected. Blank rows are ignored.
- The template has headers only, so no demonstration record can be imported accidentally.
- Phones use international format, such as `+12025550123`. Email, URLs, numeric
  values, dates, country codes and custom properties use the normal CRM validators.
- Dates: `YYYY-MM-DD`. Datetimes: ISO 8601 with timezone offset.
- `assigned_to`: an active user's email in this organization. Required for Tasks
  and Tickets. The importer does not create users.
- `account`: an existing company's exact name. `contacts`: existing contact emails,
  separated by `;`. Matching is case insensitive and must identify a unique record
  in the same organization. Ambiguous/missing matches are errors.
- `tags`: existing tag names, separated by `;`; no new tags are created implicitly.
- Custom multi-selects use `;` between stored option values. Dropdowns use the values
  shown in the guide. Structured list fields use JSON.
- A required Associated Objects field is satisfied by company or contacts, as in
  the ordinary creation form.

## API

`GET /api/record-import/{module}/` returns field metadata, required flags, choices,
revision and upload limits. Supported modules: `contacts`, `companies`, `deals`,
`tasks`, `tickets`. All requests require an authenticated, active organization
administrator. Closed/read-only organizations cannot import.

`POST` to the same endpoint is multipart with `file` and `action=preview`. It returns
`total`, `valid`, `invalid`, `errors` (CSV line, field, message), `invalid_records`
(original values and errors) and a signed `token` approving only valid row numbers.
Global errors such as insufficient capacity block confirmation; rejected rows do
not consume capacity. Send the same file with `action=commit`, that token and
`start=0` to confirm. Subsequent requests use the returned cumulative `created`
count as `start`, until `complete=true`. Commit rechecks validation, permissions
and capacity under an organization lock for each batch. Lost responses can be
retried with the same start/token; the server returns durable progress.

Error reports preserve template fields plus `__import_row` and `__import_errors`;
those diagnostic columns are ignored on reupload, never trusted as validation.
Spreadsheet formula-like values are escaped in reports. The review shows only summary counts; rejected rows and their error details
appear exclusively in the downloadable report. A receipt stores only an identifier, organization, timestamp
and created count; the uploaded CSV is not retained. It is deleted with its organization.

The older `/api/contacts/import/*`, `/api/cases/import/*` and legacy lead uploader
remain separate compatibility endpoints. They do not back this UI; use the shared
`record-import` endpoint for the current five-object workflow.
