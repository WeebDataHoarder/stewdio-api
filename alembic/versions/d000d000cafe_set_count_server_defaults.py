"""Set count server_defaults

Revision ID: d000d000beef
Revises: deadbeefcafe
Create Date: 2018-09-22 13:55:16.188388

"""

# revision identifiers, used by Alembic.
revision = 'd000d000beef'
down_revision = 'deadbeefcafe'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.alter_column('songs', 'favorite_count', server_default=sa.text('0'))
    op.alter_column('songs', 'tag_count', server_default=sa.text('0'))
    op.alter_column('songs', 'play_count', server_default=sa.text('0'))


def downgrade():
    op.alter_column('songs', 'favorite_count', server_default=None)
    op.alter_column('songs', 'tag_count', server_default=None)
    op.alter_column('songs', 'play_count', server_default=None)
