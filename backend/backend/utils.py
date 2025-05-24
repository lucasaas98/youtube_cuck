import functools
import json
import logging as _logging
import os
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from subprocess import DEVNULL, check_output
from time import time

import dateutil.parser as date_parser
import feedparser
import opml
import requests
import yt_dlp
from yt_dlp.utils import DownloadError

from backend.constants import DELAY, REMOVAL_DELAY
from backend.engine import session_scope
from backend.env_vars import DATA_FOLDER
from backend.logging import logging
from backend.models import YoutubeVideo
from backend.repo import (
    expire_video,
    get_all_videos,
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
    min_pub_date = time() - REMOVAL_DELAY
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
        min_date = time() - DELAY
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
                futures.append(
                    video_executor.submit(video_download_thread, video, channel)
                )

        for future in futures:
            future.result()

    except Exception as error:
        logger.error("Failed to get new videos", error)
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
        tuple: A tuple containing a boolean indicating whether the extraction was successful and the extracted video information.
               If the extraction was unsuccessful, the boolean value will be False and the video information will be None.
    """
    options = {}

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            video_info = ydl.extract_info(video_url, download=False)
            return video_info
    except DownloadError as error:
        logger.error(f"Failed to extract video info for {video_url}", error)
        return None


@log_decorator
def video_download_thread(video, channel):
    """
    Download a video and its thumbnail based on the video type and update the database.

    :param video: A dictionary containing the video data.
    :type video: dict
    :param channel: The name of the YouTube channel.
    :type channel: str
    """
    try:
        video_info = extract_video_info(video["video_url"])

        type = video_type(video_info)

        video_object = None

        if type in ["livestream", "premiere"]:
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
                inserted_at=int(time()),
            )
        else:
            file_name = video["video_url"].split("=")[1]

            download_video(video["video_url"], file_name)

            now = int(time())

            if not confirm_video_name(file_name):
                return

            vid_path = f"{file_name}.mp4"
            thumb_path = f"{file_name}.jpg"

            download_thumbnail(video["thumbnail"], thumb_path)

            size = get_video_size(vid_path)

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
                short=type == "short",
                inserted_at=now,
                downloaded_at=now,
                size=size,
            )

        with session_scope() as session:
            try:
                session.add(video_object)
                session.commit()
                logger.info(
                    f"Video - {video['title']} from channel {channel} was added."
                )
            except Exception as error:
                logger.error(
                    "Failed to insert the Youtube video into the YoutubeVideo table",
                    error,
                )
    except Exception as error:
        logger.error(
            "Failed at some point in the video_download_thread function", error
        )


@log_decorator
def confirm_video_name(filename):
    path = f"{DATA_FOLDER}/videos/{filename}.mp4"
    if os.path.exists(path):
        return True
    else:
        path = path.split(".")[0]
        if os.path.exists(path):
            os.rename(path, path + ".mp4")
            return True
        return False


@log_decorator
def download_thumbnail(url, filename):
    r = requests.get(url)
    with open(f"{DATA_FOLDER}/thumbnails/{filename}", "wb") as f:
        f.write(r.content)


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

    if download_video(video.vid_url, file_name) != 0:
        logger.error(f"YT_DLP Failed to download_video for video {video.vid_url}")
        return

    if not confirm_video_name(file_name):
        logger.error(f"Failed to confirm_video_name for video {video.vid_url}")
        return

    video.vid_path = f"{file_name}.mp4"
    video.thumb_path = f"{file_name}.jpg"

    download_thumbnail(video.thumb_url, video.thumb_path)
    size = get_video_size(video.vid_path)

    with session_scope() as session:
        try:
            # Update the video record in the database.
            session.query(YoutubeVideo).filter(YoutubeVideo.id == video.id).update(
                {
                    "vid_path": video.vid_path,
                    "thumb_path": video.thumb_path,
                    "downloaded_at": int(time()),
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


# @log_decorator
# def update_size_for_old_videos():
#     """
#     TEMP: because we added the size column to the database, we need to update the size column for all videos
#     """
#     logger.info("Updating size for old videos")
#     all_videos = get_all_videos()
#     for video in [x[0] for x in all_videos]:
#         try:
#             video_size = get_video_size(video.vid_path)
#             with session_scope() as session:
#                 session.query(YoutubeVideo).filter(YoutubeVideo.id == video.id).update(
#                     {"size": video_size}
#                 )
#                 session.commit()
#             logger.info(f"Video size for {video.title} was updated with {video_size}s")
#         except Exception as error:
#             logger.error(
#                 f"Failed to update size for video {video.title} at path {video.vid_path}",
#                 error,
#             )


@log_decorator
def get_video_size(video_path):
    output = check_output(
        f"ffprobe {DATA_FOLDER}/videos/{video_path} -show_format",
        shell=True,
        universal_newlines=True,
        stderr=DEVNULL,
    )

    return int(float(output.split("duration=")[1].split("\n")[0]))


@log_decorator
def download_video(url, filename):
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

    options = {
        "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]",
        "outtmpl": f"{DATA_FOLDER}/videos/{filename}.mp4",
        "quiet": True,
        "overwrites": True,
        "noprogress": True,
    }

    yt_dlp.utils.std_headers["User-Agent"] = random.choice(user_agents)

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            return ydl.download([url])
    except yt_dlp.utils.ExtractorError as error:
        logger.error("Video got fucking deleted, wtfffff", error)
    except Exception as error:
        logger.error(
            f"Failed to fetch new video {filename} at {url} with yt-dlp", error
        )


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
        if download_video(video.vid_url, file_name) != 0:
            logger.error(f"YT_DLP Failed to download_video for video {video.vid_url}")
            return

        if not confirm_video_name(file_name):
            logger.error(f"Failed to confirm_video_name for video {video.vid_url}")
            return

        video.vid_path = f"{file_name}.mp4"
        video.thumb_path = f"{file_name}.jpg"

        download_thumbnail(video.thumb_url, video.thumb_path)
        size = get_video_size(video.vid_path)

    with session_scope() as session:
        try:
            session.query(YoutubeVideo).filter(YoutubeVideo.id == video.id).update(
                {
                    "vid_path": video.vid_path,
                    "thumb_path": video.thumb_path,
                    "downloaded_at": int(time()) if is_missing else video.downloaded_at,
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
