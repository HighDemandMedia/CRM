# Google sign-in

Google is the primary option on `/login` when configured. **Sign in with email** opens the existing password form; recovery remains available. Without Google configuration, the password form remains accessible.

## Account access

- This is sign-in, not public registration. A new user opens their invitation, explicitly accepts the current terms, and chooses Google or a CRM password. Google enrollment requires the verified Google email to match the invitation. It creates an unusable local password, consumes the invitation atomically, preserves its role, and starts profile setup (plus organization setup for an owner). Existing users can sign in with the same email as their CRM account.
- Disabled users cannot sign in. Google does not grant organization membership, roles or platform-owner access. Organization selection continues to use active assigned memberships and the existing platform-owner policy.
- Google must verify the address. Gmail addresses and Google Workspace identities with an `hd` claim can authenticate. A Google account using another provider's email without `hd` must use its CRM password, because Google may no longer be authoritative for that mailbox.
- This flow only requests `openid email profile`. Connecting Gmail or Calendar is a separate opt-in action in Profile → Integrations.

## Configuration

Use an OAuth client of type **Web application** in Google Cloud:

| Service | Variable | Value |
| --- | --- | --- |
| Web | `GOOGLE_CLIENT_ID` | Web OAuth client ID |
| Web | `GOOGLE_LOGIN_DOMAIN` | `https://crm.highdemandmedia.com` |
| API | `GOOGLE_CLIENT_ID` | The same client ID |
| API | `GOOGLE_CLIENT_SECRET` | The corresponding secret, server only |

Authorize the exact redirect URI `https://crm.highdemandmedia.com/login` in that client. Local testing requires its own authorized redirect URI matching the local frontend origin plus `/login`. Never commit credentials. The `GOOGLE_INTEGRATION_*` settings for Gmail/Calendar are separate and do not enable sign-in automatically.

For this release deploy **API before Web**: the API now accepts the signed visitor context on `/api/auth/google/callback/`. It uses the existing `CRM_PROXY_SIGNING_KEY` shared by Web and API; no new signing key is required. No schema migration is introduced by Google sign-in.

## Session and failure handling

- Starting Google sign-in is a same-origin POST. Invitation enrollment stores the invitation and explicit agreement choices in a short-lived HttpOnly cookie bound to that OAuth state; the callback revalidates the invitation, organization lifecycle and legal version before any account or membership is created. It creates a random state and PKCE verifier in HttpOnly, SameSite=Lax cookies valid for ten minutes, Secure in production. Merely opening or reloading login does not replace a pending flow.
- The callback consumes those cookies once, checks state, and sends the code/verifier to the API with signed visitor identity. The API exchanges the code and validates the Google ID token's signature, issuer, audience and expiry with the installed Google authentication library.
- Login shares the password-login IP attempt limit. No mailbox permissions or offline Google refresh token are requested.
- Remember me is unchecked initially: the CRM session is limited to eight hours with session cookies. Explicitly checking it uses the existing 14-day persistent-session policy, for Google or password sign-in.
- Cancellation or an invalid/expired callback returns to login with a short translated message, another Google attempt and the email alternative. Provider error details and authorization codes are not displayed or logged.

## Verification

Automated tests cover PKCE/state, replay, signed visitor identity, failed verification, unknown/disabled users, password fallback for third-party addresses, remember choices, and existing tenant permissions. A real Google authorization still needs verification against the configured client and redirect URI before claiming the deployment is ready.

References: [Google server OAuth flow](https://developers.google.com/identity/protocols/oauth2/web-server), [ID token validation and mailbox authority](https://developers.google.com/identity/sign-in/web/backend-auth), [Google button guidance](https://developers.google.com/identity/branding-guidelines).

## Independent integrations

Gmail and Calendar now support their own Cloud projects without changing the
sign-in credentials described here. See the [independent connection rollout](../operations/google-independent-connections-2026-10-28.md)
before enabling service-specific credentials. Never reuse a sign-in project for
a connection that should be independently revocable.
