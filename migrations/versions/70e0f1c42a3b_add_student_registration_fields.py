"""Add student registration fields to users.

Revision ID: 70e0f1c42a3b
Revises: 38c4e85512a9
Create Date: 2026-10-26
"""

from alembic import op
import sqlalchemy as sa


revision = '70e0f1c42a3b'
down_revision = '38c4e85512a9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('prontuario', sa.String(length=32), nullable=True))
    op.add_column('users', sa.Column('student_name', sa.String(length=128), nullable=True))
    op.add_column('users', sa.Column('email', sa.String(length=254), nullable=True))


def downgrade():
    op.drop_column('users', 'email')
    op.drop_column('users', 'student_name')
    op.drop_column('users', 'prontuario')
