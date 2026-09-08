"""Durable owner serialization and shared login throttle.

Revision ID: 0002
Revises: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('owner_state',
        sa.Column('owner_id', sa.String(128), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('login_failures', sa.Integer(), nullable=False),
        sa.Column('window_started', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('owner_id'))


def downgrade():
    op.drop_table('owner_state')
