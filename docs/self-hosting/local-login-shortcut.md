# Open the local CRM (macOS)

Double-click `ABRIR-CRM.command` in the local CRM folder. It runs the versioned
`scripts/open-crm.command`, starts the local Docker services and frontend if needed, and opens
`http://localhost:5173/login` in your browser. Sign in using your own account. If a valid session
already exists, the normal application session rules apply.

Docker Desktop must be running; Node and pnpm must be available on PATH. The local wrapper
supplies the installed runtime paths on this computer. The launcher requires a local
Unix-socket Docker engine and does not target a remote deployment.

The launcher does not accept an account email, issue tokens, create login links, or bypass
password verification. Existing accounts and passwords are unchanged. For password recovery,
use the login page and open the email in Mailpit at `http://localhost:8025` (the launcher enables
the local mail override). See [First sign-in](../getting-started/first-sign-in.md).
