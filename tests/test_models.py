from sqlalchemy import UniqueConstraint

from app.models import Base, DeliveryAttempt, Notification, OperatorAction, Provider


def test_core_tables_are_declared():
    table_names = set(Base.metadata.tables)

    assert {
        "providers",
        "notifications",
        "delivery_attempts",
        "operator_actions",
    }.issubset(table_names)


def test_notification_has_event_uniqueness_constraint():
    constraints = [
        constraint
        for constraint in Notification.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    ]

    assert any(
        {column.name for column in constraint.columns} == {"provider_code", "event_type", "event_id"}
        for constraint in constraints
    )


def test_models_include_operational_columns():
    provider_columns = set(Provider.__table__.columns.keys())
    notification_columns = set(Notification.__table__.columns.keys())
    attempt_columns = set(DeliveryAttempt.__table__.columns.keys())
    action_columns = set(OperatorAction.__table__.columns.keys())

    assert {"provider_code", "display_name", "enabled", "paused", "queue_name"}.issubset(provider_columns)
    assert {
        "provider_code",
        "event_type",
        "event_id",
        "payload",
        "metadata",
        "status",
        "attempt_count",
    }.issubset(notification_columns)
    assert {"notification_id", "attempt_number", "response_status", "error_type", "error_message"}.issubset(
        attempt_columns
    )
    assert {"action_type", "target_type", "target_id", "actor"}.issubset(action_columns)
