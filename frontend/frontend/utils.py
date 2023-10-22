import datetime
import logging as _logging
import threading

import feedparser
import opml
import requests
from pydantic import BaseModel

from frontend.env_vars import BACKEND_PORT, BACKEND_URL, DATA_FOLDER
from frontend.logging import logging

logger = logging.getLogger(__name__)
logger.setLevel(_logging.INFO)


class Progress(BaseModel):
    time: float
    id: str


def get_rss_feed():
    t1 = threading.Thread(target=send_request_rss)
    t1.start()
    return True, t1


def send_request_rss():
    return requests.post(f"http://{BACKEND_URL}:{BACKEND_PORT}/api/refresh_rss")


def ready_up_request():
    return requests.post(f"http://{BACKEND_URL}:{BACKEND_PORT}/api/startup")


def keep_video_request(video_id):
    return requests.get(
        f"http://{BACKEND_URL}:{BACKEND_PORT}/api/fetch_and_keep/{video_id}"
    )


def unkeep_video_request(video_id):
    return requests.get(f"http://{BACKEND_URL}:{BACKEND_PORT}/api/unkeep/{video_id}")


def get_queue_size():
    data = requests.get(
        f"http://{BACKEND_URL}:{BACKEND_PORT}/api/working_threads"
    ).json()
    return (data["size"], data["still_fetching"])


def place_value(number):
    return "{:,}".format(number)


def get_all_channels():
    data = open(f"{DATA_FOLDER}/subscription_manager", "r")

    nested = opml.parse(data)

    all_channels = list()
    for channel in nested[0]:
        real_id = channel.xmlUrl.split("=")[1]
        all_channels.append((channel.title, real_id))
    return all_channels


def is_valid_url(feed_url):
    video_feed = None
    video_feed = feedparser.parse(feed_url)
    if video_feed["status"] == 200:
        return True
    else:
        return False


def progress_percentage(video):
    return (
        (video.progress_seconds / video.size * 100)
        if video.progress_seconds and video.size
        else 0
    )


def format_video_size(video):
    return str(datetime.timedelta(seconds=video.size)) if video.size else ""


def prepare_for_template(video, main_page=False):
    is_live_without_video = video.vid_path == "NA" and video.livestream

    prefix = "../" if not main_page else ""

    vid_thumb_path = video.thumb_path if video.thumb_path else "NA"

    thumb_path = (
        "thumbnails/" + vid_thumb_path
        if not is_live_without_video
        else "static/livestream-coming.png"
    )
    thumb_path = prefix + thumb_path

    return {
        "id": video.id,
        "vid_url": video.vid_url,
        "thumb_url": video.thumb_url,
        "thumb_path": thumb_path,
        "pub_date_human": video.pub_date_human,
        "title": video.title,
        "views": place_value(video.views),
        "description": video.description,
        "channel": video.channel,
        "progress_percentage": progress_percentage(video),
        "size": format_video_size(video),
    }


def prepare_for_watch(video):
    is_live_without_video = video.vid_path == "NA" and video.livestream

    vid_path = (
        "../videos/" + video.vid_path
        if not is_live_without_video and video.vid_path
        else "../static/dQw4w9WgXcQ.mp4"
    )

    return {
        "title": video.title,
        "views": place_value(video.views),
        "vid_path": vid_path,
        "channel_name": video.channel,
        "date": video.pub_date_human,
        "description": video.description.split("\n"),
        "id": video.id,
        "progress": video.progress_seconds or 0,
        "player_width": "25" if video.short else "80",
        "keep": video.keep,
        "video_id": video.id,
    }
