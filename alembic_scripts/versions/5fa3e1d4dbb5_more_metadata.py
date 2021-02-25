"""More metadata

Revision ID: 5fa3e1d4dbb5
Revises: 64c20a8f4378
Create Date: 2019-07-03 14:45:16.188388

"""

# revision identifiers, used by Alembic.
revision = '5fa3e1d4dbb5'
down_revision = '64c20a8f4378'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.alter_column('songs', 'mb_metadata', type_=sa.dialects.postgresql.JSONB, postgresql_using='mb_metadata::text::jsonb')
    op.add_column('songs', sa.Column('song_metadata', sa.JSON().with_variant(sa.dialects.postgresql.JSONB(none_as_null=True), 'postgresql'), nullable=True))
    op.add_column('users', sa.Column('user_metadata', sa.JSON().with_variant(sa.dialects.postgresql.JSONB(none_as_null=True), 'postgresql'), nullable=True))

def downgrade():
    op.alter_column('songs', 'mb_metadata', type_=sa.dialects.postgresql.JSON, postgresql_using='mb_metadata::text::json')
    op.drop_column('songs', 'song_metadata')
    op.drop_column('users', 'user_metadata')
