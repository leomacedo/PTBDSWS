"""Seed default user roles and assign the existing first user as admin.

Revision ID: af12b3c4d5e6
Revises: 70e0f1c42a3b
Create Date: 2026-10-26
"""

from alembic import op
import sqlalchemy as sa


revision = 'af12b3c4d5e6'
down_revision = '70e0f1c42a3b'
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    roles = sa.table('roles', sa.column('id', sa.Integer), sa.column('name', sa.String))
    users = sa.table('users', sa.column('id', sa.Integer), sa.column('role_id', sa.Integer))

    existing_roles = {
        row.name: row.id
        for row in connection.execute(sa.select(roles.c.id, roles.c.name)).fetchall()
    }
    if 'Admin' not in existing_roles:
        connection.execute(roles.insert().values(name='Admin'))
    if 'User' not in existing_roles:
        connection.execute(roles.insert().values(name='User'))

    role_ids = {
        row.name: row.id
        for row in connection.execute(sa.select(roles.c.id, roles.c.name)).fetchall()
    }
    user_ids = [row.id for row in connection.execute(sa.select(users.c.id).order_by(users.c.id)).fetchall()]
    if user_ids:
        connection.execute(
            users.update().where(users.c.id == user_ids[0]).values(role_id=role_ids['Admin'])
        )
    if len(user_ids) > 1:
        connection.execute(
            users.update().where(users.c.id.in_(user_ids[1:])).values(role_id=role_ids['User'])
        )


def downgrade():
    connection = op.get_bind()
    roles = sa.table('roles', sa.column('id', sa.Integer), sa.column('name', sa.String))
    users = sa.table('users', sa.column('role_id', sa.Integer))
    role_ids = sa.select(roles.c.id).where(roles.c.name.in_(['Admin', 'User']))
    connection.execute(users.update().where(users.c.role_id.in_(role_ids)).values(role_id=None))
    connection.execute(roles.delete().where(roles.c.name.in_(['Admin', 'User'])))
