"""
Falcon AI

Forward Layer

Append-only log of published risk sheets and their realised outcomes (F-008).
"""

from .store import ForwardError, ForwardStore, resolve_outcome

__all__ = ["ForwardError", "ForwardStore", "resolve_outcome"]
