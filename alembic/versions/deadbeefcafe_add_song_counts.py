"""Add Song.*_counts

Revision ID: deadbeefcafe
Revises: 1d030c7a3a83
Create Date: 2018-09-22 13:55:16.188388

"""

# revision identifiers, used by Alembic.
revision = 'deadbeefcafe'
down_revision = '1d030c7a3a83'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('songs', sa.Column('favorite_count', sa.Integer()))
    op.add_column('songs', sa.Column('tag_count', sa.Integer()))
    op.add_column('songs', sa.Column('play_count', sa.Integer()))

    op.execute('''
        UPDATE songs
        SET
            favorite_count = (SELECT count(favorites.song)  FROM favorites WHERE favorites.song  = songs.id),
            tag_count      = (SELECT count(taggings.song)   FROM taggings  WHERE taggings.song   = songs.id),
            play_count     = (SELECT count(history.song) FROM history   WHERE history.song = songs.id);
    ''')

    # After populating the fields, non-null them
    op.alter_column('songs', 'favorite_count', nullable=False)
    op.alter_column('songs', 'tag_count', nullable=False)
    op.alter_column('songs', 'play_count', nullable=False)

    op.create_index(op.f('ix_songs_favorite_count'), 'songs', ['favorite_count'], unique=False)
    op.create_index(op.f('ix_songs_tag_count'), 'songs', ['tag_count'], unique=False)
    op.create_index(op.f('ix_songs_play_count'), 'songs', ['play_count'], unique=False)

    # Create functions and set up triggers
    # COALESCE(NEW, OLD) to support inserts and updates, where one of them is NULL
    op.execute('''
        CREATE FUNCTION update_song_favorite_count() RETURNS TRIGGER
        AS '
            BEGIN
            UPDATE songs
            SET favorite_count = (SELECT count(favorites.song) FROM favorites WHERE favorites.song = songs.id)
            WHERE songs.id = COALESCE(NEW.song, OLD.song);
            RETURN NULL;
            END
        ' LANGUAGE PLPGSQL;
    ''')
    op.execute('''
        CREATE FUNCTION update_song_tag_count() RETURNS TRIGGER
        AS '
            BEGIN
            UPDATE songs
            SET tag_count = (SELECT count(taggings.song) FROM taggings WHERE taggings.song = songs.id)
            WHERE songs.id = COALESCE(NEW.song, OLD.song);
            RETURN NULL;
            END
        ' LANGUAGE PLPGSQL;
    ''')
    op.execute('''
        CREATE FUNCTION update_song_play_count() RETURNS TRIGGER
        AS '
            BEGIN
            UPDATE songs
            SET play_count = (SELECT count(history.song) FROM history WHERE history.song = songs.id)
            WHERE songs.id = COALESCE(NEW.song, OLD.song);
            RETURN NULL;
            END
        ' LANGUAGE PLPGSQL;
    ''')

    op.execute('''
        CREATE TRIGGER song_favorite_count_update
        AFTER INSERT OR UPDATE OR DELETE ON favorites
        FOR EACH ROW EXECUTE PROCEDURE update_song_favorite_count();''')
    op.execute('''
        CREATE TRIGGER song_tag_count_update
        AFTER INSERT OR UPDATE OR DELETE ON taggings
        FOR EACH ROW EXECUTE PROCEDURE update_song_tag_count();''')
    op.execute('''
        CREATE TRIGGER song_play_count_update
        AFTER INSERT OR UPDATE OR DELETE ON history
        FOR EACH ROW EXECUTE PROCEDURE update_song_play_count();''')


def downgrade():
    op.execute('''DROP TRIGGER song_favorite_count_update ON favorites;''')
    op.execute('''DROP TRIGGER song_tag_count_update ON taggings;''')
    op.execute('''DROP TRIGGER song_play_count_update ON history;''')

    op.execute('''DROP FUNCTION update_song_favorite_count;''')
    op.execute('''DROP FUNCTION update_song_tag_count;''')
    op.execute('''DROP FUNCTION update_song_play_count;''')

    op.drop_column('songs', 'favorite_count')
    op.drop_column('songs', 'tag_count')
    op.drop_column('songs', 'play_count')
