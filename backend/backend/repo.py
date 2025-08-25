import json
import logging as _logging
from time import time

from sqlalchemy import and_, desc, or_, select

from backend.constants import LIVE_DELAY
from backend.engine import session_scope
from backend.logging import logging
from backend.models import (
    Channel,
    DownloadJob,
    JsonData,
    Playlist,
    PlaylistVideo,
    RSSFeedDate,
    YoutubeVideo,
)

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
                select(PlaylistVideo).where(
                    PlaylistVideo.playlist_name == playlist_name
                )
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
                select(PlaylistVideo).where(
                    PlaylistVideo.playlist_name == playlist_name
                )
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
                        PlaylistVideo.vid_url == video[0].vid_url,
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
            result = session.execute(
                select(PlaylistVideo).where(
                    and_(
                        PlaylistVideo.playlist_name == playlist_name,
                        PlaylistVideo.vid_url == video_url,
                    )
                )
            ).delete()

            session.commit()
            if result:
                return True, "Video removed from playlist"
            else:
                return False, "Video not found in playlist"
    except Exception as error:
        logger.error(
            f"Failed to remove video {video_url} from playlist {playlist_name}", error
        )
        return False, "Failed to remove video from playlist"


def add_channel_to_db(channel_id, channel_url, channel_name):
    """
    Add a channel to the database.

    :param channel_id: YouTube channel ID
    :param channel_url: Channel URL
    :param channel_name: Channel display name
    :return: Tuple of (success, message)
    """
    try:
        with session_scope() as session:
            # Check if channel already exists
            existing = session.execute(
                select(Channel).where(Channel.channel_id == channel_id)
            ).first()
            if existing:
                return False, "Channel already exists in database"

            # Add channel to database
            new_channel = Channel(
                channel_id=channel_id,
                channel_url=channel_url,
                channel_name=channel_name,
                keep=False,
                inserted_at=int(time()),
            )
            session.add(new_channel)
            session.commit()
            return True, "Channel added successfully"
    except Exception as error:
        logger.error(f"Failed to add channel {channel_name} to database", error)
        return False, "Failed to add channel to database"


def get_channel_by_id(channel_id):
    """
    Get a channel by its ID.

    :param channel_id: YouTube channel ID
    :return: Channel object or None
    """
    try:
        with session_scope() as session:
            data = session.execute(
                select(Channel).where(Channel.channel_id == channel_id)
            ).first()
            return data[0] if data else None
    except Exception as error:
        logger.error(f"Failed to get channel {channel_id}", error)
        return None


def remove_channel_from_db(channel_id):
    """
    Remove a channel from the database.

    :param channel_id: YouTube channel ID
    :return: Tuple of (success, message)
    """
    try:
        with session_scope() as session:
            result = session.execute(
                select(Channel).where(Channel.channel_id == channel_id)
            ).delete()

            session.commit()
            if result:
                return True, "Channel removed successfully"
            else:
                return False, "Channel not found"
    except Exception as error:
        logger.error(f"Failed to remove channel {channel_id}", error)
        return False, "Failed to remove channel"


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
            # Base query
            query = session.query(YoutubeVideo).filter(
                and_(YoutubeVideo.vid_path != "NA", YoutubeVideo.vid_path.isnot(None))
            )

            # Filter shorts
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
        logger.error("Failed to get filtered videos", error)
        return [], 0


def create_download_job(video_url, video_title, channel_name, video_data, priority=0):
    """
    Create a new download job for async processing.

    :param video_url: URL of the video to download
    :param video_title: Title of the video
    :param channel_name: Channel name
    :param video_data: Full video data from RSS
    :param priority: Job priority (higher = more important)
    :return: Tuple of (success, message, job_id)
    """
    try:
        with session_scope() as session:
            # Check if job already exists for this video
            existing = session.execute(
                select(DownloadJob).where(
                    and_(
                        DownloadJob.video_url == video_url,
                        DownloadJob.status.in_(["pending", "downloading", "retrying"]),
                    )
                )
            ).first()

            if existing:
                return (
                    False,
                    "Download job already exists for this video",
                    existing[0].id,
                )

            # Create new download job
            download_job = DownloadJob(
                video_url=video_url,
                video_title=video_title,
                channel_name=channel_name,
                status="pending",
                priority=priority,
                created_at=int(time()),
                video_data=json.dumps(video_data),
            )

            session.add(download_job)
            session.commit()
            session.refresh(download_job)

            logger.info(f"Created download job for video: {video_title}")
            return True, "Download job created successfully", download_job.id

    except Exception as error:
        logger.error(f"Failed to create download job for {video_url}", error)
        return False, "Failed to create download job", None


def get_pending_download_jobs(limit=10):
    """
    Get pending download jobs ordered by priority and creation time.

    :param limit: Maximum number of jobs to return
    :return: List of download jobs
    """
    try:
        with session_scope() as session:
            data = session.execute(
                select(DownloadJob)
                .where(DownloadJob.status == "pending")
                .order_by(desc(DownloadJob.priority), DownloadJob.created_at)
                .limit(limit)
            ).all()
            return [job[0] for job in data]
    except Exception as error:
        logger.error("Failed to get pending download jobs", error)
        return []


def get_retry_download_jobs(limit=10):
    """
    Get download jobs marked for retry.

    :param limit: Maximum number of jobs to return
    :return: List of download jobs
    """
    try:
        with session_scope() as session:
            data = session.execute(
                select(DownloadJob)
                .where(DownloadJob.status == "retrying")
                .order_by(desc(DownloadJob.priority), DownloadJob.created_at)
                .limit(limit)
            ).all()
            return [job[0] for job in data]
    except Exception as error:
        logger.error("Failed to get retry download jobs", error)
        return []


def update_download_job_status(job_id, status, error_message=None):
    """
    Update the status of a download job.

    :param job_id: ID of the download job
    :param status: New status
    :param error_message: Error message if status is failed
    :return: True if successful, False otherwise
    """
    try:
        with session_scope() as session:
            job = session.query(DownloadJob).filter(DownloadJob.id == job_id).first()
            if not job:
                return False

            job.status = status

            if status == "downloading":
                job.started_at = int(time())
            elif status in ["completed", "failed"]:
                job.completed_at = int(time())

            if error_message:
                job.error_message = error_message

            session.commit()
            return True

    except Exception as error:
        logger.error(f"Failed to update download job status for job {job_id}", error)
        return False


def retry_download_job(job_id):
    """
    Mark a failed download job for retry if it hasn't exceeded max retries.

    :param job_id: ID of the download job
    :return: Tuple of (success, message)
    """
    try:
        with session_scope() as session:
            job = session.query(DownloadJob).filter(DownloadJob.id == job_id).first()
            if not job:
                return False, "Download job not found"

            if job.retry_count >= job.max_retries:
                return False, "Maximum retries exceeded"

            job.status = "retrying"
            job.retry_count += 1
            job.error_message = None
            job.started_at = None
            job.completed_at = None

            session.commit()
            return True, "Download job marked for retry"

    except Exception as error:
        logger.error(f"Failed to retry download job {job_id}", error)
        return False, "Failed to mark job for retry"


def get_download_job_stats():
    """
    Get statistics about download jobs.

    :return: Dictionary with job counts by status
    """
    try:
        with session_scope() as session:
            stats = {}

            # Count jobs by status
            for status in ["pending", "downloading", "completed", "failed", "retrying"]:
                count = (
                    session.query(DownloadJob)
                    .filter(DownloadJob.status == status)
                    .count()
                )
                stats[status] = count

            return stats

    except Exception as error:
        logger.error("Failed to get download job stats", error)
        return {}


def get_download_jobs_paginated(page=0, items_per_page=50, status_filter=None):
    """
    Get download jobs with pagination and optional status filtering.

    :param page: Page number (0-based)
    :param items_per_page: Items per page
    :param status_filter: Filter by status (optional)
    :return: Tuple of (jobs, total_count)
    """
    try:
        with session_scope() as session:
            query = session.query(DownloadJob)

            if status_filter:
                query = query.filter(DownloadJob.status == status_filter)

            total_count = query.count()

            jobs = (
                query.order_by(desc(DownloadJob.created_at))
                .offset(page * items_per_page)
                .limit(items_per_page)
                .all()
            )

            return jobs, total_count

    except Exception as error:
        logger.error("Failed to get paginated download jobs", error)
        return [], 0


def delete_old_download_jobs(days_old=30):
    """
    Delete completed and failed download jobs older than specified days.

    :param days_old: Number of days to keep jobs
    :return: Number of jobs deleted
    """
    try:
        with session_scope() as session:
            cutoff_time = int(time()) - (days_old * 24 * 60 * 60)

            deleted_count = (
                session.query(DownloadJob)
                .filter(
                    and_(
                        DownloadJob.status.in_(["completed", "failed"]),
                        DownloadJob.created_at < cutoff_time,
                    )
                )
                .delete()
            )

            session.commit()
            logger.info(f"Deleted {deleted_count} old download jobs")
            return deleted_count

    except Exception as error:
        logger.error("Failed to delete old download jobs", error)
        return 0
