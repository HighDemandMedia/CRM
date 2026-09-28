# Private CRM account provisioning

Public account registration stays disabled on hosted deployments. Local users and
organizations are not copied by Git or by a Render deployment.

## Access levels

- **Platform owner:** an explicitly provisioned Django superuser. Can use Preview
  modules and list active organizations in the organization switcher. Switching
  selects one organization, creates a protected platform-access membership if
  needed, and logs the switch. Queries and PostgreSQL RLS still operate on that
  one organization; there is no mixed cross-tenant record feed.
- **Organization Super Admin:** the owner of one organization (`Org.owner`). Can
  administer that organization's users, roles and available CRM configuration.
  Cannot appoint a platform owner, open Preview modules, or access another
  organization's records.
- **Organization Admin / Manager / Member / custom roles:** retain their existing
  organization permissions and scopes. All customer accounts, including invited
  users, receive the released module view automatically; `is_demo` is not needed.

Preview visibility is enforced by the backend and frontend. Super Admin is not a
custom permission set. Platform ownership is not assignable through the CRM UI or
API and is never inferred from an email address or domain. Legacy organization
API keys cannot impersonate the platform owner.

## First platform owner

Deploy this revision to the API (including migration `common.0066`), worker,
scheduler, and frontend. Use the **API service's interactive Render Shell**:

```sh
python manage.py provision_crm_account --platform-owner --email correahumberto98@gmail.com --organization "High Demand Media"
```

The command prompts for the person's name, then twice for a hidden password.
Passwords must pass the same validation as registration. No password is supplied
in arguments, printed, emailed, or stored in shell history. The command refuses a
second platform owner, existing email, or existing organization name; it never
resets or promotes an existing account. Creation is atomic. There are no default
credentials. Keep `PASSWORD_REGISTRATION_ENABLED=false`.

After success, sign in at `https://crm.highdemandmedia.com/login`. The account menu
shows **Platform owner**. The existing organization selector lists active
organizations. Switching does not transfer ownership of a customer's organization.

## Independent customer organization

Run the same command **without `--platform-owner`**, with the customer's actual
email and a new organization name:

```sh
python manage.py provision_crm_account --email CUSTOMER_EMAIL --organization "CUSTOMER_ORGANIZATION"
```

Replace both placeholders before running. This creates an independent
organization and its Super Admin, with no demo records and no Preview access.
Other colleagues are invited from **Users & Teams** inside that organization;
they do not need new organizations.

## Revocation and operational checks

Platform-access memberships are separate from ordinary memberships. If the
platform owner's `is_superuser` flag is revoked privately, those memberships stop
working immediately in the API, organization directory, and token refresh. Their
ordinary membership in their own organization remains governed by its own role.
Customer administrators cannot edit, demote, deactivate or remove the platform
account. Changing the organization creator remains prohibited.

Before testers enter: verify owner login, a customer Super Admin login, unavailable
Preview routes, an attempted cross-organization access, invitation delivery, and
attachment upload/download. Automated local tests do not verify Render secrets,
real mail delivery, or S3 credentials.
