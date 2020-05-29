"""history song index

Revision ID: 1d030c7a3a83
Revises: ebbe2ad47fef
Create Date: 2018-10-03 10:31:06.297466

"""

# revision identifiers, used by Alembic.
revision = '1d030c7a3a83'
down_revision = 'ebbe2ad47fef'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_index('history_song_idx', 'history', ['song'], unique=False)

def downgrade():
    op.drop_index('history_song_idx', table_name='history')
