import logging as _logging

from frontend.engine import session_scope
from frontend.logging import logging
from frontend.models import RSSFeedDate, YoutubeVideo

logger = logging.getLogger(__name__)
logger.setLevel(_logging.INFO)


def get_video_by_id(identifier):
    try:
        with session_scope() as session:
            data = session.query(YoutubeVideo).filter_by(id=identifier).first()
            return data
    except Exception as error:
        logger.warn(
            f"Failed to select videos from downloaded_videos table with id={identifier}",
            error,
        )
        return []


def get_channel_videos(channel_name):
    try:
        with session_scope() as session:
            data = (
                session.query(YoutubeVideo)
                .filter_by(channel=channel_name)
                .order_by(YoutubeVideo.pub_date.desc())
            )
            return data
    except Exception as error:
        logger.warn(
            f"Failed to select videos from downloaded_videos table from {channel_name}",
            error,
        )
        return []


def get_recent_videos(page, inserted_at_sort=False):
    try:
        with session_scope() as session:
            selection = (int(page) + 1) * 35
            initial_query = (
                session.query(YoutubeVideo)
                .filter(YoutubeVideo.vid_path != "NA")
                .filter(YoutubeVideo.short.is_(False))
            )
            ordered_query = None
            if inserted_at_sort:
                ordered_query = initial_query.order_by(
                    YoutubeVideo.downloaded_at.desc()
                )
            else:
                ordered_query = initial_query.order_by(YoutubeVideo.pub_date.desc())

            data = ordered_query.limit(35).offset(selection - 35).all()
            return data
    except Exception as error:
        logger.warn(
            "Failed to select recent videos from downloaded_videos table", error
        )
        return []


def get_recent_shorts(page):
    try:
        with session_scope() as session:
            selection = (int(page) + 1) * 35
            data = (
                session.query(YoutubeVideo)
                .filter(YoutubeVideo.vid_path != "NA")
                .filter(YoutubeVideo.short.is_(True))
                .filter(YoutubeVideo.livestream.is_(False))
                .order_by(YoutubeVideo.pub_date.desc())
                .limit(35)
                .offset(selection - 35)
                .all()
            )
            return data
    except Exception as error:
        logger.warn(
            "Failed to select recent shorts from downloaded_videos table", error
        )
        return []


def get_rss_date():
    try:
        with session_scope() as session:
            data = (
                session.query(RSSFeedDate)
                .order_by(RSSFeedDate.id.desc())
                .limit(1)
                .first()
            )
            if data:
                return data
            else:
                return RSSFeedDate()
    except Exception as error:
        logger.warn("Failed to select recent videos from rss_feed_date table", error)
        return []


def update_video_progress(id, progress):
    try:
        with session_scope() as session:
            updated_rec = session.query(YoutubeVideo).filter_by(id=id).first()
            updated_rec.progress_seconds = progress
            session.commit()
    except Exception as error:
        logger.error(f"Failed to update downloaded_videos table with id={id}", error)


def get_last_videos(number_of_videos):
    try:
        with session_scope() as session:
            data = (
                session.query(YoutubeVideo)
                .order_by(YoutubeVideo.downloaded_at.desc())
                .limit(number_of_videos)
                .all()
            )
            return data
    except Exception as error:
        logger.error(
            f"Failed to select {number_of_videos} recently downloaded videos", error
        )
