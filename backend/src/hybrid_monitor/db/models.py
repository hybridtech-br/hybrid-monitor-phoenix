"""ORM model registry.

Importing models here ensures SQLAlchemy metadata contains all tables
when Alembic autogeneration is executed.
"""

from hybrid_monitor.domain.identity.models import (
    AuditLog,
    Permission,
    Role,
    User,
)

__all__ = [
    "AuditLog",
    "Permission",
    "Role",
    "User",
]
