"""Add source

Revision ID: 08124622783b
Revises: c6b0e9463194
Create Date: 2019-07-03 17:45:16.188388

"""

# revision identifiers, used by Alembic.
revision = '08124622783b'
down_revision = 'c6b0e9463194'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('history', sa.Column('source', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('history', 'source')
