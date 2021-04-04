"""Score index

Revision ID: 2fddb20de34f
Revises: 1a4a356ee2f5
Create Date: 2021-04-04 20:45:16.188388

"""

# revision identifiers, used by Alembic.
revision = '2fddb20de34f'
down_revision = '1a4a356ee2f5'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm;')
    op.create_index('songs_trgm_path_idx', 'songs', ['path'], postgresql_using='gin',
                    postgresql_ops={
                        'path': 'gin_trgm_ops',
                    }, unique=False)
    op.create_unique_constraint('songs_path_pkey', 'songs', ['path'])
    op.add_column('songs', sa.Column('score', sa.Integer()))
    op.execute('''
        UPDATE songs
        SET
            score = (songs.favorite_count * 5 + songs.play_count + (CASE WHEN songs.path ILIKE \'%%.flac\' THEN 5 ELSE 0 END));
    ''')
    op.alter_column('songs', 'score', nullable=False)
    op.create_index('songs_score_idx', 'songs', ['score'], unique=False)
    op.execute('''
        CREATE FUNCTION update_song_score() RETURNS TRIGGER
        AS '
            BEGIN
            IF NEW.favorite_count <> OLD.favorite_count OR NEW.play_count <> OLD.play_count THEN
                UPDATE songs
                SET
                score = (songs.favorite_count * 5 + songs.play_count + (CASE WHEN songs.path ILIKE \'\'%%.flac\'\' THEN 5 ELSE 0 END))
                WHERE songs.id = COALESCE(NEW.id, OLD.id);
            END IF;
            RETURN NULL;
            END
        ' LANGUAGE PLPGSQL;
    ''')
    op.execute('''
        CREATE TRIGGER song_score_update
        AFTER INSERT OR UPDATE OR DELETE ON songs
        FOR EACH ROW EXECUTE PROCEDURE update_song_score();''')


def downgrade():
    op.execute('''DROP TRIGGER song_score_update ON songs;''')
    op.execute('''DROP FUNCTION update_song_score;''')
    op.drop_index('songs_score_idx', table_name='songs')
    op.drop_index('songs_trgm_path_idx', table_name='songs')
    op.drop_constraint('songs_path_pkey', 'songs')
    op.drop_column('songs', 'score')
