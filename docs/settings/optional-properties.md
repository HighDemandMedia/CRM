# Optional record properties

Contacts, Companies, Deals, Tasks and Tickets require only Name as a user-entered property. Record ID is an automatically generated, immutable UUID. Organization and audit fields are server-owned. Omitting a stage selects the model's initial stage; clearing it retains the current stage. Configured pipeline entry requirements and allowed source stages still apply, including on creation. Format checks, tenant permissions and workflow-specific dependencies remain enforced.

Custom property definitions still need a label, immutable internal key and field type. Their values are optional globally; administrators can require them for an individual pipeline stage. Existing values and pipeline configurations are preserved.

The required-property checkbox is removed. The catalog shows Name and the automatic Record ID as the globally required properties. A legacy unnamed record uses a display fallback in list/profile headings; no placeholder is stored as its name.

## Contact matching (implemented)

The contact form checks after a 450 ms pause and cancels stale requests. It shows up to five accessible records with matching email, normalized phone, or similar name, with an Open contact link. Matching stays inside organization and record visibility permissions; the current record is excluded while editing. Phone matching preserves country codes; a missing North American country prefix is labelled only a possible match. A stored, indexed phone key avoids scanning and normalizing every contact phone per request. No automatic merge occurs.

## Further duplicate prevention proposal

- Always compare within the organization and ignore empty values.
- Contacts: email as a strong match; normalized international phone as an additional duplicate warning because numbers may be shared. Offer opening the existing record before creating another.
- Companies: normalized domain as a strong match, with explicit handling for branches sharing a domain. Names alone should not be unique identifiers.
- Deals, Tasks and Tickets: repeated titles are valid; use Record ID to update existing records in integrations. An external-system ID can support reliable upserts.
- Never merge records automatically. If email and phone match different contacts, require review.

Existing populated-value duplicate checks have not been replaced: contact email remains unique per organization; company name still has its existing per-organization uniqueness constraint, now excluding empty names. Deal and ticket APIs retain their existing checks for populated names. The CSV importer also retains its existing phone/name duplicate checks. Consolidating these into the policy above is separate work.
