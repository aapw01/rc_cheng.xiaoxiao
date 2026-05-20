"""align providers.provider_code with model

The 0001 migration declared `provider_code` via a standalone
`UniqueConstraint` plus a non-unique `ix_providers_provider_code` index,
while the SQLAlchemy model declares it as `unique=True, index=True`,
which translates to a single unique index of the same name. This migration
removes the redundant constraint and rebuilds the index as unique so that
`alembic check` no longer reports schema drift.

Revision ID: 0002_provider_code_unique
Revises: 0001_initial
Create Date: 2026-05-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002_provider_code_unique"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("providers_provider_code_key", "providers", type_="unique")
    op.drop_index("ix_providers_provider_code", table_name="providers")
    op.create_index("ix_providers_provider_code", "providers", ["provider_code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_providers_provider_code", table_name="providers")
    op.create_index("ix_providers_provider_code", "providers", ["provider_code"], unique=False)
    op.create_unique_constraint("providers_provider_code_key", "providers", ["provider_code"])
