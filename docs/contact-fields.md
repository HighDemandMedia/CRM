# Contact fields

Contact creation and editing use one Name field, Phone, optional Email, Source, Stage, Address, City, Zip Code, State, Preferred Communication Channel and Notes. Name, Phone, Source and Stage are required in the form and on API creation.

Source options: Meta, Google, TikTok, Organic, Call, Customer Referal, Employer Referal, Walk In.

Contact stages: Lead, Follow Up, Qualified, Not Qualified, Lost. These are independent of deal pipeline stages.

Communication channels: SMS, Call, Email. The field can be left unspecified.

Catalogs live in backend/contacts/choices.py and are returned by the contacts API for the frontend dropdowns. Notes uses the existing description field; Address uses address_line and Zip Code uses postcode (text, preserving leading zeros).

The API accepts name while retaining first_name and last_name compatibility. Existing split names remain unchanged when the displayed name is unchanged. New names are stored in first_name with an empty last_name. Existing contacts retain their data and have no assumed source, stage or channel. Partial API updates may omit required fields; the edit form asks for missing required values. Legacy imports and automatic contact creation continue to use their existing contracts.

Apply migrations before running the updated interface:

```sh
docker compose exec -T backend python manage.py migrate --noinput
```

Migrations 0014 and 0015 add the fields and finalize the selected catalogs. No contact rows are deleted or backfilled. Organization scoping and existing RLS policies remain in place.

## Contact views

The Contacts module offers List and Pipeline views. List starts with Name, Phone, Email, Source, Stage and Contact Owner. Edit columns can show or hide all contact form fields plus account, status and timestamps; at least one data column stays selected. Open/Edit actions remain available even when Name is hidden. Preferences are saved in this browser, not synchronized across devices.

Pipeline uses the contact stage catalog returned by the API. Each card shows name, phone, email, source, owner and preferred channel. Contacts without a recognized stage appear under No stage. Editing a contact's Stage changes its column on the next board load. Deal pipelines are independent.

Both views retain the existing contact filters and organization permissions. List uses 25 contacts per page; each pipeline column independently fetches 25 contacts and its own total, with Previous/Next controls. The board does not infer column totals from the first page of the contact list. The API's `stage=UNASSIGNED` filter includes null, blank and unrecognized stages.

## Stage age and contact history

Migration 0016 adds the server-managed `stage_entered_at`. New contacts start their clock at creation; subsequent Stage changes reset it. Editing other fields does not reset it. Existing contacts retain a null value because their historic stage entry time is unknown. Pipeline cards show this elapsed time in color and the creation timestamp at the lower right. Displayed dates include the timezone; elapsed times refresh every minute while the page is open.

The contact profile shows its original creation timestamp and creator, stage entry timestamp, and Contact history. History reads organization-scoped Activity rows only after the existing contact access check. Server-side signals record Contact creation, scalar field changes (including before/after values), deletion and many-to-many assignments/links; generic contact notes and attachments record additions, edits and removals. Opening the contact and requesting an attachment download are also recorded. A download-request event does not assert that the client completed the transfer. User identity is derived from the authenticated request's organization profile and snapshotted; operations without an attributable user are labeled System / actor unavailable. Creation can use an explicitly supplied server-side creator for background operations.

Contact saves and their audit writes run in the same transaction. Existing Activity RLS applies; no public write endpoint for history is added. Deleted-contact events remain in Activity, but a deleted contact no longer has a profile page. Older notes, files and creation information remain visible even if they predate detailed history. Prior modifications cannot be reconstructed when no historical record exists. The stage clock and creator are not writable through the contact form/API serializer.

This tracks persisted CRM operations, not external phone calls or emails merely launched from a link; those need a note or a future communication integration. Direct SQL, QuerySet.update/bulk_update and bulk_create bypass Django save signals and must explicitly emit audit records if introduced for contact business operations. No full-history backfill is fabricated.

## List column order and fixed widths

Edit columns only selects visible fields. Drag a column header name onto another header to insert it at that position; the order is saved in this browser. Alt + left/right arrow keys on the header provide a keyboard alternative. Header edges retain drag resizing, arrow-key width adjustment and double-click to fit content; there are no numeric width controls in Edit columns. Existing column selections and saved widths are preserved.

A newly displayed column is measured against its header and the currently loaded contact rows, then its width is saved. Loading another page or changing viewport size does not automatically resize it. Fit widths to content explicitly recalculates selected widths against the current page. Column widths have a 60-pixel minimum. Long content in manually narrowed cells is truncated with an ellipsis and remains accessible through its tooltip or by opening the contact.

The contact list uses its own fixed-layout table styles instead of the app's mobile card transformation. Small screens retain the same column widths and use horizontal scrolling. Preferences are local to the browser and are not synchronized between devices.

## Sorting by column

Click a column name to sort ascending; click it again to sort descending. The arrow and aria-sort indicate the direction. Dragging a header reorders columns without triggering sorting. Sorting is applied by the API before pagination and within the existing filters/access permissions; switching sort starts at the first page. Text is case-insensitive, dates sort chronologically, and blank values appear last. Phone numbers and ZIP codes are text identifiers. Catalog columns sort by their displayed labels. Multiple owners are represented by the first email alphabetically; account sorting uses the primary account or first linked account alphabetically, then the free-text organization. Unknown sorting keys fall back to creation order.

Column dragging uses a compact rectangular preview of only the column title with a drop shadow, drawn once at drag start without rendering contact values. The source column is dimmed, and a blue vertical insertion line spans the destination column header and cells. Crossing a header midpoint moves the insertion target before/after that column; dropping uses that boundary and saves the order. Approaching the horizontal scroll area edges scrolls the table. Canceling a drag clears the preview and marker without saving a new order.

## Moving contacts in the pipeline

Drag a contact card to a different stage; the destination is outlined in blue. Dropping saves a stage-only PATCH through the current authenticated session, then refreshes the board and counts. The existing backend records the actor, old/new stage and timestamp in contact history and resets stage entry time. Same-stage drops do nothing. Only one move is submitted at a time; failed saves show an error and keep the original board. Cards omit the Stage selector; the Edit contact form remains available for changing stage without dragging. No stage is a legacy source column, not a drop destination, because stage is required. Existing filters and pagination continue to apply after moves.

Pipeline cards show name, phone, email and owner only when present, associated deal totals grouped by currency (only deals accessible to the current user), and time in stage. Missing amounts display Not set, with no assumed currency. Source, channel, creation date and edit button are omitted from the cards; the name opens the full profile.

Pipeline stage age shows completed 24-hour days only. Day zero (the first 24 hours) and unknown legacy ages are hidden, including their label container. A shared browser timer refreshes once every 24 hours when the pipeline is visible, with no server requests. Page loads and successful moves use the current time. Exact stage-change timestamps remain stored once per change for history.

Appointment is an optional date/time field on contact create/edit forms and the contact profile. The picker uses the browser local timezone and submits an ISO timestamp; the database stores a timezone-aware instant. Clearing the field removes the appointment, and changes are recorded by the existing contact history. Existing contacts start with no appointment.

Contact forms support multiple existing tags and inline tag creation with a color palette and preview. Tag creation retains existing administrator permissions; organization members can assign available tags. New tags are selected automatically and linked when the contact is saved. Unchanged tag selections are omitted from PATCH. Colored badges appear on pipeline cards and the contact profile, using additive tag_details in the read API.

Tags are presented as one searchable dropdown field. Existing selections appear as colored badges; typing filters available tags. A new name reveals the color selector and inline Create action (Enter also selects an exact match or creates the new tag). Search filtering never removes selected tags from submission.

Contact search and filters: owner, stage, inclusive creation-date range and last-activity-date range. Last activity is the newest org-scoped Contact history event (including opening the profile), falling back to creation for legacy records without history. Date ranges use the backend timezone (UTC). Filters apply before pagination. CSV export reuses the same query and sorting, fetches all matching pages, and preserves selected column order. Dates are exported as stored ISO timestamps; UTF-8 BOM, quoted cells and spreadsheet-formula neutralization support spreadsheet use. No extra export permissions are granted.

The contact toolbar keeps Search, Contact Owner, Stage and Tags visible. Filters opens a panel with Add filter; property filters can be added and removed individually, and date properties offer inclusive From/To bounds. Search covers contact text, notes, address, custom-field contents, timestamps, catalog labels, owner email, tags and linked account names within the current organization. CSV export uses the same expanded query.

Contact filters apply automatically: selections, cleared values and removed property filters update immediately; text entry waits 350 ms after typing stops. Pagination resets when filters change, focus and scroll are preserved, and Apply/Clear controls are omitted. Clearing each field or choosing All/Any removes its restriction.

Contact profile uses three desktop columns: editable Info / Properties; Activity above Notes; Companies, Deals and Attachments. Tasks and Tickets remain in collapsible sections. Mobile stacks sections. The shared contact form supports an inline autosave mode: only changed fields are PATCHed, writes are serialized, and changes made while saving are queued. Text saves after a short pause or leaving a field. Validation failures keep local input with a Retry option. Existing create/edit forms retain manual saving. Notes and attachments have separate forms; both refresh the profile/history after successful saves.

The contact profile keeps all three columns in the available screen height, with independent vertical scrolling for Properties, Activity/Notes and related records. Narrow screens use horizontal scrolling across the columns instead of stacking them. The required-fields explanatory sentence is removed from contact forms; required-field indicators remain.
