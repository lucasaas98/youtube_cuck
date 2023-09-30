import json
import logging as _logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from subprocess import PIPE, Popen
from time import time

import dateutil.parser as date_parser
import feedparser
import opml
import requests
import yt_dlp
from yt_dlp.utils import DownloadError

from .constants import DELAY, REMOVAL_DELAY
from .engine import session_scope
from .logging import logging
from .models import YoutubeVideo
from .repo import (
    expire_video,
    get_expired_videos,
    get_json,
    update_json,
    update_rss_date,
    update_view_count,
    get_downloaded_video_urls
)
from .env_vars import DATA_FOLDER


logger = logging.getLogger(__name__)
logger.setLevel(_logging.INFO)

video_executor = ThreadPoolExecutor(max_workers=4)
update_count_executor = ThreadPoolExecutor(max_workers=32)


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

        except:
            logger.error(f"Failed to delete video at path: {file_path}")

        try:
            thumb_path = os.path.join(f"{DATA_FOLDER}/thumbnails", expired_video.thumb_path)
            os.remove(thumb_path)
            logger.info(f"Delete thumbnail at path: {thumb_path}")
        except:
            logger.error(f"Failed to delete thumbnail at path: {thumb_path}")

        expire_video(expired_video.id)


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
                    futures.append(update_count_executor.submit(update_view_count, video))
                    continue
                if float(video["epoch_date"]) < min_date:
                    continue
                futures.append(
                    video_executor.submit(video_download_thread, video, channel)
                )

        for future in futures:
            future.result()

    except Exception as error:
        logger.error(f"Failed to get new videos", error)
    finally:
        logger.info("Videos Downloaded!")

def video_type(video_url):
    """
    Determine the type of a video (livestream, premiere, short, or regular video).

    :param video_url: The URL of the video.
    :type video_url: str
    :return: The type of the video as a string.
    :rtype: str
    """
    ydl_opts = {}
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            video_info = ydl.extract_info(video_url, download=False)
    except DownloadError as error:
        logger.error(f"Failed to get new videos", error)
        return "premiere"
    
    if video_info['is_live']:
        return "livestream"
    elif video_info['duration'] is not None and video_info['duration'] < 62:
        return "short"
    else:
        return "regular video"


def video_download_thread(video, channel):
    """
    Download a video and its thumbnail based on the video type and update the database.

    :param video: A dictionary containing the video data.
    :type video: dict
    :param channel: The name of the YouTube channel.
    :type channel: str
    """
    try:
        type = video_type(video["video_url"])

        video_object = None
        if type in ['livestream', 'premiere']:
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
                        inserted_at=int(time())
                    )
        else:
            file_name = video["video_url"].split("=")[1]

            download_video(video["video_url"], file_name)
            
            if not confirm_video_name(file_name):
                
                return
        
            download_thumbnail(video["thumbnail"], file_name)

            video_object = YoutubeVideo(
                        vid_url=video["video_url"],
                        vid_path=f"{file_name}.mp4",
                        thumb_url=video["thumbnail"],
                        thumb_path=f"{file_name}.jpg",
                        pub_date=int(video["epoch_date"]),
                        pub_date_human=video["human_date"],
                        title=video["title"],
                        views=int(video["views"]),
                        description=video["description"],
                        channel=channel,
                        livestream=False,
                        short=type=='short',
                        inserted_at=int(time())
                    )

        with session_scope() as session:
            try:
                session.add(video_object)
                session.commit()
                logger.info(f"Video - {video['title']} from channel {channel} was added.")
            except Exception as error:
                logger.error(
                    "Failed to insert the Youtube video into the YoutubeVideo table", error
                )
    except Exception as error:
        logger.error(
                    "Failed at some point in the video_download_thread function", error
                )


def download_video(url, filename):
    try:
        p = Popen(
            [
                f"yt-dlp -f 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]mp4' --fixup force {url} -o {DATA_FOLDER}/videos/{filename}.mp4"
            ],
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
        )
        _output, _err = p.communicate()
        return p.returncode
    except Exception as error:
        logger.error(
            f"Failed to fetch new video {filename} at {url} with yt-dlp", error
        )


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


def download_thumbnail(url, filename):
    r = requests.get(url)
    with open(f"{DATA_FOLDER}/thumbnails/{filename}.jpg", "wb") as f:
        f.write(r.content)


def get_queue_size():
    return video_executor._work_queue.qsize()
