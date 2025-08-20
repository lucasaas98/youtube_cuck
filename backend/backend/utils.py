import functools
import json
import logging as _logging
import os
import random
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from subprocess import DEVNULL, check_output
from typing import Optional, Tuple

import dateutil.parser as date_parser
import feedparser
import opml
import requests
import yt_dlp
from yt_dlp.utils import DownloadError, ExtractorError, UnavailableVideoError

from backend.constants import DELAY, REMOVAL_DELAY
from backend.download_monitor import (
    download_monitor,
    rate_limiter,
    should_download_now,
    wait_for_safe_download,
)
from backend.engine import session_scope
from backend.env_vars import DATA_FOLDER
from backend.error_reporter import (
    report_download_error,
)
from backend.logging import logging
from backend.models import YoutubeVideo
from backend.repo import (
    expire_video,
    get_downloaded_video_urls,
    get_expired_videos,
    get_json,
    get_livestream_videos,
    get_video_by_id,
    update_json,
    update_rss_date,
    update_view_count,
)

logger = logging.getLogger(__name__)
logger.setLevel(_logging.INFO)

video_executor = ThreadPoolExecutor(max_workers=1)
update_count_executor = ThreadPoolExecutor(max_workers=32)

# Import monitoring components with error handling
try:
    from backend.download_monitor import (
        download_monitor,
        rate_limiter,
        resource_monitor,
        should_download_now,
        wait_for_safe_download,
    )
    from backend.error_reporter import (
        error_reporter,
        report_download_error,
        report_recovery_action,
    )

    MONITORING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Monitoring features not available: {e}")
    MONITORING_AVAILABLE = False

    # Provide dummy functions if monitoring is not available
    class DummyMonitor:
        def record_download_attempt(self, *args, **kwargs):
            pass

        def record_download_success(self, *args, **kwargs):
            pass

        def record_download_failure(self, *args, **kwargs):
            pass

        def get_stats_summary(self):
            return {}

        def get_recent_success_rate(self, *args):
            return 100

        def get_success_rate(self):
            return 100

    class DummyRateLimiter:
        def record_request(self):
            pass

        def record_success(self):
            pass

        def record_failure(self, *args, **kwargs):
            pass

        def can_make_request(self):
            return True

        def get_wait_time(self):
            return 0

    download_monitor = DummyMonitor()
    rate_limiter = DummyRateLimiter()

    def should_download_now():
        return True, ""

    def wait_for_safe_download():
        return True

    def report_download_error(*args, **kwargs):
        pass

    def report_recovery_action(*args, **kwargs):
        pass


# Safety wrapper functions to prevent errors when monitoring is not available
def safe_report_download_error(*args, **kwargs):
    """Safely report download errors, ignoring failures if monitoring unavailable."""
    try:
        if MONITORING_AVAILABLE:
            report_download_error(*args, **kwargs)
    except Exception as e:
        logger.debug(f"Failed to report download error: {e}")


def safe_monitor_download_attempt(*args, **kwargs):
    """Safely record download attempt, ignoring failures if monitoring unavailable."""
    try:
        if MONITORING_AVAILABLE and hasattr(download_monitor, 'record_download_attempt'):
            download_monitor.record_download_attempt(*args, **kwargs)
    except Exception as e:
        logger.debug(f"Failed to record download attempt: {e}")


def safe_monitor_download_success(*args, **kwargs):
    """Safely record download success, ignoring failures if monitoring unavailable."""
    try:
        if MONITORING_AVAILABLE and hasattr(download_monitor, 'record_download_success'):
            download_monitor.record_download_success(*args, **kwargs)
    except Exception as e:
        logger.debug(f"Failed to record download success: {e}")


def safe_monitor_download_failure(*args, **kwargs):
    """Safely record download failure, ignoring failures if monitoring unavailable."""
    try:
        if MONITORING_AVAILABLE and hasattr(download_monitor, 'record_download_failure'):
            download_monitor.record_download_failure(*args, **kwargs)
    except Exception as e:
        logger.debug(f"Failed to record download failure: {e}")


def log_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Entering function {func.__name__}")
        result = func(*args, **kwargs)
        logger.info(f"Exiting function {func.__name__}")
        return result

    return wrapper


@log_decorator
def get_rss_data():
    """
    Parse the OPML file containing YouTube channel subscriptions and fetch channel data.

    :return: A dictionary containing channel names as keys and their video data as values.
    :rtype: dict
    """
    data = open(f"{DATA_FOLDER}/subscription_manager", "r")
    nested = opml.parse(data)
    all_channels = dict()

    with ThreadPoolExecutor(max_workers=8) as rss_executor:
        futures = [
            rss_executor.submit(get_channel_data, channel) for channel in nested[0]
        ]

    for future in futures:
        channel_data, channel_name = future.result()
        all_channels[channel_name] = channel_data

    return all_channels


@log_decorator
def remove_old_videos():
    """
    Remove old videos and their thumbnails based on the REMOVAL_DELAY value.
    """
    min_pub_date = time.time() - REMOVAL_DELAY
    records = get_expired_videos(min_pub_date)
    for expired_video in records:
        try:
            file_path = os.path.join(f"{DATA_FOLDER}/videos", expired_video.vid_path)
            if not os.path.exists(file_path):
                file_path = os.path.join(
                    f"{DATA_FOLDER}/videos", expired_video.vid_path.split(".")[0]
                )
            os.remove(file_path)
            logger.info(f"Delete video at path: {file_path}")

        except Exception:
            logger.error(f"Failed to delete video at path: {file_path}")

        try:
            thumb_path = os.path.join(
                f"{DATA_FOLDER}/thumbnails", expired_video.thumb_path
            )
            os.remove(thumb_path)
            logger.info(f"Delete thumbnail at path: {thumb_path}")
        except Exception:
            logger.error(f"Failed to delete thumbnail at path: {thumb_path}")

        expire_video(expired_video.id)


@log_decorator
def get_rss_feed():
    """
    Update the RSS feed data, fetch new data, and start a new thread to download the videos.

    :return: The thread object responsible for downloading videos.
    :rtype: threading.Thread
    """
    date = datetime.now()
    date_str = datetime.strftime(date, "%d/%m/%Y, %H:%M:%S GMT")
    logger.info(f"[{date_str}] Getting RSS feed!")
    update_rss_date(date_str)
    new_json = get_rss_data()
    update_json(new_json)
    thread = threading.Thread(target=get_video)
    thread.start()
    return thread


@log_decorator
def get_channel_data(channel):
    """
    Fetch video data from a channel using the feedparser library.

    :param channel: The channel object containing the YouTube channel information.
    :type channel: object
    :return: A tuple containing a list of video data dictionaries and the channel title.
    :rtype: tuple
    """
    channel_data = list()
    video_feed = feedparser.parse(channel.xmlUrl)

    for entry in video_feed["entries"]:
        thumbnail = entry["media_thumbnail"]
        date = date_parser.parse(entry["published"])
        human_readable_date = datetime.strftime(date, "%a %B %d, %Y %I:%M %p GMT")
        epoch_date = datetime.strftime(date, "%s")
        description = entry["summary"]
        rating = entry["media_starrating"]
        views = entry["media_statistics"]
        video_url = entry["link"]
        title = entry["title"]
        all_info = {
            "title": title,
            "thumbnail": thumbnail[0]["url"],
            "human_date": human_readable_date,
            "epoch_date": epoch_date,
            "description": description,
            "rating": rating["average"],
            "views": views["views"],
            "video_url": video_url,
        }
        channel_data.append(all_info)
    return channel_data, channel.title


@log_decorator
def get_video():
    """
    Download videos from the channels based on the DELAY value.
    """
    logger.info("Downloading videos!")
    try:
        down_vid_urls = get_downloaded_video_urls()
        min_date = time.time() - DELAY
        json_video_data = json.loads(get_json())

        futures = []
        for channel in json_video_data.keys():
            for video in json_video_data[channel]:
                url = video["video_url"]
                if url in down_vid_urls:
                    futures.append(
                        update_count_executor.submit(update_view_count, video)
                    )
                    continue
                if float(video["epoch_date"]) < min_date:
                    continue
                if "/shorts/" in url:
                    continue
                futures.append(
                    video_executor.submit(video_download_thread, video, channel)
                )

        for future in futures:
            future.result()

    except Exception as error:
        logger.error(f"Failed to get new videos: {error}")
    finally:
        logger.info("Videos Downloaded!")


@log_decorator
def video_type(video_info):
    """
    Determines the type of video based on its information.

    Args:
        video_info (dict): A dictionary containing information about the video.

    Returns:
        str: A string representing the type of video. Possible values are "premiere", "livestream", "short", and "regular video".
    """

    if video_info is None:
        return "premiere"
    elif video_info["is_live"]:
        return "livestream"
    elif video_info["duration"] is not None and video_info["duration"] < 62:
        return "short"
    else:
        return "regular video"


@log_decorator
def extract_video_info(video_url):
    """
    Extracts video information from a given YouTube video URL using the youtube-dl library.

    Args:
        video_url (str): The URL of the YouTube video to extract information from.

    Returns:
        dict or None: The extracted video information, or None if extraction failed.
    """
    options = {
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
    }

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                video_info = ydl.extract_info(video_url, download=False)
                return video_info
        except UnavailableVideoError as error:
            logger.error(f"Video unavailable for {video_url}: {error}")
            safe_report_download_error("video_unavailable", str(error), video_url)
            return None
        except ExtractorError as error:
            logger.error(f"Extractor error for {video_url}: {error}")
            safe_report_download_error("extractor_error", str(error), video_url)
            return None
        except DownloadError as error:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Download error for {video_url} (attempt {attempt + 1}): {error}. Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error(
                    f"Failed to extract video info for {video_url} after {max_retries} attempts: {error}"
                )
                safe_report_download_error(
                    "extraction_failed", str(error), video_url, attempts=max_retries
                )
                return None
        except Exception as error:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Unexpected error for {video_url} (attempt {attempt + 1}): {error}. Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error(
                    f"Failed to extract video info for {video_url} after {max_retries} attempts: {error}"
                )
                safe_report_download_error(
                    "extraction_error", str(error), video_url, attempts=max_retries
                )
                return None

    return None


def check_disk_space(required_mb: int = 1000) -> bool:
    """Check if there's enough disk space for download."""
    try:
        statvfs = os.statvfs(DATA_FOLDER)
        free_bytes = statvfs.f_frsize * statvfs.f_bavail
        free_mb = free_bytes / (1024 * 1024)
        return free_mb > required_mb
    except Exception as error:
        logger.error(f"Failed to check disk space: {error}")
        return False


def cleanup_partial_download(file_name: str) -> None:
    """Clean up partial download files."""
    try:
        video_path = f"{DATA_FOLDER}/videos/{file_name}.mp4"
        thumb_path = f"{DATA_FOLDER}/thumbnails/{file_name}.jpg"
        temp_video_path = f"{DATA_FOLDER}/videos/{file_name}.mp4.part"

        for path in [video_path, thumb_path, temp_video_path]:
            if os.path.exists(path):
                os.remove(path)
                logger.info(f"Cleaned up partial file: {path}")
    except Exception as error:
        logger.error(f"Failed to cleanup partial download for {file_name}: {error}")


@log_decorator
def video_download_thread(video, channel):
    """
    Download a video and its thumbnail based on the video type and update the database.

    :param video: A dictionary containing the video data.
    :type video: dict
    :param channel: The name of the YouTube channel.
    :type channel: str
    """
    file_name = None
    try:
        # Check if it's safe to download now
        can_download, reason = should_download_now()
        if not can_download:
            logger.info(f"Delaying download of {video['title']}: {reason}")
            if not wait_for_safe_download():
                logger.error(
                    f"Skipping download of {video['title']} due to system conditions"
                )
                safe_report_download_error(
                    "system_overload",
                    reason,
                    video["video_url"],
                    video.get("title"),
                    channel=channel,
                )
                return

        # Check disk space before starting
        if not check_disk_space():
            logger.error(f"Insufficient disk space to download video: {video['title']}")
            safe_report_download_error(
                "disk_space",
                "Insufficient disk space",
                video["video_url"],
                video.get("title"),
                channel=channel,
            )
            return

        video_info = extract_video_info(video["video_url"])

        if video_info is None:
            logger.error(
                f"Failed to extract video info for {video['title']}, skipping download"
            )
            safe_report_download_error(
                "info_extraction_failed",
                "Could not extract video information",
                video["video_url"],
                video.get("title"),
                channel=channel,
            )
            return

        video_type_result = video_type(video_info)
        video_object = None

        if video_type_result in ["livestream", "premiere"]:
            video_object = YoutubeVideo(
                vid_url=video["video_url"],
                thumb_url=video["thumbnail"],
                pub_date=int(video["epoch_date"]),
                pub_date_human=video["human_date"],
                title=video["title"],
                views=int(video["views"]),
                description=video["description"],
                channel=channel,
                livestream=True,
                short=False,
                inserted_at=int(time.time()),
            )
        else:
            file_name = video["video_url"].split("=")[1]

            # Record download attempt
            safe_monitor_download_attempt(video["video_url"], file_name)

            # Attempt video download with proper error handling
            download_success, error_msg = download_video(video["video_url"], file_name)

            if not download_success:
                logger.error(f"Failed to download video {video['title']}: {error_msg}")
                safe_monitor_download_failure(video["video_url"], error_msg)
                safe_report_download_error(
                    "download_failed",
                    error_msg,
                    video["video_url"],
                    video.get("title"),
                    channel=channel,
                )
                cleanup_partial_download(file_name)
                return

            now = int(time.time())

            # Verify the download was successful
            if not confirm_video_name(file_name):
                logger.error(f"Video file not found after download: {file_name}")
                safe_report_download_error(
                    "file_verification_failed",
                    f"Downloaded file not found: {file_name}",
                    video["video_url"],
                    video.get("title"),
                    channel=channel,
                )
                cleanup_partial_download(file_name)
                return

            vid_path = f"{file_name}.mp4"
            thumb_path = f"{file_name}.jpg"

            # Download thumbnail with error handling
            if not download_thumbnail(video["thumbnail"], thumb_path):
                logger.warning(
                    f"Failed to download thumbnail for {video['title']}, continuing without thumbnail"
                )
                thumb_path = None

            # Get video size with error handling
            size = get_video_size(vid_path)
            if size is None:
                logger.warning(
                    f"Failed to get video size for {video['title']}, setting size to 0"
                )
                size = 0

            # Calculate file size in MB for monitoring
            try:
                full_path = f"{DATA_FOLDER}/videos/{vid_path}"
                file_size_mb = os.path.getsize(full_path) / (1024 * 1024)
                safe_monitor_download_success(
                    video["video_url"], file_size_mb
                )
            except Exception as error:
                logger.warning(f"Failed to get file size for monitoring: {error}")
                safe_monitor_download_success(video["video_url"], 0)

            video_object = YoutubeVideo(
                vid_url=video["video_url"],
                vid_path=vid_path,
                thumb_url=video["thumbnail"],
                thumb_path=thumb_path,
                pub_date=int(video["epoch_date"]),
                pub_date_human=video["human_date"],
                title=video["title"],
                views=int(video["views"]),
                description=video["description"],
                channel=channel,
                livestream=False,
                short=video_type_result == "short",
                inserted_at=now,
                downloaded_at=now,
                size=size,
            )

        # Database insertion with better error handling
        with session_scope() as session:
            try:
                session.add(video_object)
                session.commit()
                logger.info(
                    f"Video - {video['title']} from channel {channel} was successfully added."
                )
            except Exception as error:
                logger.error(
                    f"Failed to insert video {video['title']} into database: {error}"
                )
                safe_report_download_error(
                    "database_error",
                    str(error),
                    video["video_url"],
                    video.get("title"),
                    channel=channel,
                )
                # Cleanup downloaded files if database insertion fails
                if file_name and video_type_result not in ["livestream", "premiere"]:
                    cleanup_partial_download(file_name)
                raise

    except Exception as error:
        logger.error(
            f"Unexpected error in video_download_thread for {video.get('title', 'unknown')}: {error}"
        )
        safe_report_download_error(
            "unexpected_error",
            str(error),
            video.get("video_url"),
            video.get("title"),
            channel=channel,
        )
        # Cleanup any partial downloads
        if file_name:
            cleanup_partial_download(file_name)


@log_decorator
def confirm_video_name(filename):
    """Confirm video file exists and rename if necessary."""
    try:
        path = f"{DATA_FOLDER}/videos/{filename}.mp4"
        if os.path.exists(path):
            return True
        else:
            path_without_ext = path.split(".")[0]
            if os.path.exists(path_without_ext):
                os.rename(path_without_ext, path)
                return True
            return False
    except Exception as error:
        logger.error(f"Error confirming video name for {filename}: {error}")
        return False


@log_decorator
def download_thumbnail(url, filename) -> bool:
    """Download thumbnail with error handling and retries."""
    max_retries = 3
    retry_delay = 1

    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=30, stream=True)
            response.raise_for_status()

            thumbnail_path = f"{DATA_FOLDER}/thumbnails/{filename}"
            os.makedirs(os.path.dirname(thumbnail_path), exist_ok=True)

            with open(thumbnail_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Successfully downloaded thumbnail: {filename}")
            return True

        except requests.exceptions.RequestException as error:
            if attempt < max_retries - 1:
                logger.warning(
                    f"Failed to download thumbnail {filename} (attempt {attempt + 1}): {error}. Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error(
                    f"Failed to download thumbnail {filename} after {max_retries} attempts: {error}"
                )
                safe_report_download_error(
                    "thumbnail_download_failed",
                    str(error),
                    thumbnail_url=url,
                    filename=filename,
                )
                return False
        except Exception as error:
            logger.error(f"Unexpected error downloading thumbnail {filename}: {error}")
            safe_report_download_error(
                "thumbnail_error", str(error), thumbnail_url=url, filename=filename
            )
            return False

    return False


@log_decorator
def get_queue_size():
    return video_executor._work_queue.qsize()


@log_decorator
def download_old_livestreams():
    """
    Downloads old livestreams and their thumbnails and updates the database.

    This function retrieves a list of old livestreams from the database and downloads each one using the
    `livestream_download_thread` function. It also logs any errors that occur during the download process.

    :return: None
    """
    logger.info("Starting download of old livestreams...")
    old_livestreams = [x[0] for x in get_livestream_videos()]
    futures = []
    for livestream in old_livestreams:
        try:
            futures.append(
                video_executor.submit(livestream_download_thread, livestream)
            )
        except Exception as error:
            logger.error(
                f"Failed to download old livestream {livestream.vid_url}", error
            )
    for future in futures:
        future.result()
    logger.info("Download of old livestreams complete.")


@log_decorator
def livestream_download_thread(video):
    """
    Download a livestream and its thumbnail and update the database.

    :param video: A YoutubeVideo object containing all livestream data.
    :type video: YoutubeVideo
    """
    file_name = video.vid_url.split("=")[1]

    download_success, error_msg = download_video(video.vid_url, file_name)
    if not download_success:
        logger.error(f"Failed to download video {video.vid_url}: {error_msg}")
        cleanup_partial_download(file_name)
        return

    if not confirm_video_name(file_name):
        logger.error(f"Failed to confirm_video_name for video {video.vid_url}")
        cleanup_partial_download(file_name)
        return

    video.vid_path = f"{file_name}.mp4"
    video.thumb_path = f"{file_name}.jpg"

    if not download_thumbnail(video.thumb_url, video.thumb_path):
        logger.warning(f"Failed to download thumbnail for video {video.vid_url}")
        video.thumb_path = None

    size = get_video_size(video.vid_path)
    if size is None:
        logger.warning(f"Failed to get video size for {video.vid_url}, setting to 0")
        size = 0

    with session_scope() as session:
        try:
            # Update the video record in the database.
            session.query(YoutubeVideo).filter(YoutubeVideo.id == video.id).update(
                {
                    "vid_path": video.vid_path,
                    "thumb_path": video.thumb_path,
                    "downloaded_at": int(time.time()),
                    "size": size,
                }
            )
            session.commit()
            logger.info(f"Livestream - {video.title} was updated.")
        except Exception as error:
            logger.error(
                "Failed to update the Youtube Livestream",
                error,
            )


@log_decorator
def get_video_size(video_path) -> Optional[int]:
    """Get video duration in seconds with error handling."""
    try:
        full_path = f"{DATA_FOLDER}/videos/{video_path}"

        if not os.path.exists(full_path):
            logger.error(f"Video file not found: {full_path}")
            return None

        output = check_output(
            f"ffprobe '{full_path}' -show_format",
            shell=True,
            universal_newlines=True,
            stderr=DEVNULL,
            timeout=30,
        )

        duration_line = None
        for line in output.split("\n"):
            if line.startswith("duration="):
                duration_line = line
                break

        if duration_line:
            duration_str = duration_line.split("duration=")[1]
            return int(float(duration_str))
        else:
            logger.error(f"Could not find duration in ffprobe output for {video_path}")
            return None

    except Exception as error:
        logger.error(f"Failed to get video size for {video_path}: {error}")
        return None


@log_decorator
def download_video(url, filename) -> Tuple[bool, Optional[str]]:
    """
    Download video with comprehensive error handling and retry logic.

    Returns:
        Tuple[bool, Optional[str]]: (success, error_message)
    """
    user_agents = [
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.3",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.",
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Mobile Safari/537.3",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.2 Mobile/15E148 Safari/604.",
        "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Mobile Safari/537.3",
        "Mozilla/5.0 (Linux; Android 10; MAR-LX1A) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.0.0 Mobile Safari/537.3",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.3",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36 Edg/117.0.2045.6",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.3",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.",
    ]

    # Ensure output directory exists
    os.makedirs(f"{DATA_FOLDER}/videos", exist_ok=True)

    # Improved format selection with comprehensive fallbacks
    format_strings = [
        "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]",
        "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "best[height<=1080][ext=mp4]",
        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
        "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "best[height<=720]",
        "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "best[height<=480]",
        "best[ext=mp4]",
        "best",
        "worst"
    ]

    options = {
        "format": "/".join(format_strings),
        "outtmpl": f"{DATA_FOLDER}/videos/{filename}.mp4",
        "quiet": True,
        "overwrites": True,
        "noprogress": True,
        "socket_timeout": 60,
        "retries": 3,
        "fragment_retries": 3,
        "ignoreerrors": False,
        "no_warnings": False,
        "extractor_retries": 3,
    }

    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            # Record rate limiting request
            if MONITORING_AVAILABLE and hasattr(rate_limiter, 'record_request'):
                rate_limiter.record_request()

            # Randomize user agent for each attempt
            yt_dlp.utils.std_headers["User-Agent"] = random.choice(user_agents)

            with yt_dlp.YoutubeDL(options) as ydl:
                result = ydl.download([url])

                if result == 0:  # Success
                    logger.info(f"Successfully downloaded video: {filename}")
                    if MONITORING_AVAILABLE and hasattr(rate_limiter, 'record_success'):
                        rate_limiter.record_success()
                    return True, None
                else:
                    error_msg = f"yt-dlp returned non-zero exit code: {result}"
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"{error_msg} (attempt {attempt + 1}). Retrying in {retry_delay}s..."
                        )
                        time.sleep(retry_delay)
                        retry_delay *= 2
                    else:
                        logger.error(
                            f"Failed to download {filename} after {max_retries} attempts: {error_msg}"
                        )
                        return False, error_msg

        except UnavailableVideoError as error:
            error_msg = f"Video unavailable: {error}"
            logger.error(f"Video {filename} is unavailable: {error}")
            return False, error_msg

        except ExtractorError as error:
            error_msg = f"Extractor error: {error}"
            if "Private video" in str(error) or "removed" in str(error).lower():
                logger.error(f"Video {filename} is private or removed: {error}")
                return False, error_msg
            elif attempt < max_retries - 1:
                logger.warning(
                    f"Extractor error for {filename} (attempt {attempt + 1}): {error}. Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error(
                    f"Extractor error for {filename} after {max_retries} attempts: {error}"
                )
                return False, error_msg

        except DownloadError as error:
            error_msg = f"Download error: {error}"
            if "HTTP Error 429" in str(error):
                # Rate limited
                if MONITORING_AVAILABLE and hasattr(rate_limiter, 'record_failure'):
                    rate_limiter.record_failure(is_rate_limit_error=True)
                if attempt < max_retries - 1:
                    wait_time = retry_delay * 3  # Longer wait for rate limiting
                    logger.warning(
                        f"Rate limited for {filename} (attempt {attempt + 1}): {error}. Waiting {wait_time}s..."
                    )
                    time.sleep(wait_time)
                    retry_delay *= 2
                else:
                    logger.error(
                        f"Rate limited for {filename} after {max_retries} attempts: {error}"
                    )
                    return False, error_msg
            elif attempt < max_retries - 1:
                if MONITORING_AVAILABLE and hasattr(rate_limiter, 'record_failure'):
                    rate_limiter.record_failure()
                logger.warning(
                    f"Download error for {filename} (attempt {attempt + 1}): {error}. Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                if MONITORING_AVAILABLE and hasattr(rate_limiter, 'record_failure'):
                    rate_limiter.record_failure()
                logger.error(
                    f"Download error for {filename} after {max_retries} attempts: {error}"
                )
                return False, error_msg

        except Exception as error:
            error_msg = f"Unexpected error: {error}"
            if MONITORING_AVAILABLE and hasattr(rate_limiter, 'record_failure'):
                rate_limiter.record_failure()
            if attempt < max_retries - 1:
                logger.warning(
                    f"Unexpected error for {filename} (attempt {attempt + 1}): {error}. Retrying in {retry_delay}s..."
                )
                time.sleep(retry_delay)
                retry_delay *= 2
            else:
                logger.error(
                    f"Unexpected error for {filename} after {max_retries} attempts: {error}"
                )
                return False, error_msg

    return False, "Max retries exceeded"


@log_decorator
def download_and_keep(video_id):
    """
    Download an old video and keep it forever.

    :param video_id: A video_id for a YoutubeVideo
    :type video_id: str
    """

    video = get_video_by_id(video_id)[0]
    is_missing = video.vid_path == "NA"

    file_name = video.vid_url.split("=")[1]

    if is_missing:
        # Check disk space before downloading
        if not check_disk_space():
            logger.error(f"Insufficient disk space to download video {video.vid_url}")
            safe_report_download_error(
                "disk_space",
                "Insufficient disk space for download_and_keep",
                video.vid_url,
                video.title,
            )
            return

        download_success, error_msg = download_video(video.vid_url, file_name)
        if not download_success:
            logger.error(f"Failed to download video {video.vid_url}: {error_msg}")
            safe_report_download_error(
                "download_failed", error_msg, video.vid_url, video.title
            )
            cleanup_partial_download(file_name)
            return

        if not confirm_video_name(file_name):
            logger.error(f"Failed to confirm_video_name for video {video.vid_url}")
            safe_report_download_error(
                "file_verification_failed",
                f"Downloaded file not found: {file_name}",
                video.vid_url,
                video.title,
            )
            cleanup_partial_download(file_name)
            return

        video.vid_path = f"{file_name}.mp4"
        video.thumb_path = f"{file_name}.jpg"

        if not download_thumbnail(video.thumb_url, video.thumb_path):
            logger.warning(f"Failed to download thumbnail for video {video.vid_url}")
            video.thumb_path = None

        size = get_video_size(video.vid_path)
        if size is None:
            logger.warning(
                f"Failed to get video size for {video.vid_url}, setting to 0"
            )
            size = 0

    with session_scope() as session:
        try:
            session.query(YoutubeVideo).filter(YoutubeVideo.id == video.id).update(
                {
                    "vid_path": video.vid_path,
                    "thumb_path": video.thumb_path,
                    "downloaded_at": (
                        int(time.time()) if is_missing else video.downloaded_at
                    ),
                    "size": size if is_missing else video.size,
                    "keep": True,
                }
            )
            session.commit()
            logger.info(f"Video - {video.title} was updated and will be kept")
        except Exception as error:
            logger.error(
                "Failed to update the video",
                error,
            )


@log_decorator
def unkeep(video_id):
    with session_scope() as session:
        try:
            session.query(YoutubeVideo).filter(YoutubeVideo.id == video_id).update(
                {"keep": False}
            )
            session.commit()
            logger.info(f"Video - {video_id} was unkept")
        except Exception as error:
            logger.error(
                "Failed to update the video",
                error,
            )


def preview_channel_info(channel_input):
    """
    Preview channel information using yt-dlp and RSS feeds without adding it.

    :param channel_input: Channel URL, channel ID, or channel name
    :type channel_input: str
    :return: A dictionary containing channel information or error
    :rtype: dict
    """
    try:
        # Handle different input formats
        if channel_input.startswith("UC") and len(channel_input) == 24:
            # It's a channel ID
            channel_url = f"https://www.youtube.com/channel/{channel_input}"
        elif channel_input.startswith("http"):
            # It's a URL
            channel_url = channel_input
        else:
            # Try as username/handle
            if channel_input.startswith("@"):
                channel_url = f"https://www.youtube.com/{channel_input}"
            else:
                channel_url = f"https://www.youtube.com/c/{channel_input}"

        # Extract basic channel info using yt-dlp
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(channel_url, download=False)

                if not info:
                    return {
                        "success": False,
                        "error": "Could not find channel information. Please check the channel URL/ID and try again.",
                    }

                # Safely extract channel information
                channel_name = "Unknown"
                if isinstance(info, dict):
                    if "title" in info and info["title"]:
                        channel_name = str(info["title"])
                    elif "uploader" in info and info["uploader"]:
                        channel_name = str(info["uploader"])

                channel_id = ""
                if (
                    isinstance(info, dict)
                    and "channel_id" in info
                    and info["channel_id"]
                ):
                    channel_id = str(info["channel_id"])

                channel_info = {
                    "channel_name": channel_name,
                    "channel_id": channel_id,
                    "channel_url": (
                        str(info.get("channel_url", channel_url))
                        if isinstance(info, dict)
                        else channel_url
                    ),
                    "subscriber_count": (
                        int(info.get("subscriber_count", 0))
                        if isinstance(info, dict) and info.get("subscriber_count")
                        else 0
                    ),
                    "video_count": (
                        int(info.get("video_count", 0))
                        if isinstance(info, dict) and info.get("video_count")
                        else 0
                    ),
                    "description": (
                        str(info.get("description", ""))
                        if isinstance(info, dict) and info.get("description")
                        else ""
                    ),
                    "thumbnail": (
                        str(info.get("thumbnail", ""))
                        if isinstance(info, dict) and info.get("thumbnail")
                        else ""
                    ),
                    "feed_url": (
                        f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
                        if channel_id
                        else None
                    ),
                }

                # Try to get recent videos from RSS feed if we have channel_id
                if channel_id:
                    try:
                        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
                        video_feed = feedparser.parse(feed_url)

                        if hasattr(video_feed, "entries") and video_feed.entries:
                            recent_videos = []
                            for entry in video_feed.entries[
                                :3
                            ]:  # Get 3 most recent videos
                                recent_videos.append(
                                    {
                                        "title": (
                                            entry.get("title", "")
                                            if hasattr(entry, "get")
                                            else ""
                                        ),
                                        "published": (
                                            entry.get("published", "")
                                            if hasattr(entry, "get")
                                            else ""
                                        ),
                                        "link": (
                                            entry.get("link", "")
                                            if hasattr(entry, "get")
                                            else ""
                                        ),
                                    }
                                )
                            channel_info["recent_videos"] = recent_videos
                            channel_info["feed_working"] = True
                        else:
                            channel_info["recent_videos"] = []
                            channel_info["feed_working"] = False
                    except Exception as e:
                        logger.warning(f"Could not fetch RSS feed for channel: {e}")
                        channel_info["recent_videos"] = []
                        channel_info["feed_working"] = False
                else:
                    channel_info["recent_videos"] = []
                    channel_info["feed_working"] = False

                return {"success": True, "channel_info": channel_info}

            except Exception as e:
                logger.error(f"Failed to extract channel info: {e}")
                return {
                    "success": False,
                    "error": "Could not find channel information. Please check the channel URL/ID and try again.",
                }

    except Exception as e:
        logger.error(f"Error in preview_channel_info: {e}")
        return {
            "success": False,
            "error": "An error occurred while fetching channel information.",
        }
