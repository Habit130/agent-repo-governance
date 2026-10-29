"""Checks an API token against the SHA-256 digest kept for it. The token itself is never stored."""

import hashlib
import hmac


def digest(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def is_valid(token, stored_digest):
    """Whether token matches stored_digest, compared in constant time."""
    if not token:
        return False
    return hmac.compare_digest(digest(token), stored_digest)
