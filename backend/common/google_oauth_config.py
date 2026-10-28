"""Select OAuth credentials without silently moving existing grants between clients."""

from dataclasses import dataclass, field

from django.conf import settings

PREFIXES = {
    "legacy": "GOOGLE_INTEGRATION",
    "gmail": "GOOGLE_GMAIL",
    "calendar": "GOOGLE_CALENDAR",
    "login": "GOOGLE",
    "sender": "GMAIL_SYSTEM",
}


@dataclass(frozen=True)
class OAuthClient:
    client_id: str
    secret: str = field(repr=False)
    project_id: str

    @property
    def configured(self):
        return bool(self.client_id and self.secret)

    @property
    def declared(self):
        return bool(self.client_id or self.secret or self.project_id)


def client_config(key, config=settings):
    prefix = PREFIXES[key]
    return OAuthClient(
        *(
            str(getattr(config, f"{prefix}_{suffix}", "")).strip()
            for suffix in ("CLIENT_ID", "CLIENT_SECRET", "PROJECT_ID")
        )
    )


def isolation_errors(service, config=settings):
    """Project IDs must come from Cloud Console; different client IDs alone do not isolate."""
    client = client_config(service, config)
    if not client.declared:
        return []
    errors = []
    prefix = PREFIXES[service]
    if not client.configured or not client.project_id:
        errors.append(
            f"Set {prefix}_CLIENT_ID, {prefix}_CLIENT_SECRET and {prefix}_PROJECT_ID together."
        )
    for other_key, other_prefix in PREFIXES.items():
        if other_key == service:
            continue
        other = client_config(other_key, config)
        if not other.declared:
            continue
        if not other.project_id:
            errors.append(
                f"Set {other_prefix}_PROJECT_ID before enabling independent Google connections."
            )
        elif client.project_id == other.project_id:
            errors.append(
                f"{prefix} must use a different Google Cloud project from {other_prefix}."
            )
        if client.client_id and client.client_id == other.client_id:
            errors.append(f"{prefix} must use its own OAuth client.")
    return errors


def authorization_client(service):
    dedicated = client_config(service)
    if dedicated.declared:
        if isolation_errors(service):
            return None
        return dedicated
    legacy = client_config("legacy")
    return legacy if legacy.configured else None


def stored_client(client_id):
    # Blank provenance belongs to the pre-migration shared client, never to a new one.
    if not client_id:
        legacy = client_config("legacy")
        return legacy if legacy.configured else None
    for key in ("legacy", "gmail", "calendar"):
        client = client_config(key)
        if client.configured and client.client_id == client_id:
            return client
    return None


def independent_disconnect(connection):
    dedicated = client_config(connection.service)
    return bool(
        connection.oauth_client_id
        and connection.oauth_project_id
        and dedicated.configured
        and dedicated.client_id == connection.oauth_client_id
        and dedicated.project_id == connection.oauth_project_id
        and not isolation_errors(connection.service)
    )


def grant_project(connection):
    if connection.oauth_project_id:
        return connection.oauth_project_id
    # The old project can be declared during rollout without rewriting token rows.
    legacy = client_config("legacy")
    if not connection.oauth_client_id or connection.oauth_client_id == legacy.client_id:
        return legacy.project_id or "legacy"
    return f"unknown:{connection.oauth_client_id}"
