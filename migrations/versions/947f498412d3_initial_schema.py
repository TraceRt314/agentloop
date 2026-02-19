"""initial schema

Baseline migration — stamps the version table without altering existing
tables. All tables were created by SQLModel.metadata.create_all() before
Alembic was introduced.

Revision ID: 947f498412d3
Revises:
Create Date: 2026-02-19 12:37:30.939329

"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = '947f498412d3'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Baseline — no schema changes needed."""
    pass


def downgrade() -> None:
    """Baseline — nothing to undo."""
    pass
