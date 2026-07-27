"""Create default Identity data and the first Micael Monitor administrator."""

import asyncio
import json
import os

from hybrid_monitor.core.session import session_scope
from hybrid_monitor.domain.identity.bootstrap import BootstrapResult, bootstrap_identity


def _required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not configured")
    return value


async def run() -> BootstrapResult:
    """Run the idempotent Identity bootstrap within a managed transaction."""
    result: BootstrapResult | None = None
    async for session in session_scope():
        result = await bootstrap_identity(
            session,
            administrator_email=_required_environment("PHOENIX_BOOTSTRAP_ADMIN_EMAIL"),
            administrator_name=_required_environment("PHOENIX_BOOTSTRAP_ADMIN_NAME"),
            administrator_password=_required_environment("PHOENIX_BOOTSTRAP_ADMIN_PASSWORD"),
        )

    if result is None:
        raise RuntimeError("Identity bootstrap did not obtain a database session")
    return result


async def main() -> None:
    """Execute the bootstrap and emit a machine-readable, non-secret summary."""
    result = await run()
    print(
        json.dumps(
            {
                "permissions_created": result.permissions_created,
                "roles_created": result.roles_created,
                "administrator_created": result.administrator_created,
                "administrator_role_assigned": result.administrator_role_assigned,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
