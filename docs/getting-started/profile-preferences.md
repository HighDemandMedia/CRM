# Profile preferences

Implemented locally:
- Name, sign-in email (read-only), phone, language and preferred time zone.
- Photo upload controls are not offered in Profile. Existing photos can still be displayed.
- In-app notification preferences per organization: master switch, mentions and ticket comments. The dispatcher checks these preferences before creating new notifications. Existing notifications remain.
- Preferred Gmail access scope: send only, or read/send/sync. This is a saved preference, not an OAuth grant.
- Separate Gmail and Google Calendar cards, explicitly marked Setup required.

Timezone is stored as a personal preference; it does not change organization reporting/day boundaries. Calendar timezone rendering still uses the existing calendar implementation.

Organization name, currency, timezone and business hours stay under organization settings, not Profile.

## Google integration work still required

Google sign-in does not constitute a Gmail/Calendar connection. No integration tokens or connected accounts exist yet; connecting, selecting calendars, synchronization and disconnection are not implemented. The current UI deliberately disables connection buttons.

Before enabling these cards:
1. Confirm the email access scope with the owner.
2. Configure a Google Cloud OAuth application for the deployment and local callback URLs. The current local Google client ID and client secret are unset.
3. Implement user/organization-scoped OAuth with state/PKCE, secure token storage, refresh and revocation.
4. Add calendar discovery/selection, event mapping and synchronization with explicit conflict, cancellation and disconnect behavior.
5. Implement the chosen email workflow, then replace setup-required status with persisted connection state and real management actions.
6. Verify access isolation, expired/revoked consent, synchronization retries and disconnect behavior before enabling the buttons.

No account was connected and no Google consent was granted by this profile UI update.
