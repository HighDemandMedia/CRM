"""Bounded, create-only CSV imports using the ordinary record creation contracts.

Preview never saves. Commit revalidates and delegates writes to the existing create
handlers so associations, audit signals and on-commit notifications stay consistent.
"""

import csv
import hashlib
import io
import json
import uuid
from copy import copy

from django.core import signing
from django.db import transaction
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request

from common.creation_forms import configuration, validate_creation
from common.custom_fields import validate_payload
from common.models import CSVImportReceipt, Org, Profile, Tags
from common.permissions import is_org_admin
from common.pipeline_settings import stage_field, stages_for
from common.property_catalog import target_model
from common.rbac import check_request
from common.usage_limits import resource_count
from common.work_item_creation import prepare_creation

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 1000
COMMIT_BATCH_SIZE = 100
REPORT_COLUMNS = {"__import_row", "__import_errors"}
TOKEN_SALT = "crm.csv-import.v2"
TARGETS = {
    "contacts": ("Contact", "contacts"),
    "companies": ("Account", "accounts"),
    "deals": ("Opportunity", "opportunities"),
    "tasks": ("Task", "tasks"),
    "tickets": ("Case", "cases"),
}


def contract(module):
    from accounts.serializer import AccountCreateSerializer
    from accounts.views import AccountsListView
    from cases.serializer import CaseCreateSerializer
    from cases.views import CaseListView
    from contacts.serializer import CreateContactSerializer
    from contacts.views import ContactsListView
    from opportunity.serializer import OpportunityCreateSerializer
    from opportunity.views.opportunity_views import OpportunityListView
    from tasks.serializer import TaskCreateSerializer
    from tasks.views.task_views import TaskListView

    return {
        "contacts": (CreateContactSerializer, ContactsListView),
        "companies": (AccountCreateSerializer, AccountsListView),
        "deals": (OpportunityCreateSerializer, OpportunityListView),
        "tasks": (TaskCreateSerializer, TaskListView),
        "tickets": (CaseCreateSerializer, CaseListView),
    }[module]


def authorize(request, module):
    from rest_framework.exceptions import PermissionDenied

    if module not in TARGETS:
        raise ValidationError("Choose a supported object.")
    if not is_org_admin(request.profile):
        raise PermissionDenied("Only organization administrators can import records.")
    if request.profile.org.closing_at:
        raise PermissionDenied("This organization is read-only.")


def schema(request, module):
    authorize(request, module)
    target, _ = TARGETS[module]
    config = configuration(request.profile.org, target)
    ordered = config["selected"] + [
        f
        for f in config["fields"]
        if f["key"] not in {r["key"] for r in config["selected"]}
    ]
    fields = []
    for field in ordered:
        if field["key"] == "associations":
            # Either company or contacts satisfies the creation-form requirement.
            fields.extend(
                [
                    {
                        "key": "account",
                        "label": "Company",
                        "relation": "Account",
                        "field_type": "relationship",
                        "required": False,
                        "options": [],
                    },
                    {
                        "key": "contacts",
                        "label": "Contacts",
                        "relation": "Contact",
                        "multiple": True,
                        "field_type": "relationship",
                        "required": False,
                        "options": [],
                    },
                ]
            )
        else:
            fields.append({**field, "required": field.get("required", False)})
    for field in fields:
        if field["key"] == stage_field(target):
            field["options"] = [
                {"value": s["key"], "label": s["label"]}
                for s in stages_for(request.profile.org, target)
            ]
    return {
        "fields": fields,
        "revision": config["revision"],
        "max_rows": MAX_ROWS,
        "max_bytes": MAX_BYTES,
    }


def read_upload(request):
    upload = request.FILES.get("file")
    if not upload or not upload.name.lower().endswith(".csv"):
        raise ValidationError("Choose a .csv file.")
    content = upload.read(MAX_BYTES + 1)
    if len(content) > MAX_BYTES:
        raise ValidationError("The CSV must be 2 MB or smaller.")
    return content


def parse(content, fields):
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValidationError("Save the CSV using UTF-8 encoding.") from exc
    if "\x00" in text:
        raise ValidationError("The file contains invalid characters.")
    try:
        # Excel commonly exports semicolon-separated files in Spanish locales.
        dialect = (
            csv.Sniffer().sniff(text[:8192], delimiters=",;")
            if ";" in text.split("\n", 1)[0]
            else csv.excel
        )
        reader = csv.reader(io.StringIO(text, newline=""), dialect=dialect, strict=True)
        headers = [s.strip() for s in next(reader)]
        allowed = {f["key"] for f in fields} | REPORT_COLUMNS
        if (
            not headers
            or len(headers) != len(set(headers))
            or any(h not in allowed for h in headers)
        ):
            raise ValidationError(
                "Use unique column names from the template; remove unknown or empty columns."
            )
        rows = []
        for values in reader:
            if not any(v.strip() for v in values):
                continue
            if len(values) != len(headers):
                raise ValidationError(
                    f"CSV line {reader.line_num}: the number of cells does not match the header."
                )
            rows.append(
                (
                    reader.line_num,
                    {k: v for k, v in zip(headers, values) if k not in REPORT_COLUMNS},
                )
            )
            if len(rows) > MAX_ROWS:
                raise ValidationError(f"Import up to {MAX_ROWS} records at a time.")
        if not rows:
            raise ValidationError("Add at least one record below the header.")
        return rows
    except (csv.Error, StopIteration) as exc:
        raise ValidationError(
            "Could not read this CSV. Download a new template."
        ) from exc


def row_request(request, module, payload):
    # A fresh DRF request isolates each row. It retains the authenticated actor
    # and tenant; normal action/assignment checks run against the create route.
    raw = copy(request._request)
    raw.path = raw.path_info = f"/api/{TARGETS[module][1]}/"
    raw.method = "POST"
    row = Request(raw)
    row.user = request.user
    row._full_data = payload
    row._files = {}
    check_request(row)
    if module in {"tasks", "tickets"}:
        row._full_data = prepare_creation(row)
    return row


def relation_value(request, field, text):
    model_name = field["relation"]
    model = (
        Profile
        if model_name == "Profile"
        else Tags
        if model_name == "Tags"
        else target_model(model_name)
    )
    if model is None:
        raise ValidationError(
            {field["key"]: "This association is not supported by CSV."}
        )
    lookup = (
        "user__email"
        if model_name == "Profile"
        else "email"
        if model_name == "Contact"
        else "name"
    )
    qs = model.objects.filter(org=request.profile.org)
    if model_name in {"Profile", "Tags"}:
        qs = qs.filter(is_active=True)
    values = [v.strip() for v in text.split(";") if v.strip()]
    if not field.get("multiple") and len(values) != 1:
        raise ValidationError({field["key"]: "Choose one existing record."})
    ids = []
    for value in values:
        matches = list(
            qs.filter(**{f"{lookup}__iexact": value}).values_list("pk", flat=True)[:2]
        )
        if len(matches) != 1:
            raise ValidationError(
                {
                    field[
                        "key"
                    ]: "No unique matching record in this organization. Use an existing name or email."
                }
            )
        ids.append(str(matches[0]))
    return ids if field.get("multiple") or field["key"] == "assigned_to" else ids[0]


def payload_for(request, values, fields):
    payload = {}
    for field in fields:
        key = field["key"]
        text = values.get(key, "").strip()
        if not text:
            continue
        value = text
        if field.get("relation"):
            value = relation_value(request, field, text)
        elif field["field_type"] == "checkbox":
            if text.lower() not in {"true", "false", "1", "0", "yes", "no"}:
                raise ValidationError({key: "Use true or false."})
            value = text.lower() in {"true", "1", "yes"}
        elif field["field_type"] == "multi_select":
            value = [v.strip() for v in text.split(";") if v.strip()]
        elif field["field_type"] == "list":
            try:
                value = json.loads(text)
            except ValueError as exc:
                raise ValidationError({key: "Use a JSON list."}) from exc
        if key.startswith("custom_fields."):
            payload.setdefault("custom_fields", {})[
                key.removeprefix("custom_fields.")
            ] = value
        else:
            payload[key] = value
    return payload


def flatten_errors(detail, prefix=""):
    if isinstance(detail, dict):
        return [
            item
            for key, value in detail.items()
            for item in flatten_errors(value, f"{prefix}.{key}".strip("."))
        ]
    if isinstance(detail, list):
        return [item for value in detail for item in flatten_errors(value, prefix)]
    return [{"field": prefix or "record", "message": str(detail)}]


def validate_rows(request, module, content, selected_rows=None):
    meta = schema(request, module)
    rows = parse(content, meta["fields"])
    if selected_rows is not None:
        rows = [(n, values) for n, values in rows if n in selected_rows]
    target = TARGETS[module][0]
    serializer_class, _ = contract(module)
    valid, errors, seen = [], [], set()
    for number, values in rows:
        try:
            payload = payload_for(request, values, meta["fields"])
            if module == "deals":
                payload["currency"] = request.profile.org.default_currency
            if module == "companies" and "tags" in payload:
                payload["tag_ids"] = payload.pop("tags")
            row = row_request(request, module, payload)
            validate_creation(request.profile.org, target, row.data)
            serializer = serializer_class(data=row.data, request_obj=row)
            serializer.is_valid(raise_exception=True)
            _, custom_errors = validate_payload(
                target, row.data.get("custom_fields", {}), request.profile.org
            )
            if custom_errors:
                raise ValidationError({"custom_fields": custom_errors})
            from common.record_identity import record_identity_keys

            identities = set(
                record_identity_keys(module, serializer.validated_data).items()
            )
            repeated = identities & seen
            if repeated:
                raise ValidationError(
                    {
                        field: "This value is repeated in the CSV."
                        for field, _ in sorted(repeated)
                    }
                )
            seen.update(identities)
            valid.append((number, row.data))
        except ValidationError as exc:
            errors.extend({"row": number, **e} for e in flatten_errors(exc.detail))
    maximum = request.profile.org.usage_limits.get(module)
    if (
        maximum is not None
        and resource_count(request.profile.org_id, module) + len(valid) > maximum
    ):
        errors.append(
            {
                "row": 0,
                "field": "limit",
                "message": "This import exceeds the organization's record limit.",
            }
        )
    return meta, rows, valid, errors


def preview(request, module, content):
    meta, rows, valid, errors = validate_rows(request, module, content)
    token = None
    if valid and not any(error["row"] == 0 for error in errors):
        token = signing.dumps(
            {
                "org": str(request.profile.org_id),
                "actor": str(request.user.pk),
                "module": module,
                "digest": hashlib.sha256(content).hexdigest(),
                "nonce": str(uuid.uuid4()),
                "revision": meta["revision"],
                "rows": [number for number, _ in valid],
                "total": len(rows),
            },
            salt=TOKEN_SALT,
            compress=True,
        )
    by_row = {}
    for error in errors:
        if error["row"]:
            by_row.setdefault(error["row"], []).append(error)
    return {
        "total": len(rows),
        "valid": len(valid),
        "errors": errors,
        "invalid": len(rows) - len(valid),
        "invalid_records": [
            {"row": number, "values": values, "errors": by_row[number]}
            for number, values in rows
            if number in by_row
        ],
        "token": token,
    }


def commit(request, module, content, token, start=0):
    authorize(request, module)
    try:
        proof = signing.loads(token, salt=TOKEN_SALT, max_age=1800)
    except (signing.BadSignature, TypeError) as exc:
        raise ValidationError("Preview this file again before importing.") from exc
    expected = {
        "org": str(request.profile.org_id),
        "actor": str(request.user.pk),
        "module": module,
        "digest": hashlib.sha256(content).hexdigest(),
    }
    if any(proof.get(k) != v for k, v in expected.items()):
        raise ValidationError("The file or account changed. Preview again.")
    try:
        start = int(start)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Invalid import progress. Preview again.") from exc
    approved_rows = proof["rows"]
    total = len(approved_rows)
    if start < 0 or start > total:
        raise ValidationError("Invalid import progress. Preview again.")

    def progress(created, repeated=False):
        return {
            "created": created,
            "total": total,
            "skipped": proof["total"] - total,
            "complete": created == total,
            "already_imported": repeated,
        }

    with transaction.atomic():
        org = Org.objects.select_for_update().get(pk=request.profile.org_id)
        request.profile.org = org
        receipt = CSVImportReceipt.objects.filter(org=org, id=proof["nonce"]).first()
        completed = receipt.created_count if receipt else 0
        # A repeated request returns durable progress, including after a lost response.
        if start < completed or completed == total:
            return progress(completed, True)
        if start != completed:
            raise ValidationError("Invalid import progress. Retry the previous batch.")
        if proof["revision"] != schema(request, module)["revision"]:
            raise ValidationError(
                "The creation form changed. Download the updated template and preview again."
            )
        batch_rows = set(approved_rows[start : start + COMMIT_BATCH_SIZE])
        _, _, valid, errors = validate_rows(request, module, content, batch_rows)
        maximum = org.usage_limits.get(module)
        if (
            maximum is not None
            and resource_count(org.pk, module) + total - completed > maximum
        ):
            errors.append(
                {
                    "row": 0,
                    "field": "limit",
                    "message": "This import exceeds the organization's record limit.",
                }
            )
        if errors:
            raise ValidationError({"errors": errors})
        _, view_class = contract(module)
        for number, payload in valid:
            row = row_request(request, module, payload)
            view = view_class()
            view.request = row
            view.args, view.kwargs = (), {}
            try:
                result = view.post(row)
            except ValidationError as exc:
                raise ValidationError(
                    {
                        "errors": [
                            {"row": number, **e} for e in flatten_errors(exc.detail)
                        ]
                    }
                ) from exc
            if result.status_code >= 400:
                raise ValidationError(
                    {
                        "errors": [
                            {"row": number, **e}
                            for e in flatten_errors(
                                result.data.get("errors", result.data)
                            )
                        ]
                    }
                )
        completed += len(valid)
        if receipt:
            receipt.created_count = completed
            receipt.save(update_fields=["created_count"])
        else:
            CSVImportReceipt.objects.create(
                id=proof["nonce"], org=org, created_count=completed
            )
        return progress(completed)
