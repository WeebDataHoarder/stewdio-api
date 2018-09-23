import sqlalchemy as sa

from ..database import Base

class History(Base):
    __tablename__ = "history"
    id = sa.Column(sa.BIGINT, primary_key=True)
    play_time = sa.Column(sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now())
    song_id = sa.Column(sa.Integer,
            sa.ForeignKey("songs.id"),
            name="song",
            nullable=False)
    song = sa.orm.relationship("Song")

    def json(self):
        return dict(
            id=self.id,
            play_time=self.play_time.timestamp(),
            song=self.song.json(),
        )
