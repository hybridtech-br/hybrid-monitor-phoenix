"""Identity ORM metadata regression tests."""

from hybrid_monitor.db import Base
from hybrid_monitor.db import models as _models  # noqa: F401

EXPECTED_TABLES = {
    "audit_logs",
    "permissions",
    "role_permissions",
    "roles",
    "user_roles",
    "users",
}


def test_identity_tables_are_registered() -> None:
    assert EXPECTED_TABLES.issubset(Base.metadata.tables)


def test_user_email_index_is_unique() -> None:
    users = Base.metadata.tables["users"]
    email_index = next(index for index in users.indexes if index.name == "ix_users_email")

    assert email_index.unique is True


def test_permission_code_index_is_unique() -> None:
    permissions = Base.metadata.tables["permissions"]
    code_index = next(
        index for index in permissions.indexes if index.name == "ix_permissions_code"
    )

    assert code_index.unique is True


def test_audit_log_indexes_match_query_patterns() -> None:
    audit_logs = Base.metadata.tables["audit_logs"]
    index_columns = {
        index.name: tuple(column.name for column in index.columns)
        for index in audit_logs.indexes
    }

    assert index_columns["ix_audit_logs_user_timestamp"] == ("user_id", "timestamp")
    assert index_columns["ix_audit_logs_action_timestamp"] == ("action", "timestamp")


def test_audit_metadata_column_keeps_safe_python_attribute() -> None:
    audit_logs = Base.metadata.tables["audit_logs"]

    assert "metadata" in audit_logs.c
    assert "details" not in audit_logs.c
