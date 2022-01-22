"""Add Status Index

Revision ID: 05ae38b278ea
Revises: 2fddb20de34f
Create Date: 2022-01-22 20:45:16.188388

"""

# revision identifiers, used by Alembic.
revision = '05ae38b278ea'
down_revision = '2fddb20de34f'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_index('songs_status_idx', 'songs', ['status'], unique=False)


def downgrade():
    op.drop_index('songs_status_idx', table_name='songs')