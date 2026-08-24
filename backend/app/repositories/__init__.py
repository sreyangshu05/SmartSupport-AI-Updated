"""Repository layer.

The domain services (``app/services``) are the primary data-access boundary in
this codebase and fully encapsulate SQLAlchemy queries behind business-logic
methods. This package provides small, focused query helpers for cross-cutting
reads (health, counts) that don't belong to a single service, avoiding a
duplicate query layer per the project's "prefer existing structure, no
unjustified duplication" rule.
"""
