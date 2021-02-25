"""Add user passwords and API keys

Revision ID: bb0b1a4d9123
Revises: 4c4f05124c3e
Create Date: 2018-03-13 21:34:56.285427

"""

# revision identifiers, used by Alembic.
revision = 'bb0b1a4d9123'
down_revision = '4c4f05124c3e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('user_api_keys',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('user', sa.Integer(), nullable=False),
    sa.Column('key', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['user'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('key')
    )
    op.alter_column('users', 'nick', new_column_name='name')
    op.add_column('users', sa.Column('password', sa.Text(), nullable=True))
    op.create_index('uniq_name', 'users', ['name'], unique=True)
    op.drop_index('uniq_nick', table_name='users')


def downgrade():
    op.alter_column('users', 'name', new_column_name='nick')
    op.create_index('uniq_nick', 'users', ['nick'], unique=True)
    op.drop_index('uniq_name', table_name='users')
    op.drop_column('users', 'password')
    op.drop_table('user_api_keys')
