"""change balance.points to bigint

Revision ID: 7e86be98d751
Revises: 0e5d65e23fa2
Create Date: 2026-03-01 02:20:43.528921
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7e86be98d751'
down_revision = '0e5d65e23fa2'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Upgrade schema: change balance.points from Integer to BigInteger."""
    op.alter_column(
        table_name="balance",
        column_name="points",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False
    )


def downgrade() -> None:
    """Downgrade schema: change balance.points from BigInteger back to Integer."""
    op.alter_column(
        table_name="balance",
        column_name="points",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False
    )