"""Rename Song fields

Revision ID: 4c4f05124c3e
Revises: c8e3ade17ee0
Create Date: 2018-02-26 21:32:20.972375

"""

# revision identifiers, used by Alembic.
revision = '4c4f05124c3e'
down_revision = 'c8e3ade17ee0'

from alembic import op


def upgrade():
    op.alter_column('songs', 'length', new_column_name='duration')
    op.alter_column('songs', 'location', new_column_name='path')


def downgrade():
    op.alter_column('songs', 'duration', new_column_name='length')
    op.alter_column('songs', 'path', new_column_name='location')
