"""add indexes

Revision ID: ebbe2ad47fef
Revises: bf4bf948f860
Create Date: 2018-09-22 13:55:16.188388

"""

# revision identifiers, used by Alembic.
revision = 'ebbe2ad47fef'
down_revision = 'bf4bf948f860'

from alembic import op


def upgrade():
    # taggings must be free from duplicates and must not have a primary key
    op.create_primary_key('taggings_pkey', 'taggings', ['song', 'tag'])


def downgrade():
    op.drop_constraint('PRIMARY', 'taggings_pkey', type_='primary')
