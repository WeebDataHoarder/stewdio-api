"""Add album artists indexes

Revision ID: abf740a01621
Revises: ae12046bfa16
Create Date: 2019-08-24 17:45:16.188388

"""

# revision identifiers, used by Alembic.
revision = 'abf740a01621'
down_revision = 'ae12046bfa16'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm;')
    op.create_index('songs_trgm_title_idx', 'songs', ['title'], postgresql_using='gin',
                    postgresql_ops={
                        'title': 'gin_trgm_ops',
                    }, unique=False)
    op.create_unique_constraint('artists_name_pkey', 'artists', ['name'])
    op.create_index('artists_trgm_name_idx', 'artists', ['name'], postgresql_using='gin',
                    postgresql_ops={
                        'name': 'gin_trgm_ops',
                    }, unique=False)
    op.create_unique_constraint('albums_name_pkey', 'albums', ['name'])
    op.create_index('albums_trgm_name_idx', 'albums', ['name'], postgresql_using='gin',
                    postgresql_ops={
                        'name': 'gin_trgm_ops',
                    }, unique=False)
    op.create_index('songs_artist_idx', 'songs', ['artist'], unique=False)
    op.create_index('songs_album_idx', 'songs', ['album'], unique=False)

def downgrade():
    op.drop_index('songs_trgm_title_idx', table_name='artists')
    op.drop_index('artists_trgm_name_idx', table_name='artists')
    op.drop_index('albums_trgm_name_idx', table_name='albums')
    op.drop_index('songs_artist_idx', table_name='songs')
    op.drop_index('songs_album_idx', table_name='songs')
    op.drop_constraint('artists_name_pkey', 'artists')
    op.drop_constraint('albums_name_pkey', 'albums')
