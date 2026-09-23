# Local customer demo

Open `../ABRIR-DEMO.command` from the CRM workspace to sign in as **demo@example.com** (Customer Demo). The launcher creates a short-lived local sign-in link; there is no shared password. Return to your administrator with `../ABRIR-CRM.command`.

The **High Demand Media · Demo** organization contains fictional companies, contacts, deals, tickets, tasks, appointments and notes. It is separate from CRM Prueba A and B. The demo user is an Admin of this organization: it can manage records, properties, pipelines, users, teams and permissions. It has no membership in CRM Prueba A or B and no platform superuser access. The existing organization owner remains Super Admin.

Modules marked Review are hidden in the navigation menus and search. Direct navigation to those pages returns to Today. This visibility is specific to the demo membership; administrator navigation is unchanged. The demo cannot create additional organizations.

Provision a fresh local installation with:

```sh
docker compose exec -T backend python manage.py migrate
docker compose exec -T backend python manage.py setup_customer_demo --owner-email admin@example.com
```

Setup only runs in DEBUG mode and is repeatable: existing demo edits are preserved. The owner receives administrator access to the demo organization. Only the demo identity gets the restricted presentation.

This is a local demonstration, not a public deployment. The launcher requires the local Docker services and frontend. Do not share its temporary login URL as a permanent customer URL.
