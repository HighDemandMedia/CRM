# Google Calendar change notifications

Calendar uses HTTPS `events.watch` channels; it does not use Gmail's Pub/Sub topic.
Existing Calendar scopes and OAuth projects remain unchanged.

## Enable after deployment

1. Deploy API, Worker and Scheduler with migration `common.0089`, then Web.
2. Set `GOOGLE_CALENDAR_PUSH_URL` on API, Worker and Scheduler to the public HTTPS API URL ending in `/api/integrations/google/calendar/push/`. The URL must reach Django directly, without a sign-in page, redirect or proxy requiring CRM session credentials. Keep the webhook's signed-token validation enabled.
3. The existing five-minute scheduler registers a channel for each active Calendar connection. No new user consent is required for an already valid connection. Channels renew automatically within a day of expiry.
4. Verify a Google-created event, reschedule and cancellation appear in the connected user's CRM calendar. Verify a CRM-created event, reschedule and cancellation reach Google. Use a test organization and authorized recipients: normal appointment notification rules still apply.
5. Verify disconnecting Calendar stops processing its callbacks, without changing Gmail; reconnecting rotates the generation and rejects old callbacks. Verify another user's calendar remains private.

## Behavior and recovery

- CRM appointment writes queue synchronization only after commit. Google-originated writes do not loop back into the queue.
- Google callbacks carry a signed, expiring token bound to organization, connection, authorization generation and channel. The worker also checks the stored resource ID, expiry, connection status and active organization/user before processing.
- Repeated callbacks coalesce. A change arriving during synchronization schedules a follow-up pass.
- Incremental sync keeps unchanged events; expired Google sync tokens trigger a full rebuild. Partial failures preserve the old cache. A daily full refresh advances the existing 90-day past / 365-day future window.
- The visible Calendar page checks a lightweight personal revision every ten seconds and reloads events only on change. It pauses in hidden tabs and backs off on errors. Background refresh preserves an open event editor.
- The five-minute scheduled sync remains as a fallback for lost notifications and failed queue submissions. Google push is best-effort, not an instantaneous delivery guarantee.
- Deleted connections and rotated generations reject old callbacks. Channels not explicitly stopped expire on Google within the requested seven-day lifetime. Successful renewal stops the superseded channel.

To disable new watch registration, clear `GOOGLE_CALENDAR_PUSH_URL` on all backend services. Existing callbacks then receive 503 until their channels expire; the scheduled sync continues. This setting does not revoke OAuth access or remove events.

Local automated tests use mocked Google responses and queue delivery. Real callback latency requires the deployed HTTPS endpoint and a connected test account.
