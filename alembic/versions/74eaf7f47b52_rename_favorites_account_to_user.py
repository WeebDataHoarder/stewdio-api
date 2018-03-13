"""Rename favorites.account to user

Revision ID: 74eaf7f47b52
Revises: bb0b1a4d9123
Create Date: 2018-03-13 22:06:41.660344

"""

# revision identifiers, used by Alembic.
revision = '74eaf7f47b52'
down_revision = 'bb0b1a4d9123'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column('favorites', 'account', new_column_name='user_id')
    op.drop_constraint('favorites_account_fkey', 'favorites')
    op.create_foreign_key('favorites_user_fkey', 'favorites', 'users', ['user_id'], ['id'])


def downgrade():
    op.alter_column('favorites', 'user_id', new_column_name='account')
    op.drop_constraint('favorites_user_fkey', 'favorites')
    op.create_foreign_key('favorites_account_fkey', 'favorites', 'users', ['account'], ['id'])
