from sqlalchemy import Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.schema import Column
from sqlalchemy.types import JSON, Boolean, Integer, String, Text

Base = declarative_base()


class YoutubeVideo(Base):
    __tablename__ = "youtube_video"
    id = Column(Integer, primary_key=True)
    vid_url = Column(String(300), unique=True)
    vid_path = Column(String(255))
    thumb_url = Column(String(1000))
    thumb_path = Column(String(1000))
    pub_date = Column(Integer)
    pub_date_human = Column(String(1000))
    title = Column(String(1000))
    views = Column(Integer)
    description = Column(Text)
    channel = Column(String(1000))
    short = Column(Boolean)
    livestream = Column(Boolean)
    progress_seconds = Column(Integer)
    inserted_at = Column(Integer)
    downloaded_at = Column(Integer)

    # Add composite index
    index_pub_date = Index("idx_pub_date", pub_date)
    index_downloaded_at = Index("idx_downloaded_at", downloaded_at)
    composite_index = Index("idx_filter_conditions", vid_path, short)


class JsonData(Base):
    __tablename__ = "json_data"
    id = Column(Integer, primary_key=True)
    rss_feed_json = Column(JSON)


class RSSFeedDate(Base):
    __tablename__ = "rss_feed_date"
    id = Column(Integer, primary_key=True)
    date_human = Column(String(1000))


class Playlist(Base):
    __tablename__ = "playlist"
    id = Column(Integer, primary_key=True)
    name = Column(String(1000))


class PlaylistVideo(Base):
    __tablename__ = "playlist_video"
    id = Column(Integer, primary_key=True)
    vid_url = Column(String(1000))
    vid_path = Column(String(1000))
    title = Column(String(1000))
    playlist_name = Column(String(1000))
