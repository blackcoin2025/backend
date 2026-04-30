"""add timezone to started_at

Revision ID: e4260c738b43
Revises: 7e86be98d751
Create Date: 2026-04-28 10:34:56.237464
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4260c738b43'
down_revision: Union[str, Sequence[str], None] = '7e86be98d751'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # 🔥 conversion propre vers timezone UTC
    op.execute("""
        ALTER TABLE user_daily_tasks
        ALTER COLUMN started_at TYPE TIMESTAMP WITH TIME ZONE
        USING started_at AT TIME ZONE 'UTC';
    """)

    op.execute("""
        ALTER TABLE user_daily_tasks
        ALTER COLUMN completed_at TYPE TIMESTAMP WITH TIME ZONE
        USING completed_at AT TIME ZONE 'UTC';
    """)


def downgrade() -> None:
    """Downgrade schema."""

    # ⚠️ retour en arrière (perte timezone)
    op.execute("""
        ALTER TABLE user_daily_tasks
        ALTER COLUMN started_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    """)

    op.execute("""
        ALTER TABLE user_daily_tasks
        ALTER COLUMN completed_at TYPE TIMESTAMP WITHOUT TIME ZONE;
    """)