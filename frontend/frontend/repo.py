import logging as _logging
import threading
from time import time

from sqlalchemy import desc, func, or_

from frontend.engine import session_scope
from frontend.logging import logging
from frontend.models import (
    MostRecentVideo,
    Playlist,
    PlaylistVideo,
    RSSFeedDate,
    YoutubeVideo,
)

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


def get_channel_videos(channel_name, page=0, items_per_page=35):
    try:
        with session_scope() as session:
            # Get total count
            total_count = (
                session.query(func.count(YoutubeVideo.id))
                .filter_by(channel=channel_name)
                .scalar()
            )

            # Get paginated data
            offset = page * items_per_page
            data = (
                session.query(YoutubeVideo)
                .filter_by(channel=channel_name)
                .order_by(YoutubeVideo.pub_date.desc())
                .limit(items_per_page)
                .offset(offset)
                .all()
            )
            return data, total_count
    except Exception as error:
        logger.warn(
            f"Failed to select videos from downloaded_videos table from {channel_name}",
            error,
        )
        return [], 0


def get_recent_videos(page, items_per_page=35):
    try:
        with session_scope() as session:
            # Get total count
            total_count = (
                session.query(func.count(YoutubeVideo.id))
                .filter(YoutubeVideo.short.is_(False))
                .scalar()
            )

            # Get paginated data
            offset = int(page) * items_per_page
            ordered_query = (
                session.query(YoutubeVideo).filter(YoutubeVideo.short.is_(False))
            ).order_by(YoutubeVideo.downloaded_at.desc())

            data = ordered_query.limit(items_per_page).offset(offset).all()
            return data, total_count
    except Exception as error:
        logger.warn(
            "Failed to select recent videos from downloaded_videos table", error
        )
        return [], 0


def get_recent_shorts(page, items_per_page=35):
    try:
        with session_scope() as session:
            # Get total count
            total_count = (
                session.query(func.count(YoutubeVideo.id))
                .filter(YoutubeVideo.vid_path != "NA")
                .filter(YoutubeVideo.short.is_(True))
                .filter(YoutubeVideo.livestream.is_(False))
                .scalar()
            )

            # Get paginated data
            offset = int(page) * items_per_page
            data = (
                session.query(YoutubeVideo)
                .filter(YoutubeVideo.vid_path != "NA")
                .filter(YoutubeVideo.short.is_(True))
                .filter(YoutubeVideo.livestream.is_(False))
                .order_by(YoutubeVideo.pub_date.desc())
                .limit(items_per_page)
                .offset(offset)
                .all()
            )
            return data, total_count
    except Exception as error:
        logger.warn(
            "Failed to select recent shorts from downloaded_videos table", error
        )
        return [], 0


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

        t1 = threading.Thread(target=create_or_update_most_recent_video, args=(id,))
        t1.start()
    except Exception as error:
        logger.error(f"Failed to update downloaded_videos table with id={id}", error)


def create_or_update_most_recent_video(id):
    try:
        with session_scope() as session:
            video = session.query(MostRecentVideo).filter_by(vid_id=id).first()
            if video:
                video.updated_at = int(time())
            else:
                new_video = MostRecentVideo(vid_id=id, updated_at=int(time()))
                session.add(new_video)
            session.commit()
    except Exception as error:
        logger.error(
            f"Failed to update most_recent_videos table with vid_id={id}", error
        )


def most_recent_video():
    try:
        with session_scope() as session:
            data = (
                session.query(MostRecentVideo)
                .order_by(MostRecentVideo.updated_at.desc())
                .limit(1)
                .first()
            )
            if data:
                return data
            else:
                return None
    except Exception as error:
        logger.warn(
            "Failed to select most recent video from most_recent_videos table", error
        )
        return []


def most_recent_videos():
    try:
        with session_scope() as session:
            data = (
                session.query(MostRecentVideo)
                .order_by(MostRecentVideo.updated_at.desc())
                .limit(35)
                .all()
            )
            if data:
                return data
            else:
                return None
    except Exception as error:
        logger.warn(
            "Failed to select most recent videos from most_recent_videos table", error
        )
        return []


def get_all_playlists():
    try:
        with session_scope() as session:
            data = session.query(Playlist).order_by(Playlist.name).all()
            return data
    except Exception as error:
        logger.warn("Failed to select playlists from playlist table", error)
        return []


def get_playlist_by_name(playlist_name):
    try:
        with session_scope() as session:
            data = session.query(Playlist).filter_by(name=playlist_name).first()
            return data
    except Exception as error:
        logger.warn(
            f"Failed to select playlist {playlist_name} from playlist table", error
        )
        return None


def get_playlist_videos(playlist_name, page=0, items_per_page=35):
    try:
        with session_scope() as session:
            # Get total count
            total_count = (
                session.query(func.count(PlaylistVideo.id))
                .filter(PlaylistVideo.playlist_name == playlist_name)
                .scalar()
            )

            # Get paginated data
            offset = page * items_per_page
            data = (
                session.query(PlaylistVideo, YoutubeVideo)
                .join(YoutubeVideo, PlaylistVideo.vid_url == YoutubeVideo.vid_url)
                .filter(PlaylistVideo.playlist_name == playlist_name)
                .limit(items_per_page)
                .offset(offset)
                .all()
            )
            return data, total_count
    except Exception as error:
        logger.warn(
            f"Failed to select videos from playlist_video table for playlist {playlist_name}",
            error,
        )
        return [], 0


def create_playlist(playlist_name):
    try:
        with session_scope() as session:
            existing_playlist = (
                session.query(Playlist).filter_by(name=playlist_name).first()
            )
            if existing_playlist:
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
            # Delete all videos from the playlist first
            session.query(PlaylistVideo).filter_by(playlist_name=playlist_name).delete()
            # Delete the playlist
            playlist = session.query(Playlist).filter_by(name=playlist_name).first()
            if playlist:
                session.delete(playlist)
                session.commit()
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
            playlist = session.query(Playlist).filter_by(name=playlist_name).first()
            if not playlist:
                return False, "Playlist not found"

            # Get video details
            video = session.query(YoutubeVideo).filter_by(id=video_id).first()
            if not video:
                return False, "Video not found"

            # Check if video is already in playlist
            existing_entry = (
                session.query(PlaylistVideo)
                .filter_by(playlist_name=playlist_name, vid_url=video.vid_url)
                .first()
            )
            if existing_entry:
                return False, "Video already in playlist"

            # Auto-keep the video to prevent deletion
            video.keep = True

            # Add video to playlist
            playlist_video = PlaylistVideo(
                vid_url=video.vid_url,
                vid_path=video.vid_path,
                title=video.title,
                playlist_name=playlist_name,
            )
            session.add(playlist_video)
            session.commit()
            return True, "Video added to playlist and marked as kept"
    except Exception as error:
        logger.error(
            f"Failed to add video {video_id} to playlist {playlist_name}", error
        )
        return False, "Failed to add video to playlist"


def remove_video_from_playlist(playlist_name, video_url):
    try:
        with session_scope() as session:
            playlist_video = (
                session.query(PlaylistVideo)
                .filter_by(playlist_name=playlist_name, vid_url=video_url)
                .first()
            )
            if playlist_video:
                session.delete(playlist_video)
                session.commit()
                return True, "Video removed from playlist"
            else:
                return False, "Video not found in playlist"
    except Exception as error:
        logger.error(
            f"Failed to remove video {video_url} from playlist {playlist_name}", error
        )
        return False, "Failed to remove video from playlist"


def get_filtered_videos(
    page=0,
    items_per_page=35,
    search_query=None,
    sort_by="downloaded_at",
    sort_order="desc",
    filter_kept=None,
    include_shorts=True,
):
    """
    Get videos with filtering, sorting, and search capabilities.

    :param page: Page number (0-based)
    :param items_per_page: Number of items per page
    :param search_query: Search query to match against title, description, or channel
    :param sort_by: Field to sort by (downloaded_at, pub_date, title, views)
    :param sort_order: Sort order (asc or desc)
    :param filter_kept: Filter by keep status (True, False, or None for all)
    :param include_shorts: Whether to include shorts (True/False)
    :return: Tuple of (videos, total_count)
    """
    try:
        with session_scope() as session:
            # Base query - include all videos for compatibility with original behavior
            # Only filter out videos without vid_path if they're "NA"
            query = session.query(YoutubeVideo).filter(YoutubeVideo.vid_path != "NA")

            # Filter shorts - match original behavior
            if not include_shorts:
                query = query.filter(YoutubeVideo.short.is_(False))

            # Filter by keep status
            if filter_kept is not None:
                query = query.filter(YoutubeVideo.keep.is_(filter_kept))

            # Search functionality
            if search_query and search_query.strip():
                search_term = f"%{search_query.strip()}%"
                query = query.filter(
                    or_(
                        YoutubeVideo.title.ilike(search_term),
                        YoutubeVideo.description.ilike(search_term),
                        YoutubeVideo.channel.ilike(search_term),
                    )
                )

            # Get total count before applying pagination
            total_count = query.count()

            # Apply sorting
            if sort_by == "downloaded_at":
                sort_field = YoutubeVideo.downloaded_at
            elif sort_by == "pub_date":
                sort_field = YoutubeVideo.pub_date
            elif sort_by == "title":
                sort_field = YoutubeVideo.title
            elif sort_by == "views":
                sort_field = YoutubeVideo.views
            else:
                sort_field = YoutubeVideo.downloaded_at

            if sort_order == "desc":
                query = query.order_by(desc(sort_field))
            else:
                query = query.order_by(sort_field)

            # Apply pagination
            offset = page * items_per_page
            videos = query.limit(items_per_page).offset(offset).all()

            return videos, total_count

    except Exception as error:
        logger.warn("Failed to get filtered videos", error)
        return [], 0
