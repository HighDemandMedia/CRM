# Gmail system sender

The system sender delivers Django authentication, invitation and support mail.
It is separate from individual users' Gmail and Calendar integrations. Attachments
can remain in S3 without configuring SES. Local development keeps its existing
mail backend until explicitly changed.

## Initial authorization

Enable Gmail API in a Google Cloud project and create a Desktop OAuth client.
For an External project in Testing, add the sender as a test user. Download the
client JSON outside the repository. Run on the computer with a browser:

```sh
python3 scripts/authorize-system-gmail.py \
  --credentials /path/outside/repository/client.json \
  --output /path/outside/repository/gmail-system.env \
  --sender info@highdemandmedia.com
```

The helper opens Google's consent page using loopback, state and PKCE. It asks
for `gmail.send`, `openid` and `email`, verifies the selected email via Google's
userinfo endpoint, and saves the configuration with owner-only file permissions.
It neither reads the mailbox nor sends a test email. A Google account using a
custom email address must actually have a Gmail/Workspace mailbox to send mail.

## Render

Copy the private file's variables into an environment group linked only to the
backend and email worker. Never commit the file, tokens or downloaded client JSON.
`DEFAULT_FROM_EMAIL` must use the authorized sender. Different Reply-To addresses
are supported; alternate From addresses are rejected.

Use `EMAIL_BACKEND=common.gmail_backend.GmailEmailBackend` and the four
`GMAIL_SYSTEM_*` variables from the helper. No new Python dependency is required.
Expired/revoked authorization raises a sanitized delivery error. Ambiguous send
failures are not automatically retried by this backend, avoiding duplicate sends.
Existing task retry policies still apply.

## Before continuous use

External Google OAuth apps in Testing issue Gmail refresh tokens that expire in
seven days. Resolve the project's audience/publishing status and any applicable
Google verification requirements before relying on this for continuous service.
Reauthorize after that change. A successful authorization is not a delivery test:
explicitly test a real message and recovery/invitation flows after deployment.

References:
- https://developers.google.com/identity/protocols/oauth2/native-app
- https://developers.google.com/identity/protocols/oauth2
- https://developers.google.com/workspace/gmail/api/guides/sending
