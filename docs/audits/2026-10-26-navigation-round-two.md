# Navigation latency: second pass — 2026-10-26

## Status

Local only. No commit, push or deployment. Production data/configuration unchanged. Baseline: da9e8884d21643727946a67bd7078d8c5bab1576, with the same opt-in measurement instrumentation as the candidate.

## Root cause and implementation

Contacts, Companies and Deals called server `parent()` for presentation data already inherited by the page. SvelteKit re-executed ancestor server loads, including people and tags. The normal batched-board/list path now inherits those catalogues and combines stage presentation in universal page loads. Older API versions without batched boards keep the existing server-parent fallback and stage pagination.

The list/pipeline switch preloads on pointer/focus intent. SvelteKit owns the response: there is no shared record, identity or permissions cache. Hints older than five seconds force fresh navigation data. Errors on speculative reads do not prevent a normal retry. Existing Tasks/Tickets callbacks are retained.

A compact delayed loading label and aria-busy complement the existing progress line. The final version keeps content stable, without dimming it or changing its interactivity while navigating. No new colors or dependencies.

API authorization is unchanged. Organization UI context is still requested on URL changes, including query changes, so this optimization does not remove permission/onboarding/lifecycle checks. A pathname access in the installed SvelteKit version tracks the whole URL; it must not be assumed to refresh only when changing modules.

## Measurement

Two local production builds, ports 5192/5193, same API, session, organization CRM Prueba A and demo records. Five alternating rounds per variant. Twenty-five module navigations and ten Contact view switches per variant in the final run. No database mutations or outgoing messages. The metric is beforeNavigate through afterNavigate, DOM tick and the next animation frame. It excludes automation round trips and any preload that finishes before clicking; it is not INP, LCP or a full paint measurement. No deliberate hover wait was used.

Median milliseconds (range), five samples per row and version:

| Operation | Before | After |
| --- | ---: | ---: |
| Companies | 67 (44–68) | 67 (36–68) |
| Deals | 67 (67–136) | 73 (46–78) |
| Tasks | 67 (41–68) | 68 (68–72) |
| Tickets | 140 (134–201) | 143 (124–145) |
| Contacts | 66 (40–67) | 34 (34–39) |
| pipeline | 68 (61–95) | 61 (59–64) |
| list | 92 (62–96) | 62 (61–92) |

The final Contact pipeline-to-list median fell from 92 to 62 ms (about 33%). List-to-pipeline was 68 to 61 ms. Earlier batches varied substantially; notably Companies moved between 40 and 67 ms and some earlier list-return samples were 24–31 ms. These preliminary figures do not supersede the final run. Module timings do not demonstrate a consistent overall speedup: Deals, Tasks and Tickets were slightly slower in the final sample, within the variability observed across rounds. No universal improvement or production latency reduction is claimed.

A separate bounded backend log check of ten Contact view switches per version confirmed 40 versus 20 relevant API reads: before, 10 each of ui-context, people, tags and contacts; after, 10 ui-context and 10 contacts. One independent notification refresh is excluded. All returned 200. The measured log window was 2026-10-26T19:31:30.866Z–19:31:37.170Z; later changes were limited to loading presentation.

## Verification

- 129 frontend test files, 1,049 tests passed.
- Type checking: zero errors/warnings. Production build passed. Formatting/ESLint passed.
- Regression coverage: custom stages, independent stage offsets/totals, search/filter parameters, list offsets, API permission denial propagation, legacy-board fallback, no presentation state retained across organizations, preload age/error behavior and request-local diagnostic isolation.
- Local browser: list/pipeline, search, stage filtering, user options in creation form, cancel, browser back/forward. No browser console errors observed.
- Visual checks at normal desktop, 820×1180 tablet and 390×844 mobile; viewport reset afterwards. Existing horizontal table/board scrolling retained.
- No backend, schema, RBAC or tenant-isolation changes. Full multi-role production QA was not repeated in this local-only task.

## Remaining work / release boundary

Do not describe the navigation problem as fully solved. The retained ui-context and record requests still depend on API/database/network response time. Before a later release, use the same production account and navigation sequence, inspect server timing and API timings, and compare concurrent-load behavior. Only then decide whether API query/connection work is warranted. Do not weaken permission refresh or use shared tenant data caching to improve a benchmark.

CRM_PERFORMANCE_DIAGNOSTICS defaults to false. When enabled it emits aggregate numeric Server-Timing and hidden navigation-duration attributes, without URLs, tokens, identities or payloads. api_total sums overlapping completed calls; it is not critical-path latency and does not include work that finishes after the response starts streaming. Disable after a bounded diagnostic session.

Evidence: deliverables/latency-local-release-candidate-2026-10-26.json and navigation-{desktop,tablet,mobile}-2026-10-26.png in the workspace parent. Earlier comparison JSON files are retained as variability evidence.
