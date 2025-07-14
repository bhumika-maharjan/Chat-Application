"""Merge heads to unify migrations

Revision ID: 17b9b1833494
Revises: 5548ced79565, b0459cbd8ae5
Create Date: 2025-07-14 15:11:11.704098

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "17b9b1833494"
down_revision: str | Sequence[str] | None = ("5548ced79565", "b0459cbd8ae5")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
