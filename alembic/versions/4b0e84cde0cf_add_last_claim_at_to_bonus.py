"""add last_claim_at to bonus

Revision ID: 4b0e84cde0cf
Revises: 02c060d8569e
Create Date: 2026-02-16 19:45:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4b0e84cde0cf'
down_revision = '02c060d8569e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add last_claim_at column to bonus table."""
    op.add_column('bonus', sa.Column('last_claim_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Remove last_claim_at column from bonus table."""
    op.drop_column('bonus', 'last_claim_at')
