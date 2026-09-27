# High Demand Media Help

Help is pinned in the navigation footer and available to demo users. It contains Contact support and Knowledge base. The standalone navigation link to the legacy tenant Knowledge base (`/solutions`) is removed; existing organization articles are not deleted. `/help/new` redirects to the new form. Older enterprise ticket detail routes remain for compatibility but are not linked from this product help center.

## Requests

`GET /api/help/requests/` returns authenticated sender information, fixed support recipient and mail mode. `POST` requires an active authenticated organization profile and one of:

- Bug: subject, CRM area, actual vs expected result, and impact on work. Frequency, reproduction steps and affected-page URL are optional. Three compact sections separate location, symptoms and triage.
- Feature: idea title, CRM area, current problem and desired outcome. Audience and proposed solution are optional; the latter is collapsed by default.
- Help: topic and a single question, with optional previous attempts. Subject is derived by the server from the question. Relevant product guides are suggested locally as the user types and open in a separate tab to preserve the form.

Drafts survive switching request types within the page; optional context is disclosed on demand. No browser storage is used. Bug impact, frequency and feature audience use validated choices with readable email labels.

All recipients are server-fixed to info@highdemandmedia.com. Reply-To is the authenticated user's email. The message includes verified name, organization name/ID and a reference. It does not include CRM records, notes, browser storage, tokens or automatic screenshots. Extra form fields belonging to another request type are discarded. Sending is synchronous through the configured Django mail backend; errors preserve form values and do not show success. Authenticated users are limited to ten POST requests/hour. A request UUID scoped to user and organization suppresses duplicate successful submissions for 24 hours; a short cache lock avoids concurrent submissions. Cache availability is required. A process crash between SMTP acceptance and cache persistence can still cause a duplicate retry; this is not a transactional email outbox.

Local Mailpit/console/file/locmem delivery in DEBUG is explicitly shown as local test mode. Those backends in production are unavailable (Mailpit included), and dummy delivery is always unavailable. SMTP success means the mail service accepted the message, not that the recipient read it. Production needs working SMTP/SES settings and a verified sender; no credentials were configured by this change. Automated tests use the in-memory mailbox and send no external email.

## Knowledge base

`/help/knowledge` searches product guides in `frontend/src/lib/help/articles.js`. Guides cover navigation, contacts, duplicates/merge, companies, deals, list/pipeline views, calendar, tasks/reminders, tickets, reports, properties/pipelines/tags, roles/teams, profile/notifications/integrations and deletion/associations. Content explicitly distinguishes planned vs actual deal closes, current-state reports vs historical snapshots, and setup-required Google integrations vs active connections. Update the relevant guide whenever a workflow changes. These guides contain product information, not organization/customer data.

## Form design references

Reviewed September 23, 2026. Adapted for our CRM rather than reproducing another product:

- [Atlassian bug reports](https://www.atlassian.com/software/jira/templates/bug-report): symptoms, expected/actual behavior, reproduction and frequency/context.
- [Salesforce IdeaExchange guidance](https://trailhead.salesforce.com/content/learn/modules/ideaexchange-basics/post-and-upvote-an-idea): problem, purpose/impact and use cases. Our form does not require users to design a solution.
- [HubSpot support](https://knowledge.hubspot.com/help-and-resources/get-help-with-hubspot): start with a question, offer related knowledge, then contact support. Our form keeps submission directly available.
