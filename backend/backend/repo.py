import json
import logging as _logging
from time import time

from sqlalchemy import and_, select

from backend.constants import LIVE_DELAY
from backend.engine import session_scope
from backend.logging import logging
from backend.models import Channel, JsonData, Playlist, PlaylistVideo, RSSFeedDate, YoutubeVideo

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
                .filter(YoutubeVideo.keep.is_(False))
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
        logger.error("Failed to update rss_feed_date table", error)


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
    # we want to get the livestream videos that are not downloaded and are older than 12 hours and are less than LIVE_DELAY old
    time_now = int(time())
    try:
        with session_scope() as session:
            data = session.execute(
                select(YoutubeVideo)
                .where(YoutubeVideo.livestream)
                .where(YoutubeVideo.downloaded_at.is_(None))
                .where(YoutubeVideo.inserted_at < time_now - 43200)
                .where(YoutubeVideo.inserted_at > time_now - LIVE_DELAY)
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
                    and_(
                        YoutubeVideo.vid_path != "NA", YoutubeVideo.vid_path.isnot(None)
                    )
                )
                .where(YoutubeVideo.size.is_(None))
            ).all()
            return data
    except Exception as error:
        logger.error("Failed to get all videos", error)
        return []


def get_real_all_videos(session):
    data = session.execute(
        select(YoutubeVideo).where(YoutubeVideo.channel_id.is_(None))
    ).all()
    return data


def get_all_channels():
    try:
        with session_scope() as session:
            data = session.execute(select(Channel)).all()
            return data
    except Exception as error:
        logger.error("Failed to get all videos", error)
        return []


def get_video_by_id(video_id):
    try:
        with session_scope() as session:
            data = session.execute(
                select(YoutubeVideo).where(YoutubeVideo.id == video_id)
            ).one()
            return data
    except Exception as error:
        logger.error("Failed to get all videos", error)
        return []


def get_all_playlists():
    try:
        with session_scope() as session:
            data = session.execute(select(Playlist)).all()
            return data
    except Exception as error:
        logger.error("Failed to get all playlists", error)
        return []


def get_playlist_by_name(playlist_name):
    try:
        with session_scope() as session:
            data = session.execute(
                select(Playlist).where(Playlist.name == playlist_name)
            ).first()
            return data
    except Exception as error:
        logger.error(f"Failed to get playlist {playlist_name}", error)
        return None


def get_playlist_videos(playlist_name):
    try:
        with session_scope() as session:
            data = session.execute(
                select(PlaylistVideo).where(PlaylistVideo.playlist_name == playlist_name)
            ).all()
            return data
    except Exception as error:
        logger.error(f"Failed to get videos for playlist {playlist_name}", error)
        return []


def create_playlist(playlist_name):
    try:
        with session_scope() as session:
            existing = session.execute(
                select(Playlist).where(Playlist.name == playlist_name)
            ).first()
            if existing:
                return False, "Playlist already exists"

            new_playlist = Playlist(name=playlist_name)
            session.add(new_playlist)
            session.commit()
            return True, "Playlist created successfully"
    except Exception as error:
        logger.error(f"Failed to create playlist {playlist_name}", error)
        return False, "Failed to create playlist"


def delete_playlist(playlist_name):
    try:
        with session_scope() as session:
            # Delete playlist videos first
            session.execute(
                select(PlaylistVideo).where(PlaylistVideo.playlist_name == playlist_name)
            ).delete()

            # Delete playlist
            result = session.execute(
                select(Playlist).where(Playlist.name == playlist_name)
            ).delete()

            session.commit()
            if result:
                return True, "Playlist deleted successfully"
            else:
                return False, "Playlist not found"
    except Exception as error:
        logger.error(f"Failed to delete playlist {playlist_name}", error)
        return False, "Failed to delete playlist"


def add_video_to_playlist(playlist_name, video_id):
    try:
        with session_scope() as session:
            # Check if playlist exists
            playlist = session.execute(
                select(Playlist).where(Playlist.name == playlist_name)
            ).first()
            if not playlist:
                return False, "Playlist not found"

            # Get video details
            video = session.execute(
                select(YoutubeVideo).where(YoutubeVideo.id == video_id)
            ).first()
            if not video:
                return False, "Video not found"

            # Check if video already in playlist
            existing = session.execute(
                select(PlaylistVideo).where(
                    and_(
                        PlaylistVideo.playlist_name == playlist_name,
                        PlaylistVideo.vid_url == video[0].vid_url
                    )
                )
            ).first()
            if existing:
                return False, "Video already in playlist"

            # Auto-keep the video to prevent deletion
            video[0].keep = True

            # Add video to playlist
            playlist_video = PlaylistVideo(
                vid_url=video[0].vid_url,
                vid_path=video[0].vid_path,
                title=video[0].title,
                playlist_name=playlist_name
            )
            session.add(playlist_video)
            session.commit()
            return True, "Video added to playlist and marked as kept"
    except Exception as error:
        logger.error(f"Failed to add video {video_id} to playlist {playlist_name}", error)
        return False, "Failed to add video to playlist"


def remove_video_from_playlist(playlist_name, video_url):
    try:
        with session_scope() as session:
            result = session.execute(
                select(PlaylistVideo).where(
                    and_(
                        PlaylistVideo.playlist_name == playlist_name,
                        PlaylistVideo.vid_url == video_url
                    )
                )
            ).delete()

            session.commit()
            if result:
                return True, "Video removed from playlist"
            else:
                return False, "Video not found in playlist"
    except Exception as error:
        logger.error(f"Failed to remove video {video_url} from playlist {playlist_name}", error)
        return False, "Failed to remove video from playlist"
