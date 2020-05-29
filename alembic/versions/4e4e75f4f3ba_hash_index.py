"""Partial index for hashes

Revision ID: 4e4e75f4f3ba
Revises: abf740a01621
Create Date: 2020-02-27 17:45:16.188388

"""

# revision identifiers, used by Alembic.
revision = '4e4e75f4f3ba'
down_revision = 'abf740a01621'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_index('songs_trgm_hash_idx', 'songs', ['hash'], postgresql_using='gin',
                    postgresql_ops={
                        'hash': 'gin_trgm_ops',
                    }, unique=False)

def downgrade():
    op.drop_index('songs_trgm_hash_idx', table_name='songs')
