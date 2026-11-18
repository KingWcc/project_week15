"""Application-level exceptions with user-safe messages."""

from __future__ import annotations


class ModelResponseError(RuntimeError):
    """The model replied, but the reply could not be parsed or was empty."""
