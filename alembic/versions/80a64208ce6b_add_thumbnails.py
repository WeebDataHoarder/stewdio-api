"""Add thumbnails

Revision ID: 80a64208ce6b
Revises: 08124622783b
Create Date: 2019-07-13 17:45:16.188388

"""

# revision identifiers, used by Alembic.
revision = '80a64208ce6b'
down_revision = '08124622783b'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('covers', sa.Column('thumb_small', sa.LargeBinary(), nullable=True))
    op.add_column('covers', sa.Column('thumb_large', sa.LargeBinary(), nullable=True))

def downgrade():
    op.drop_column('covers', 'thumb_small')
    op.drop_column('covers', 'thumb_large')
