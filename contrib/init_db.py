#!/usr/bin/env python3

from stewdio.config import db
from stewdio.database import Base
import stewdio.types

db.engine.echo = True
Base.metadata.create_all(bind=db.engine)

# Create functions and triggers for automatically updating songs.*_counts
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

db.session.commit()
