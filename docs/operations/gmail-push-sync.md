# Gmail automatic updates

## Behavior

Authenticated Google Pub/Sub notifications enqueue the existing Gmail sync. They
contain a mailbox address and history ID, not email bodies. The sync reads changes
since its saved history cursor, retains only mail related to contacts accessible
to the connected user, and preserves existing tenant and personal-mailbox privacy.
Notifications may include unrelated messages or label changes; Gmail cannot watch
only CRM contacts. Unrelated messages are not displayed or retained in the CRM.

Duplicate notifications coalesce. A notification received during an active sync
causes a subsequent pass. Incremental pages continue after five seconds instead
of waiting for the scheduled fallback. Watches renew daily during synchronization.
The existing five-minute scheduler remains the recovery path for dropped or
delayed notifications, worker failures and expired history. No new user scopes.

An open Contact or Company checks a small permission-scoped cache revision every
10 seconds while Activity or Emails is visible. Changes refresh the record and
loaded email pages without a manual button or full navigation. Hidden browser
tabs stop checking, transient failures back off to at most 60 seconds, and revoked
record access stops checking and reloads the access state. This is near real time,
not a guaranteed delivery time. `last_sync` remains the last successful sync pass;
message dates remain Google's original sent/received time.

## Activation (not performed by adding this code)

1. In the **dedicated Gmail project**, enable Pub/Sub and create a topic such as
   `crm-gmail-changes`. Gmail requires the topic to belong to the project making
   the `users.watch` call. Do not use the Calendar or Google sign-in projects.
2. On that topic only, grant `roles/pubsub.publisher` to
   `gmail-api-push@system.gserviceaccount.com`.
3. Create a service account used solely for authenticated Pub/Sub delivery; do
   not generate a private key. Configure Pub/Sub's service agent to mint OIDC
   tokens for this service account, following Google's authenticated-push guide.
4. Create an **authenticated push subscription** with wrapped messages and a
   60-second acknowledgement deadline. Use the direct API endpoint:
   `https://hdm-crm-staging-api.onrender.com/api/integrations/google/gmail/push/`.
   Set the OIDC audience to exactly that URL and select the delivery service
   account. Enable retries. The endpoint acknowledges only after queueing.
5. Configure all four variables together on API, Worker and Scheduler:

   ```text
   GOOGLE_GMAIL_PUSH_TOPIC=projects/hdm-crm-gmail-production/topics/crm-gmail-changes
   GOOGLE_GMAIL_PUSH_SUBSCRIPTION=projects/hdm-crm-gmail-production/subscriptions/<subscription-name>
   GOOGLE_GMAIL_PUSH_AUDIENCE=https://hdm-crm-staging-api.onrender.com/api/integrations/google/gmail/push/
   GOOGLE_GMAIL_PUSH_SERVICE_ACCOUNT=<delivery-service-account-email>
   ```

   Resource names must match what was actually created. Keep all four empty to
   retain polling-only mode. This configuration needs no new credential or change
   to Gmail/Calendar/login OAuth clients or SES system email delivery.
6. Deploy API (including migrations), Worker, Scheduler and Web. Migrations are
   additive; the timestamp column has a database default for older workers during
   a rolling deployment. Allow the next scheduled pass to register the watches.
   Existing connected users do not need to reconnect solely for push.

## Verify after activation

- Confirm watches have a future `mail_watch_expires_at`, the configured topic and
  a recent `mail_watch_renewed_at`. Failed renewal logs a connection ID only and
  leaves polling available. Monitor Pub/Sub delivery errors/backlog.
- With authorized test mail only, receive/send a message involving a CRM contact;
  verify Activity and Emails update while another message stays expanded.
- Confirm an unrelated sender does not appear, a different user cannot read the
  mailbox, duplicates produce one message, and Calendar remains connected.
- Verify invalid identity/audience/subscription fails and valid delivery gets 204.
- Check tab visibility, filters, loaded pages, transient outages and recovery.
- A mailbox can belong to several org memberships. Notifications route only to
  active connected memberships in active non-closing organizations. Do not call
  `users.stop` for one membership: a Gmail watch is shared per mailbox/project.

## Rollback

Clear all four push variables and redeploy the backend services; keep the existing
scheduled sync. Disable the push subscription to stop retries to a disabled
endpoint. Do not revoke Google grants or remove OAuth clients. No database
rollback or customer-data deletion is required.

## References

- [Gmail push notifications](https://developers.google.com/workspace/gmail/api/guides/push)
- [Authenticated Pub/Sub push](https://docs.cloud.google.com/pubsub/docs/authenticate-push-subscriptions)
