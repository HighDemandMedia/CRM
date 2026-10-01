"""Organization-owned ordering for system and custom record properties."""

import hashlib
import json

from common.property_catalog import FIELDS


def property_key(row):
    return row["key"] if row.get("is_system") else "custom_fields." + row["key"]


def ordered_properties(org, target, rows):
    order = (org.property_order or {}).get(target, [])
    rank = {key: i for i, key in enumerate(order)}
    return sorted(rows, key=lambda row: rank.get(property_key(row), len(rank)))


def revision(org):
    return hashlib.sha256(
        json.dumps(org.property_order, sort_keys=True).encode()
    ).hexdigest()


def layout(org):
    from common.models import CustomFieldDefinition
    from common.property_catalog import LABELS
    from common.serializer import CustomFieldDefinitionSerializer

    definitions = CustomFieldDefinitionSerializer(
        CustomFieldDefinition.objects.filter(
            org=org, is_active=True, target_model__in=FIELDS
        ),
        many=True,
    ).data
    return {
        target: {
            "order": (org.property_order or {}).get(target, []),
            "system": [
                {
                    "key": key,
                    "label": LABELS.get(key, key.replace("_", " ").capitalize()),
                }
                for key in [*FIELDS[target], "last_activity_at"]
            ],
            "custom": [d for d in definitions if d["target_model"] == target],
        }
        for target in FIELDS
    }
