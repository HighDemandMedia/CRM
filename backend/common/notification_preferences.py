"""Personal, organization-scoped delivery settings for actual CRM producers."""

CHANNELS = ("popup", "browser", "bell", "email")
TOPICS = (
    {
        "key": "task.reminder",
        "group": "Tasks",
        "label": "Task reminders",
        "description": "When a task assigned to you is due for a reminder.",
    },
    {
        "key": "calendar.reminder",
        "group": "Calendar",
        "label": "Upcoming events",
        "description": "Before an event you host or attend.",
    },
    {
        "key": "case.mentioned",
        "group": "Tickets",
        "label": "Mentions",
        "description": "When someone mentions you in a ticket.",
    },
    {
        "key": "case.commented",
        "group": "Tickets",
        "label": "Ticket comments",
        "description": "New comments on tickets you follow.",
    },
    {
        "key": "webform.submitted",
        "group": "Web forms",
        "label": "Form submissions",
        "description": "Submissions routed to you by the form's notification settings.",
    },
)
TOPIC_KEYS = frozenset(topic["key"] for topic in TOPICS)


def channels_for(profile, verb):
    # Existing preferences remain the defaults until the user saves the matrix.
    enabled = profile.notify_in_app
    if verb.endswith(".mentioned"):
        enabled = enabled and profile.notify_mentions
    if verb.endswith(".commented"):
        enabled = enabled and profile.notify_comments
    defaults = {
        "popup": enabled and verb in ("task.reminder", "calendar.reminder"),
        "browser": False,
        "bell": enabled,
        # Web forms already send internal email through their own durable outbox.
        "email": verb == "webform.submitted",
    }
    overrides = (profile.notification_preferences or {}).get(verb, {})
    return {key: overrides.get(key, value) for key, value in defaults.items()}


def preferences_payload(profile):
    return {
        "topics": TOPICS,
        "values": {key: channels_for(profile, key) for key in TOPIC_KEYS},
    }


def delivery_channels(notification, profile):
    current = channels_for(profile, notification.verb)
    original = notification.channels or {
        "bell": True,
        "popup": notification.verb in ("task.reminder", "calendar.reminder"),
    }
    return {key: bool(original.get(key) and current[key]) for key in CHANNELS}
