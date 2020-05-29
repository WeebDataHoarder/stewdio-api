"""Add audio hash

Revision ID: ae12046bfa16
Revises: 80a64208ce6b
Create Date: 2019-08-10 17:45:16.188388

"""

# revision identifiers, used by Alembic.
revision = 'ae12046bfa16'
down_revision = '80a64208ce6b'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('songs', sa.Column('audio_hash', sa.Text(), nullable=True))
    op.create_index('songs_audio_hash_idx', 'songs', ['audio_hash'], unique=False)

def downgrade():
    op.drop_index('songs_audio_hash_idx', table_name='songs')
    op.drop_column('songs', 'audio_hash')

