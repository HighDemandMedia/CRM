# CRM visual system

Implemented locally on 2026-10-05 against main commit `3cee1aa`. This change is presentation-only, except for replacing retired navigation destinations (Invoices in mobile navigation and Leads in the root error page) with active Calendar and Companies destinations. No backend, migrations, dependencies, permissions, integrations, or laboratory modules were changed.

## Foundation

`frontend/src/lib/styles/design-tokens.css` is the single foundation, imported by `app.css`. Existing Tailwind and `v2` variables alias these tokens so both component families and portalled content use the same values.

| Role                                   | Value / usage                                                           |
| -------------------------------------- | ----------------------------------------------------------------------- |
| Canvas                                 | Paper `#F6F4F1`                                                         |
| Secondary surface / decorative divider | Stone `#E4DED2`                                                         |
| Main action / active navigation        | Coral `#F95C4B`, black text                                             |
| Main text / navigation background      | Black `#000000`                                                         |
| Cards                                  | White (adaptive in dark mode)                                           |
| Input boundary / focus                 | Separate darker tokens; Stone is too faint for these roles              |
| Semantic states                        | Distinct success, warning, danger, information, external calendar pairs |

New presentation code should consume semantic tokens rather than introduce additional hex values. Maintain customer-configured web-form appearance; `WebFormPreview.svelte` is deliberately not recolored to the CRM palette.

Typography remains the existing bundled Manrope. The reference labels its serif as Big Caslon; [Carter & Cone](https://carterandcone.com/font/big-caslon/) describes it as a display family. No Big Caslon web font or evidence of a web license was found in the repository. Adding it requires the appropriate WOFF2 files and web-use rights for the deployment domains. A screenshot or a locally installed desktop font is not that asset. The proposed Big Caslon heading / Manrope interface pairing remains unapproved; no replacement was made. `--crm-font-title` currently aliases the existing UI face.

| Token     | Size     | Purpose                                |
| --------- | -------- | -------------------------------------- |
| text-xs   | .75rem   | Metadata and compact supporting labels |
| text-sm   | .875rem  | Controls and record tables             |
| text-base | 1rem     | Body copy / mobile input text          |
| text-lg   | 1.125rem | Section headings                       |
| text-xl   | 1.5rem   | Page headings                          |
| text-2xl  | 2rem     | Record headings / key totals           |
| text-3xl  | 2.5rem   | Exceptional prominent totals           |

Spacing uses a .25rem base with steps through 3rem. Radii, shadows, action states, line heights, control heights and focus are centralized. Layout-specific geometry (column widths, chart positioning and breakpoints) remains local. Mobile shared controls use 2.75rem touch targets; tables retain their existing contained horizontal scrolling and resizing behavior.

## Implementation coverage

- Main shell, navigation, preferences navigation, mobile navigation and search.
- Today, contacts, companies, deals/pipelines, calendar, reports, tasks and tickets.
- Record details, associations, notes, attachments, deletion confirmation and creation panels.
- Organization, teams, roles, properties, pipelines, tags, web forms, profile/integrations and notifications.
- Help, knowledge base, authentication, organization selection, customer portal and error surfaces.
- Hover, selected, active, disabled, focus and validation treatment through shared tokens/components.

The active route import graph was inspected (144 presentation files); unused legacy components and the separate laboratory were excluded. Existing route-specific styles were migrated rather than replacing the UI library or changing domain behavior.

## Verification

- Frontend: 463 tests pass in 65 files, including 56 new light/dark token contrast checks.
- Contrast checks enforce 4.5:1 for normal text pairs and 3:1 for control boundaries/focus. Black on Coral is explicitly checked across default/hover/active states.
- Svelte check: 0 errors, 0 warnings.
- Production build: passes with adapter-node.
- ESLint: 0 errors, 280 warnings. An isolated copy of HEAD produced the same 280 warnings; no lint rules were disabled.
- Changed files formatted with Prettier; final whitespace diff checked.
- Browser QA on local main with existing demo records: desktop 1280px, tablet 834px and mobile 390px.
- Visually reviewed login, Today, populated contacts and contact detail, calendar, reports, tasks, tickets, roles, web forms, profile/integrations, search and notifications.
- Checked invalid contact creation without saving, mobile form layout, long record/organization labels, report data table (31 rows), empty web forms, disabled integrations and keyboard focus in search.
- Corrected cramped role actions on tablet, low-contrast completed tasks, task title wrapping and validation scroll positioning.

Screenshots are saved outside the repository at `../work/visual-system-2026-10-05/`.

## Limits and follow-up

Big Caslon remains pending a licensed web asset and approval of the pairing. Token tests and representative browser checks do not constitute an exhaustive WCAG certification: full assistive-technology, physical-device and cross-browser testing is still recommended. Dark tokens are covered by contrast tests; every dark screen was not manually exercised. Customer portal authenticated flows and real external integrations were not exercised by this visual change. No production data was changed, and no commit, push or deployment was performed.

## Property-driven lists and responsive references

The active Contacts, Companies, Deals, Tasks and Tickets lists use the existing
organization UI-context property catalog. System properties except Notes (`description`) and Record ID (`id`) are visible by default
in the configured property order; active custom properties can be selected in Edit
columns. Show all includes custom properties; Reset restores system defaults.
Preferences use a new version, scoped to the organization and signed-in user, so
old six-column layouts do not suppress the new defaults. Browser storage is optional.

The existing column aliases and supported server sorting are retained. Newly
available properties are displayable/exportable; this change does not add server
sorting for custom properties. CSV exports resolve column definitions on the server
and retain export permission checks and spreadsheet formula escaping.

On small screens, selected columns remain in a horizontally scrollable, keyboard
focusable table. The column selector moves into a viewport-bound panel with search,
selection count, Show all, Reset and Close. No new UI dependency is required.

Public design references reviewed:

- [Carbon data tables](https://www.carbondesignsystem.com/building-blocks/core/components/data-table/guidelines): common toolbar, consistent table controls and readable density.
- [PatternFly tables](https://www.patternfly.org/components/table/): responsive table patterns and column management.
- [Twenty CRM](https://github.com/twentyhq/twenty): public CRM reference for object views and field customization; no source code copied.

Validation includes catalog order, custom values, stale preferences, CSV columns,
frontend checks/build, backend relation visibility and constant task-list query
counts. Visual checks use the local demo organization at desktop, tablet and phone
widths. Hosted Render services are unchanged.

## Website brand alignment (2026-10-05)

The current UI uses Inter, as requested, replacing the earlier Manrope / pending
Big Caslon proposal. Inter is bundled from `@fontsource-variable/inter` under the
SIL Open Font License; the normal Latin variable face is served locally with swap
and the requested system fallback stack. Its license is included under
`frontend/static/fonts/Inter-OFL.txt`.

The website https://highdemandmedia.com/ supplies red `#C3110C`, orange `#E6501B`,
dark text `#1D0502`, muted text `#4A302C` and maroon `#740A03`. Shared primary
buttons use the 135-degree red/orange gradient with white text and a 12% black
overlay (18% hover, 24% active) to maintain small-text AA contrast. The reusable
button component, v2 buttons and mobile creation button share these tokens.
CRM surfaces, density and semantic status colors remain suited to data entry.

Notes and Record ID stay in Edit columns, but are excluded from default/reset
selections across all five active object lists. Explicit saved selections remain
intact. Use Reset to apply the new default to an already customized list.

Validation: 471 frontend tests pass, including defaults/manual selection and
contrast samples throughout each gradient state in light/dark themes; Svelte
checks and production build pass. Local browser checks cover the branded login
and populated contact list, reset behavior and manual ID selection.
