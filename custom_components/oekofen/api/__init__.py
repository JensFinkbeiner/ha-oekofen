"""Protocol client for the local JSON interface of ÖkoFEN Pellematic boilers.

This package must not import Home Assistant, so that it can later be
extracted into a standalone PyPI library.
"""

from .client import OekofenClient
from .exceptions import (
    OekofenAuthError,
    OekofenBusyError,
    OekofenConnectionError,
    OekofenError,
    OekofenParseError,
)
from .models import FieldMeta, OekofenData, OekofenFault, Value

__all__ = [
    "FieldMeta",
    "OekofenAuthError",
    "OekofenBusyError",
    "OekofenClient",
    "OekofenConnectionError",
    "OekofenData",
    "OekofenError",
    "OekofenFault",
    "OekofenParseError",
    "Value",
]
