"""DORMANT FastAPI backend (ADR-0057). Present but inactive: most products are static deterministic-replay and
never run this. Activate only on an ADR-0002 trigger. A thin read-only layer over data/derived, never a
re-implementation of the engine."""

from .config import VERSION as __version__  # VERSION is the single source (T4)

__all__ = ["__version__"]
