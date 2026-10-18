# Security rules

BottleCRM is a multi-tenant application where every org's data sits in the same database, the same
tables, next to every other org's. The rules on this page exist because the two ways that goes wrong,
one tenant reading or writing another tenant's data, and a non-admin reaching admin- or
platform-level actions, are the two outcomes every change touching auth, permissions, or
serializers has to rule out before it merges.

## The trust boundary

The backend (`backend/`) is the only trust boundary in this system.
[Architecture overview](../architecture/overview.md#the-three-clients) describes why that has to be
true structurally, not just as policy: a SvelteKit web app, a Flutter mobile app, and any
third-party integration all talk to the *same* Django REST Framework API over the same JSON
endpoints. There is no separate, more-trusted internal API. A rule enforced only in the SvelteKit
UI (disabling a button, hiding a form field, client-side validation) protects none of the three
clients, because a browser DevTools console, a modified mobile build, or a plain `curl` request
reaches the same endpoint directly, skipping whatever the UI would have prevented. Every constraint
that matters has to be enforced in the DRF view or serializer, full stop.

## Identity is server-derived

Who is making a request, which org they're acting in, and what role they hold are facts the server
establishes and re-validates on every request, never values read from the request body, a query
string, or a custom header. [Authentication](../architecture/authentication.md#claims) shows the
concrete mechanism: the `org_id` claim inside a caller's signed JWT is not simply trusted, the
middleware that resolves it re-checks it against an active `Profile` row on every single request:

```python
profile = Profile.objects.select_related("org").get(
    user_id=user_id, org_id=org_id, is_active=True
)
```

If that lookup fails (the membership was revoked, the profile was deactivated) the request gets a
403 asking the caller to sign in again, rather than proceeding on a claim that's gone stale. The
practical rule for any view or serializer you write: identity comes from `request.user` and
`request.profile`, both set by middleware before your code runs (see
[Overview](../architecture/overview.md#request-lifecycle)), never from a field the client sent.
`role`, in particular, is a display convenience when it appears in a JWT payload; every real
permission check reads `request.profile.role` fresh from the database, not from the token.

## Tenant scoping

Pair every permission check with an explicit org filter. The two are independent controls, and
neither substitutes for the other. `HasOrgContext` (`backend/common/permissions.py`) is the standard
permission class on nearly every org-scoped view:

```python
class HasOrgContext(permissions.BasePermission):
    def has_permission(self, request, view):
        if not hasattr(request, "profile") or request.profile is None:
            return False
        if not hasattr(request, "org") or request.org is None:
            return False
        if not request.profile.is_active:
            return False
        return True
```

That establishes "a real, active member of this org is making this request". It does not filter
which rows the view returns. Every queryset still has to add
`Model.objects.filter(org=request.profile.org)` itself, and every `create()` / `serializer.save()`
still has to pass `org=request.profile.org` explicitly, never accept it from the request body. RLS
(PostgreSQL Row-Level Security) backs this up at the database layer, but it's a safety net for when
the filter is missing, not a substitute for writing it. See
[The two-layer contract](../architecture/multi-tenancy-and-rls.md#the-two-layer-contract) for why
both layers are required, and [Adding an org-scoped model](adding-an-org-scoped-model.md) for the
full checklist when the view is for a brand-new model.

## Server-owned fields

Any field the server is supposed to derive: `org`, `created_by`, `profile`, a publish/visibility
flag, must never be settable from `request.data`. There are two real mechanisms in this codebase
for that, not one:

**Declare the field `read_only=True` or list it in `read_only_fields`.** `TeamCreateSerializer` in
`backend/common/serializer.py` declares `read_only_fields = ("created_at", "created_by", "org")`;
`leads/serializer.py` sets `read_only_fields = ("id", "created_at", "updated_at", "org")` on
`LeadStageSerializer` and `LeadPipelineSerializer`; and `TimeEntrySerializer`
(`backend/cases/serializer.py`) declares the field itself read-only; `profile =
ProfileSerializer(read_only=True)`: for exactly the reason this section opens with: `profile` is
who logged the time entry, and it has to be a fact the server sets, not one a client requests.

**Or don't accept it through the serializer at all, and set it explicitly at the call site.**
`TimeEntryCreateSerializer`'s own docstring states this directly: "`case`, `profile`, and `org` are
injected by the view and not accepted from the client", and indeed none of the three appear in its
`Meta.fields`. The view (`backend/cases/time_views.py`) backs that up:

```python
entry = TimeEntry.objects.create(
    org=request.profile.org,
    case=case,
    profile=request.profile,
    **serializer.validated_data,
)
```

`serializer.validated_data` can only ever contain the fields the serializer declared in the first
place, so there's nothing for a client to override here even by guessing field names, the
equivalent of popping a key out of `request.data` before `save()`, but enforced by what the
serializer's `fields` tuple omits rather than by a runtime pop.

The sharpest example of *why* this matters is `is_sample`, a flag shared, via one imported
`SAMPLE_DATA_HELP_TEXT` constant, by six models: `Lead`, `Account`, `Contact`, `Case`, `Opportunity`,
and `Task` (`grep -rl SAMPLE_DATA_HELP_TEXT backend/` finds it in each app's `models.py`, plus
`common/base.py` where it's defined once). `leads/serializer.py` declares
`read_only_fields = ("is_sample",)`. The help text itself, defined once in `backend/common/base.py`
and shared by every model that has the field, states the reasoning as a security invariant rather
than documentation:

```python
SAMPLE_DATA_HELP_TEXT = (
    "True only for demo rows created by common.packs.applier._apply_sample_data. "
    "Server-set exclusively, never expose this as a writable field on any "
    "serializer. It is the sole key common.packs.applier.clear_sample_data uses "
    "to decide what to delete, so a client-writable path here would let a user "
    "mark an arbitrary real record as sample and have it deleted."
)
```

If a field like this were writable, a hostile request wouldn't need a bug in the delete logic at
all. It would just flip the flag on someone else's real record and let the legitimate "clear sample
data" action do the deleting. When you add a field the server is meant to own, ask what a client
could achieve by setting it directly, not just whether the happy path needs it to be read-only.

## Prove permission checks can fail

A permission check that always evaluates to the same answer isn't a check. It's dead code wearing
a check's shape, and this codebase has a well-documented history of exactly that happening by
accident. `Case.created_by` (like nearly every model's `created_by`) is a foreign key to `User`, not
to `Profile`. Comparing a `Profile` instance directly against it,

```python
request.profile == self.object.created_by  # always False: Profile compared to a User FK
```

Type-checks in Python and never raises, but is never `True`, which silently turned an intended
"creator or admin" check into "admin only" with no error anywhere. This isn't hypothetical in this
codebase: `git log -L` on `CaseAttachmentView.delete` in `backend/cases/views.py` shows a commit
(`c9250dd`) whose diff replaces exactly this,

```diff
-            request.profile.role == "ADMIN"
-            or request.profile.is_admin
-            or request.profile == self.object.created_by
+            is_org_admin(request.profile)
+            or request.profile.user_id == self.object.created_by_id
```

Confirming from the actual commit history, not from a comment describing it, that the
`Profile`-vs-`User` comparison was live code before it was replaced with the type-correct
`request.profile.user_id == self.object.created_by_id`.

[Permissions and roles](../architecture/permissions-and-roles.md#object-level-checks) documents this
pattern in depth, including which apps had it fixed and which, as of that page's own last check
against source, still don't; read it before writing a new `created_by` comparison, and compare
`profile.user_id` to `obj.created_by_id`, never `profile` to `obj.created_by` directly.

The only way to know a check can fail is to write a test that makes it fail. `leads/tests/
test_lead_access_and_totals.py` states the rule its own tests follow: "Every permission test asserts
both directions. A check that can only return False is indistinguishable from a check that is never
reached." In practice that means a pair of tests, not one, for example
`opportunity/tests/test_sales_goals.py`:

```python
def test_create_goal_admin(self, admin_client, org_a):
    ...
    response = admin_client.post(self.GOALS_URL, data, format="json")
    assert response.status_code == 201

def test_create_goal_non_admin_forbidden(self, user_client):
    ...
    response = user_client.post(self.GOALS_URL, data, format="json")
    assert response.status_code == 403
```

A single test asserting only the `403` case would pass identically whether the admin check works
correctly or whether it denies *everyone*, admin included, because of a mistake like the one above.
Only the paired `True` test catches that. See [Testing](testing.md) for the fast-iteration commands,
and [Adding an org-scoped model](adding-an-org-scoped-model.md#the-tests) for the same pairing
applied to tenant isolation specifically.


## Client IPs, CSV exports and browser protections

Use `common.request_meta.client_ip` for request IPs. Do not read the first
`X-Forwarded-For` entry or use DRF's default forwarded-header identity for login
throttles. `DJANGO_TRUSTED_PROXY_CIDRS` is an explicit, comma-separated list of
verified ingress proxy networks. The resolver walks the chain from the socket
peer right to left, stopping at the first untrusted address. An empty setting
uses the socket peer; invalid or oversized chains also fall back to that peer.

For managed ingress without stable published proxy CIDRs, the alternative
`DJANGO_TRUSTED_PROXY_HOPS` selects the Nth XFF entry from the right. These modes
are mutually exclusive. Fixed hops require **every public ingress route** to
append the same trusted tail, with no direct access bypassing those proxies.
Neither mode trusts the first caller-supplied XFF entry. Do not use `0.0.0.0/0`,
`::/0`, guess private networks, or enable a hop count based only on a diagram.
Unverified/empty configuration intentionally uses the peer and can group visitors.

Web sends authenticated visitor context on password login, registration,
password changes and recovery. `CRM_PROXY_SIGNING_KEY` must be the same dedicated
random 32-byte secret (64 hex characters) on Web and API. It is server-only;
never use a `PUBLIC_` variable or reuse Django/JWT/Google credentials. The HMAC
binds version, timestamp, HTTP method, path, IP and SHA-256 of the exact JSON
bytes. The API validates it before parsing, with a 60-second clock tolerance,
64 KiB body limit and an explicit authentication-path allowlist. Invalid,
incomplete or expired context is rejected. Valid context only selects an IP
bucket: it never authenticates a user or grants permissions. Replaying identical
signed bytes within the short window still consumes the same throttle bucket.

Web takes the IP exclusively from adapter-node `getClientAddress()`. Configure
`ADDRESS_HEADER=X-Forwarded-For` and `XFF_DEPTH` only after validating the actual
public/custom-domain proxy chain; never forward browser IP headers directly.
A configured signing key with an unavailable/invalid adapter address fails
closed. Without a key, local development keeps its unsigned behavior. The API
continues to support direct clients via its verified ingress configuration.
Retain per-account login and per-form global limits with the shared Redis cache.

### Render activation gate (2026-10-16)

Read-only runtime inspection confirmed that Web uses the private API origin.
Controlled empty login requests against the public API demonstrated an XFF tail
of `[actual caller, edge proxy]`, including when the caller supplied a forged
prefix. Therefore `DJANGO_TRUSTED_PROXY_HOPS=2` is the observed API candidate;
it is **not evidence that Web's custom-domain path has the same depth**.

Before committing to production activation:

1. Temporarily set `CRM_PROXY_DIAGNOSTIC_ID` on Web to an operator-chosen
   alphanumeric/hyphen identifier (16-80 characters). Deploy Web with signing
   still disabled, then send `HEAD /login` with `X-CRM-Proxy-Probe` matching it.
   Only this matching request logs bounded IP metadata as `crm.proxy_probe`;
   it never returns diagnostics, credentials or cookies to the caller. Remove
   the variable after verification. Verify Web's actual XFF tail on both `crm.highdemandmedia.com` and its enabled
   Render hostname, including a forged prefix. Verify API custom domains too if
   any are added. If depths differ, normalize ingress first; do not guess.
2. Set the shared signing key on API first and deploy the API verifier. Keep Web
   signing disabled until the verifier is live. No database migration is needed.
3. Configure the verified API hop count (leave CIDRs empty), then Web's verified
   `ADDRESS_HEADER`/`XFF_DEPTH` and the same signing key; deploy Web. Keep clocks
   synchronized. Never print the signing key in shell output or logs.
4. Send controlled empty login requests through Web and directly to API. Check
   the selected throttle identities in restricted server diagnostics, without
   exposing raw headers publicly. Forged prefixes must not change the identity;
   distinct source IPs must remain distinct. Do not exhaust a customer's quota.
5. Confirm normal sign-in, recovery and invitation registration. Roll back Web
   signing first if necessary, then the API verifier/key. Restore proxy settings
   together with their code. Never roll back to trusting the leftmost XFF entry.

The code and automated tests do not constitute live verification of Web's proxy
chain. Do not mark the production gate complete until step 4 passes.

CSV quoting is not formula protection. Pass untrusted cell values through
`common.csv_utils.csv_safe` before `csv.writer`; it also handles whitespace and
BOM-prefixed formulas. Keep the existing browser-side CSV protection for client
exports.

SvelteKit generates CSP nonces/hashes for its own scripts. The CRM permits
same-origin scripts, blocks plugins, restricts base URLs and rejects embedding
via `frame-ancestors 'none'` and `X-Frame-Options: DENY`. These frontend rules do
not change the public form embed endpoint served by Django. Inline dynamic
styles and integration images remain supported; do not weaken script policy to
fix a styling issue. Verify the compiled login, navigation, email composer and
public form preview when changing CSP.

The development Compose ports bind to `127.0.0.1`. Editing Compose does not
change existing containers: activating these bindings requires their recreation.
Inventory the actual Compose project/overrides first and preserve database
volumes and Redis queued work. Do not use `down -v`, prune, or restart the
separate laboratory stack. These development settings do not configure Render.
