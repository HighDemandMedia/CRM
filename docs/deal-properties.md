# Deal properties

Create/edit fields: Name*, Amount, Stage*, Close Date, Deal Owner*, Priority* (Low/Medium/High), Source* (Contacts catalogue), Address/City/State/Zip Code/Country and Associate* (company and/or contacts).

At least one association is required. API validates owner and contact IDs and company against the current organization. PATCH preserves omitted relationships and supports clearing one association when another remains. Legacy deals may retain blank new fields until edited; no priority, source or owner is invented by migration.

Amount and Close Date are optional, including closed stages. Line-item totals remain protected from manual overwrite. The kanban continues to record the closing actor/date on a close action when no date is set. Existing stage identifiers, history, currencies and unrelated fields remain intact.

Migration opportunity.0018_deal_properties adds priority and address fields and updates the source choices. Earlier source values remain stored; the new form requires selection from the Contacts catalogue.

## List and pipeline views

Deals uses the Contacts-style toolbar, automatic filters, column selection, persisted column order/widths and sortable headers. Stage cells use the segmented indicator with six actual stages. Pipeline cards move between stages through the existing permission-checked move endpoint and show daily stage age. Each stage is paginated independently; the same filters apply to both views and CSV export. CSV exports all matching pages in selected column order. The former view=board URL remains accepted.
