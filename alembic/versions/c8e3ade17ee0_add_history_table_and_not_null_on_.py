"""Add History table and NOT NULL on favorites

Revision ID: c8e3ade17ee0
Revises: 45330e860116
Create Date: 2018-02-26 21:16:11.598602

"""

# revision identifiers, used by Alembic.
revision = 'c8e3ade17ee0'
down_revision = '45330e860116'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table('history',
    sa.Column('id', sa.BIGINT(), primary_key=True),
    sa.Column('play_time', sa.TIMESTAMP(timezone=True), nullable=False),
    sa.Column('data', sa.JSON(), nullable=False)
    )
    op.alter_column('favorites', 'account',
               existing_type=sa.INTEGER(),
               nullable=False)
    op.alter_column('favorites', 'song',
               existing_type=sa.INTEGER(),
               nullable=False)


def downgrade():
    op.alter_column('favorites', 'song',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.alter_column('favorites', 'account',
               existing_type=sa.INTEGER(),
               nullable=True)
    op.drop_table('history')
