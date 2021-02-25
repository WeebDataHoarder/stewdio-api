"""Add API pkey

Revision ID: 64c20a8f4378
Revises: abcdeffedcba
Create Date: 2019-06-01 14:45:16.188388

"""

# revision identifiers, used by Alembic.
revision = '64c20a8f4378'
down_revision = 'abcdeffedcba'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_unique_constraint('user_api_keys_user_pkey', 'user_api_keys', ['name', 'user'])

def downgrade():
    op.drop_constraint('user_api_keys_user_pkey', 'user_api_keys')
