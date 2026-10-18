"""One validated client IP definition for throttles, submissions and audit logs."""

from ipaddress import ip_address, ip_network

from django.conf import settings

REFERER_MAX_LENGTH = 512


def _address(value):
    try:
        # Scope IDs are interface-local, not valid public client identities.
        if "%" in value:
            return None
        address = ip_address(value.strip())
        # Normalize IPv4-mapped IPv6 so it cannot create a second throttle bucket.
        return getattr(address, "ipv4_mapped", None) or address
    except (ValueError, AttributeError, TypeError):
        return None


def client_ip(request):
    """Prefer authenticated Web context, then explicitly configured ingress.

    CIDRs walk right-to-left through trusted peers; fixed hops select the
    verified managed-ingress tail. With neither configured, use the socket peer.
    Malformed trusted addresses fall back to that peer, never an untrusted prefix.
    """
    verified = getattr(request, "_verified_client_ip", None)
    if verified is not None:
        return verified
    peer = _address(request.META.get("REMOTE_ADDR", ""))
    if peer is None:
        return None
    networks = [ip_network(cidr) for cidr in settings.TRUSTED_PROXY_CIDRS]

    def trusted(address):
        return any(address in network for network in networks)

    hops = settings.TRUSTED_PROXY_HOPS
    if not hops and not trusted(peer):
        return str(peer)
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if not forwarded or len(forwarded) > 2048:
        return str(peer)
    values = forwarded.split(",")
    if hops:
        # Validate only the trusted tail. A caller controls the prefix and must
        # not force valid requests into the shared proxy bucket with junk there.
        if len(values) < hops:
            return str(peer)
        tail = [_address(value) for value in values[-hops:]]
        return str(tail[0]) if all(tail) else str(peer)
    chain = [_address(value) for value in values]
    if len(chain) > 32 or any(address is None for address in chain):
        return str(peer)
    current = peer
    for address in reversed(chain):
        if not trusted(current):
            break
        current = address
    return str(current)


def referer(request):
    """Store a bounded Referer string; it is informational, never trusted."""
    return request.META.get("HTTP_REFERER", "")[:REFERER_MAX_LENGTH]
