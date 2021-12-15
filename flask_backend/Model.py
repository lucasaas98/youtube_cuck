import sqlalchemy
from sqlalchemy.future.engine import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.schema import Column
from sqlalchemy.types import Float, Integer, String, Text
from sqlalchemy.orm.session import sessionmaker
from sqlalchemy.dialects.mysql import LONGTEXT

import os


db_user = 'root'
db_pass = os.getenv("db_root_password")
db_name = os.getenv("db_name")
db_host = os.getenv("YT_CUCK_MYSQL_SERVICE_HOST")
db_port = os.getenv("YT_CUCK_MYSQL_SERVICE_PORT")

engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}")

Base = declarative_base()



class YoutubeVideo(Base):
    __tablename__ = 'youtube_video'
    id = Column(Integer, primary_key=True)
    vid_url = Column(String(1000), unique=True)
    vid_path = Column(String(1000))
    thumb_url = Column(String(1000))
    thumb_path = Column(String(1000))
    pub_date = Column(Integer)
    pub_date_human = Column(String(1000))
    rating = Column(Float)
    title = Column(String(1000))
    views = Column(Integer)
    description = Column(Text)
    channel = Column(String(1000))


class JsonData(Base):
    __tablename__ = 'json_data'
    id = Column(Integer, primary_key=True)
    rss_feed_json = Column(LONGTEXT)


class VideoFlag(Base):
    __tablename__ = 'video_flag'
    id = Column(Integer, primary_key=True)
    flag = Column(Integer)


class RSSFeedDate(Base):
    __tablename__ = 'rss_feed_date'
    id = Column(Integer, primary_key=True)
    date_human = Column(String(1000))


class Playlist(Base):
    __tablename__ = 'playlist'
    id = Column(Integer, primary_key=True)
    name = Column(String(1000))


class PlaylistVideo(Base):
    __tablename__ = 'playlist_video'
    id = Column(Integer, primary_key=True)
    vid_url = Column(String(1000))
    vid_path = Column(String(1000))
    title = Column(String(1000))
    playlist_name = Column(String(1000))

class ThreadPool(Base):
    __tablename__ = 'thread_pool'
    id = Column(Integer, primary_key=True)
    count = Column(Integer)

def get_db_access():
    factory = sessionmaker(bind=engine)
    session = factory()
    return session