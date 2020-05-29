"""Add covers

Revision ID: c6b0e9463194
Revises: 5fa3e1d4dbb5
Create Date: 2019-07-03 17:45:16.188388

"""

# revision identifiers, used by Alembic.
revision = 'c6b0e9463194'
down_revision = '5fa3e1d4dbb5'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('covers',
    sa.Column('id', sa.BIGINT(), primary_key=True),
    sa.Column('hash', sa.Text(), nullable=False, unique=True),
    sa.Column('type', sa.Text(), nullable=False),
    sa.Column('mime', sa.Text(), nullable=False),
    sa.Column('data', sa.LargeBinary(), nullable=False)
    )
    op.add_column('songs', sa.Column('cover', sa.BIGINT(), sa.ForeignKey('covers.id'), nullable=True))


def downgrade():
    op.drop_column('songs', 'cover')
    op.drop_table('covers')
