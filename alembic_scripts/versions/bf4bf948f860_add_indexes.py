"""add indexes

Revision ID: bf4bf948f860
Revises: e43080100a6f
Create Date: 2018-09-22 11:38:52.159738

"""

# revision identifiers, used by Alembic.
revision = 'bf4bf948f860'
down_revision = 'e43080100a6f'

from alembic import op

def upgrade():
    op.create_index('taggings_tag_idx', 'taggings', ['tag'], unique=False)
    op.create_index('taggings_song_idx', 'taggings', ['song'], unique=False)
    op.create_index('favorites_user_id_idx', 'favorites', ['user_id'], unique=False)
    op.create_index('favorites_song_idx', 'favorites', ['song'], unique=False)


def downgrade():
    op.drop_index('favorites_song_idx', table_name='favorites')
    op.drop_index('favorites_user_id_idx', table_name='favorites')
    op.drop_index('taggings_song_idx', table_name='taggings')
    op.drop_index('taggings_tag_idx', table_name='taggings')
