"""Idempotent bootstrap data for the Micael Monitor Identity domain."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hybrid_monitor.core.security import hash_password
from hybrid_monitor.domain.identity.models import Permission, Role, User
from hybrid_monitor.domain.identity.services.authentication import AuthenticationService

DEFAULT_PERMISSIONS: dict[str, str] = {
    "system.admin": "Full platform administration",
    "users.read": "View users",
    "users.write": "Create and update users",
    "roles.read": "View roles and permissions",
    "roles.write": "Create and update roles and permissions",
    "cameras.read": "View cameras and live status",
    "cameras.write": "Register and configure cameras",
    "events.read": "View monitoring events",
    "events.export": "Export event evidence",
    "vision.manage": "Manage computer-vision capabilities",
    "settings.manage": "Manage platform settings",
}

DEFAULT_ROLES: dict[str, tuple[str, ...]] = {
    "Administrator": tuple(DEFAULT_PERMISSIONS),
    "Supervisor": (
        "users.read",
        "roles.read",
        "cameras.read",
        "cameras.write",
        "events.read",
        "events.export",
        "vision.manage",
    ),
    "Operator": (
        "cameras.read",
        "events.read",
        "events.export",
    ),
    "Viewer": (
        "cameras.read",
        "events.read",
    ),
    "Auditor": (
        "users.read",
        "roles.read",
        "cameras.read",
        "events.read",
        "events.export",
    ),
}


@dataclass(frozen=True, slots=True)
class BootstrapResult:
    """Summary of changes applied by an Identity bootstrap run."""

    permissions_created: int
    roles_created: int
    administrator_created: bool
    administrator_role_assigned: bool


async def bootstrap_identity(
    session: AsyncSession,
    *,
    administrator_email: str,
    administrator_name: str,
    administrator_password: str,
) -> BootstrapResult:
    """Create default permissions, roles, and the first administrator idempotently."""
    email = AuthenticationService.normalize_email(administrator_email)
    if "@" not in email:
        raise ValueError("Administrator email is invalid")
    if not administrator_name.strip():
        raise ValueError("Administrator name must not be empty")
    if len(administrator_password) < 12:
        raise ValueError("Administrator password must contain at least 12 characters")

    permission_result = await session.execute(select(Permission))
    permissions = {permission.code: permission for permission in permission_result.scalars()}
    permissions_created = 0
    for code, description in DEFAULT_PERMISSIONS.items():
        if code not in permissions:
            permission = Permission(code=code, description=description)
            session.add(permission)
            permissions[code] = permission
            permissions_created += 1

    await session.flush()

    role_result = await session.execute(select(Role).options(selectinload(Role.permissions)))
    roles = {role.name: role for role in role_result.scalars()}
    roles_created = 0
    for name, permission_codes in DEFAULT_ROLES.items():
        role = roles.get(name)
        if role is None:
            role = Role(name=name, description=f"Default {name} role")
            session.add(role)
            roles[name] = role
            roles_created += 1
        role.permissions = [permissions[code] for code in permission_codes]

    await session.flush()

    user_result = await session.execute(
        select(User)
        .where(User.email == email)
        .options(selectinload(User.roles))
    )
    administrator = user_result.scalar_one_or_none()
    administrator_created = administrator is None
    if administrator is None:
        administrator = User(
            name=administrator_name.strip(),
            email=email,
            password_hash=hash_password(administrator_password),
            is_active=True,
        )
        session.add(administrator)

    administrator_role = roles["Administrator"]
    role_assigned = administrator_role not in administrator.roles
    if role_assigned:
        administrator.roles.append(administrator_role)

    await session.flush()
    return BootstrapResult(
        permissions_created=permissions_created,
        roles_created=roles_created,
        administrator_created=administrator_created,
        administrator_role_assigned=role_assigned,
    )
