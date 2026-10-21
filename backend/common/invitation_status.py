from django.utils import timezone


def invitation_issue(invitation):
    """Return a safe terminal state without disclosing recipient or tenant data."""
    if not invitation or not invitation.org.is_active:
        return "invitation_invalid", "This invitation is unavailable."
    if invitation.revoked_at:
        return "invitation_cancelled", "This invitation was cancelled."
    if invitation.accepted_at:
        return "invitation_accepted", "This invitation has already been accepted."
    if invitation.expires_at <= timezone.now():
        return "invitation_expired", "This invitation has expired."
    return None
