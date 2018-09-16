"""improve history

Revision ID: e43080100a6f
Revises: 9468e73ed926
Create Date: 2018-09-10 20:55:44.072925

"""

# revision identifiers, used by Alembic.
revision = 'e43080100a6f'
down_revision = '9468e73ed926'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('history', sa.Column(sa.Integer,
            sa.ForeignKey("songs.id"),
            name="song"))
    op.execute("""UPDATE history SET song = (data->>'id')::int
            WHERE data->>'id' ~ '^\d+$'
            AND EXISTS(SELECT 1 FROM songs WHERE id = (data->>'id')::int)""")
    op.execute("""UPDATE history SET song =
            (SELECT id FROM songs WHERE hash = data->>'hash')
            WHERE song IS NULL""")
    op.execute("""DELETE FROM history WHERE song IS NULL""")
    op.alter_column('history', 'song', nullable=False)
    op.alter_column('history', 'data', nullable=True)


def downgrade():
    op.drop_column('history', 'song')
    op.alter_column('history', 'data', nullable=False)
