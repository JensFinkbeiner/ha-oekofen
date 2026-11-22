"""Exceptions of the ÖkoFEN protocol client.

Messages never contain the password or the request URL (the password is part
of the URL path), so they are safe to log.
"""

from __future__ import annotations


class OekofenError(Exception):
    """Base class for all errors of the client."""


class OekofenConnectionError(OekofenError):
    """The boiler could not be reached or did not answer in time."""


class OekofenBusyError(OekofenConnectionError):
    """The boiler rejected the request because of its rate limit (2.5 s)."""


class OekofenAuthError(OekofenError):
    """The boiler answered with its help page instead of data (wrong password)."""


class OekofenParseError(OekofenError):
    """The answer could not be decoded or parsed."""
