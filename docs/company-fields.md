# Companies

Companies uses the existing Account model and /accounts routes. The company detail layout remains unchanged; list, pipeline, create and edit are updated.

Properties: Domain (stored as website, plain domains normalized to HTTPS), Name, Company Owner, Industry, Number of Employees, Annual revenue and currency, Address/City/State/Zip Code/Country, Pages (up to 50 name + HTTP(S) link pairs), Source and Tags.

Contacts can be linked/unlinked through Account.contacts. This association appears in the contact's Companies section. It does not reassign Contact.account, the separate primary company field. Contacts and tag IDs are validated within the current organization. PATCH preserves relationships omitted from the request.

List columns can be selected, dragged, resized and sorted. Layout persists in browser storage separately from Contacts. Filtering applies automatically. CSV exports every matching active company using selected column order. Search includes company fields, pages, contacts, owner and tags.

Pipeline uses the same stages as Contacts: Lead, Follow Up, Qualified, Not Qualified and Lost. Dragging updates Stage and its entry timestamp while preserving Source. Existing companies start in Lead when migration 0010 runs. Stage time displays whole days, hidden on day zero, with a daily browser refresh and no server polling. Stage is selectable in create/edit and as a visible filter; Source remains available under additional filters.

Database migration: accounts.0009_account_source_pages adds nullable source and pages defaulting to an empty array, preserving existing records.
