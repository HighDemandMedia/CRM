# Profile preferences

Reviewed against the implementation on 2026-11-01.

## First-time setup

An invited member confirms their name, CRM language and personal time zone before
opening the workspace. The initial administrator also confirms organization details.
The guided sequence is **Your profile → Appearance → Notifications → Review**, with
**Your organization** before Review for an initial administrator. Each step has its own
screen and progress indicator, with Back/Continue controls and a final Complete setup action.
These choices are optional; keeping the current defaults does not block completion.
Changing notification choices does not complete setup or change membership permissions.
Back/Continue preserves the current form draft; appearance and notification choices save
immediately. Reloading resumes the server-owned profile or organization phase, not an
unsubmitted draft.

## Profile and appearance

Profile contains name, read-only sign-in email, phone, language and time zone.
Profile information uses its Save changes button. Photo upload controls are not offered.
Organization name, currency, time zone and business hours stay in Organization settings.

Appearance offers Light and Dark using the same control during setup and in Profile.
The choice takes effect immediately and is saved in this browser. It is not synchronized
between devices or saved as an organization-wide choice. Clearing site storage resets it.
Appearance is not a claim of comprehensive accessibility conformance.

## Notification preferences

Notifications → Preferences manages Pop-up, Browser, Bell and Email by topic, with
immediate saving. The same component is used during setup. Preferences belong to the
current user in the current organization. Existing history is retained when a channel is
disabled. Failed saves restore the last saved choice and show an error.

Available topics are task reminders, upcoming events, ticket mentions, ticket comments,
and website form submissions. Channel and group checkboxes support bulk changes.
Browser alerts require permission, requested when the user enables that channel, and an
open CRM tab. With both Pop-up and Browser enabled, the visible CRM uses Pop-up and a
background tab uses Browser; delivery receipts suppress duplicate presentations across tabs.
Browser previews are generic. Bell/history can show record context within the user's access.

Email alerts use the configured system sender, not the user's Gmail connection.
Account recovery, invitations and guest meeting invitations are separate transactional flows.
Reminder scheduling and polling mean delivery is not guaranteed to be instantaneous.

## Connected accounts

Google sign-in, Gmail and Google Calendar are separate connections. Connecting either
integration requires the user's own Google consent. Mailbox access is personal and scoped
to the organization. Gmail supports sending and related-email synchronization; new mailbox
changes trigger background sync, with periodic recovery if push delivery is delayed.

Google Calendar creates appointments in the connected calendar. The availability dropdown
loads automatically and supports multiple calendars with removable selected labels.
Those additional calendars contribute busy time, not duplicate CRM appointments. Internal
CRM notes are not included in guest invitations. Calendar updates and attendee responses
sync in the background; instant delivery is not guaranteed.

See [connected accounts](../self-hosting/google-connected-accounts.md),
[Gmail push](../operations/gmail-push-sync.md) and the in-app knowledge base for current flows.
