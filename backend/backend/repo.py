import json
import logging as _logging
from time import time

from sqlalchemy import and_, select

from backend.constants import DELAY
from backend.engine import session_scope
from backend.logging import logging
from backend.models import JsonData, RSSFeedDate, YoutubeVideo

logger = logging.getLogger(__name__)
logger.setLevel(_logging.INFO)


def expire_video(identifier):
    try:
        with session_scope() as session:
            updated_rec = session.query(YoutubeVideo).filter_by(id=identifier).first()
            updated_rec.vid_path = "NA"
            updated_rec.thumb_path = "NA"
            session.commit()
    except Exception as error:
        logger.error(
            f"Failed to update downloaded_videos table with id={identifier}", error
        )


def get_expired_videos(date):
    try:
        with session_scope() as session:
            data = (
                session.query(YoutubeVideo)
                .filter(YoutubeVideo.pub_date < date)
                .filter(YoutubeVideo.vid_path != "NA")
                .all()
            )
            return data
    except Exception as error:
        logger.error(
            "Failed to select expired videos from downloaded_videos table", error
        )
        return []


def update_view_count(video_data):
    try:
        with session_scope() as session:
            url = video_data["video_url"]
            views = int(video_data["views"])
            rating = float(video_data["rating"])
            vid = session.query(YoutubeVideo).filter_by(vid_url=url).first()
            vid.views = views
            vid.rating = rating
            session.commit()
    except Exception as error:
        logger.error(
            f"Failed to update downloaded_videos table with vid_url={video_data['video_url']}",
            error,
        )


def update_rss_date(date_str):
    try:
        with session_scope() as session:
            data = (
                session.query(RSSFeedDate)
                .order_by(RSSFeedDate.id.desc())
                .limit(1)
                .all()
            )
            if data == []:
                insert_rss_date(session, date_str)
            else:
                data[0].date_human = date_str
            session.commit()
    except Exception as error:
        logger.error(f"Failed to update rss_feed_date table", error)


def insert_rss_date(session, date_str):
    try:
        session.add(RSSFeedDate(date_human=date_str))
    except Exception as error:
        logger.error("Failed to insert video into downloaded_videos table", error)


def get_json():
    try:
        with session_scope() as session:
            data = session.query(JsonData).order_by(JsonData.id.desc()).limit(1).first()
            if data:
                return data.rss_feed_json
            return data
    except Exception as error:
        logger.error("Failed to select recent videos from json_data table", error)
        return []


def update_json(json_data):
    try:
        with session_scope() as session:
            data = session.query(JsonData).order_by(JsonData.id.desc()).limit(1).all()
            if data == []:
                insert_json(json.dumps(json_data))
            else:
                data[0].rss_feed_json = json.dumps(json_data)
            session.commit()
    except Exception as error:
        logger.error("Failed to update json_data table", error)


def insert_json(json_data):
    try:
        with session_scope() as session:
            session.add(JsonData(rss_feed_json=json_data))
            session.commit()
    except Exception as error:
        logger.error("Failed to insert jsondata into JsonData table", error)


def get_downloaded_video_urls():
    try:
        with session_scope() as session:
            down_vid_urls = [
                res[0] for res in session.execute(select(YoutubeVideo.vid_url)).all()
            ]
            return down_vid_urls
    except Exception as error:
        logger.error("Failed to get downloaded video urls", error)
        return []


def get_livestream_videos():
    # we want to get the livestream videos that are not downloaded and are older than 24 hours and are less than DELAY old

    time_now = int(time())
    try:
        with session_scope() as session:
            data = session.execute(
                select(YoutubeVideo)
                .where(YoutubeVideo.livestream)
                .where(YoutubeVideo.downloaded_at.is_(None))
                .where(YoutubeVideo.inserted_at < time_now - 86400)
                .where(YoutubeVideo.inserted_at > time_now - DELAY)
            ).all()
            return data
    except Exception as error:
        logger.error("Failed to get livestreams to download", error)
        return []


def get_all_videos():
    try:
        with session_scope() as session:
            data = session.execute(
                select(YoutubeVideo)
                .where(
                    and_(YoutubeVideo.vid_path != "NA", YoutubeVideo.vid_path != None)
                )
                .where(YoutubeVideo.size.is_(None))
            ).all()
            return data
    except Exception as error:
        logger.error("Failed to get all videos", error)
        return []
