"""Add password authentication and e-mail confirmation.

Revision ID: 9c2d8f5a1b40
Revises: af12b3c4d5e6
Create Date: 2026-11-15
"""

import os

from alembic import op
import sqlalchemy as sa
from werkzeug.security import generate_password_hash


revision = '9c2d8f5a1b40'
down_revision = 'af12b3c4d5e6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('password_hash', sa.String(length=256), nullable=True))
    op.add_column('users', sa.Column('confirmed', sa.Boolean(), nullable=False, server_default=sa.false()))
    connection = op.get_bind()
    users = sa.table('users', sa.column('id', sa.Integer), sa.column('password_hash', sa.String))
    connection.execute(sa.text('UPDATE users SET email = lower(email) WHERE email IS NOT NULL'))
    for user_id, in connection.execute(sa.select(users.c.id)):
        connection.execute(users.update().where(users.c.id == user_id).values(
            password_hash=generate_password_hash(os.urandom(32).hex())))
    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('email', existing_type=sa.String(length=254), nullable=False)
        batch_op.alter_column('password_hash', existing_type=sa.String(length=256), nullable=False)
        batch_op.create_index('ix_users_email', ['email'], unique=True)


def downgrade():
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_index('ix_users_email')
        batch_op.drop_column('confirmed')
        batch_op.drop_column('password_hash')
