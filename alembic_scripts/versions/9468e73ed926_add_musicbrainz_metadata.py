"""Add MusicBrainz metadata

Revision ID: 9468e73ed926
Revises: 74eaf7f47b52
Create Date: 2018-03-29 23:37:07.888458

"""

# revision identifiers, used by Alembic.
revision = '9468e73ed926'
down_revision = '74eaf7f47b52'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('songs', sa.Column('mb_metadata', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('songs', 'mb_metadata')
