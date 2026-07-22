"""Identity ORM relationship helpers."""

from sqlalchemy.orm import relationship

from hybrid_monitor.domain.identity.models.association import (
    role_permissions,
    user_roles,
)


# Relationship declarations are kept centralized during the first domain phase.
# Concrete model attributes will import these definitions as the domain grows.

__all__ = [
    "relationship",
    "user_roles",
    "role_permissions",
]
