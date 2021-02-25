"""Fix triggers

Revision ID: abcdeffedcba
Revises: d000d000beef
Create Date: 2018-09-22 13:55:16.188388

"""

# revision identifiers, used by Alembic.
revision = 'abcdeffedcba'
down_revision = 'd000d000beef'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.execute('''DROP TRIGGER song_favorite_count_update ON favorites;''')
    op.execute('''DROP TRIGGER song_tag_count_update ON taggings;''')
    op.execute('''DROP TRIGGER song_play_count_update ON history;''')

    op.execute('''DROP FUNCTION update_song_favorite_count;''')
    op.execute('''DROP FUNCTION update_song_tag_count;''')
    op.execute('''DROP FUNCTION update_song_play_count;''')

    # Create function and set up triggers
    op.execute('''
        CREATE FUNCTION update_song_count_from() RETURNS TRIGGER
        AS $$
        DECLARE
            song_id INTEGER;
        BEGIN
            -- Pick NEW or OLD
            IF TG_OP = 'DELETE' THEN
                song_id = OLD.song;
            ELSE
                song_id = NEW.song;
            END IF;


            EXECUTE format('
                UPDATE songs
                SET %1$I = (SELECT count(%2$I.song) FROM %2$I WHERE %2$I.song = songs.id)
                WHERE songs.id = %3$s;
            ', TG_ARGV[0], TG_TABLE_NAME, song_id);

            RETURN NULL;
        END
        $$ LANGUAGE PLPGSQL;
    ''')

    op.execute('''
        CREATE TRIGGER song_favorite_count_update
        AFTER INSERT OR UPDATE OR DELETE ON favorites
        FOR EACH ROW EXECUTE PROCEDURE update_song_count_from('favorite_count');''')
    op.execute('''
        CREATE TRIGGER song_tag_count_update
        AFTER INSERT OR UPDATE OR DELETE ON taggings
        FOR EACH ROW EXECUTE PROCEDURE update_song_count_from('tag_count');''')
    op.execute('''
        CREATE TRIGGER song_play_count_update
        AFTER INSERT OR UPDATE OR DELETE ON history
        FOR EACH ROW EXECUTE PROCEDURE update_song_count_from('play_count');''')


def downgrade():
    op.execute('''DROP TRIGGER song_favorite_count_update ON favorites;''')
    op.execute('''DROP TRIGGER song_tag_count_update ON taggings;''')
    op.execute('''DROP TRIGGER song_play_count_update ON history;''')

    op.execute('''DROP FUNCTION update_song_count_from;''')

    # Recreate old
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
