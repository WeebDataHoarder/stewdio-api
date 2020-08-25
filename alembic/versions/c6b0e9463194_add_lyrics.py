"""Add lyrics

Revision ID: 1a4a356ee2f5
Revises: 4e4e75f4f3ba
Create Date: 2029-08-25 17:45:16.188388

"""

# revision identifiers, used by Alembic.
revision = '1a4a356ee2f5'
down_revision = '4e4e75f4f3ba'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('songs', sa.Column('lyrics', sa.JSON().with_variant(sa.dialects.postgresql.JSONB(none_as_null=True), 'postgresql'), nullable=True))


def downgrade():
    op.drop_column('songs', 'lyrics')
