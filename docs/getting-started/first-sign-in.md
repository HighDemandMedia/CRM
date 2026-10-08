# First sign-in

High Demand Media CRM uses the same authentication flow locally and online. Open `/login`,
choose **Sign in**, and enter your own email and password. There is no development login
button or command that generates a session for another user.

## Accounts and invitations

Access is invitation-only. The platform owner creates an organization and invites its
administrator. That administrator can invite their team. New users accept the invitation,
choose a password, and complete their profile. The first administrator also completes the
organization setup. Existing users sign in before accepting an invitation.

For the first platform owner on a new installation, use the interactive
`provision_crm_account` command documented in [Private account provisioning](../self-hosting/account-provisioning.md).
It asks for a password privately and does not generate a browser login session.

## Local development

The [local launcher](../self-hosting/local-login-shortcut.md) starts the services and opens
the normal login page. It does not create an account, mint tokens, or choose a user.
Existing local accounts retain their passwords. Demo data no longer gives new accounts a
shared default password. Prefer using your existing account when seeding demo data.

If you do not know your password, use the recovery option on the login page. With the
`docker-compose.mail.yml` override enabled, recovery and invitation emails are captured by
Mailpit at `http://localhost:8025`. Follow the recovery link to set a password. This uses the
same verification and expiration checks as online recovery.

## Google OAuth

Available when Google sign-in is configured. It authenticates existing active users with
verified Google email addresses; it does not provision a new account.

## Magic links

Email recovery sends a short-lived, single-use link to an existing account. Verification
permits a password change within the recovery window. It does not create a new account.

See [Password access and invitations](../access/password-login.md) for recovery and invitation
behavior, and [Authentication API](../api/authentication.md) for API contracts.

## Choosing an organization

One active organization is selected automatically. Users with several active memberships can
choose one at `/org`. The server verifies membership when switching organizations; typing an
organization ID never grants access. Pending profile and organization setup is completed before
entering the workspace.

The frontend stores authentication in HttpOnly cookies. Access tokens last one hour; refresh
tokens last 14 days and rotate when used. Closing a tab or browser does not end a valid persistent
session. Use **Sign out** to end it; private browsing and cleared cookies remove local access.
See [Personal preferences and sessions](../settings/personal-preferences-and-uploads.md).
