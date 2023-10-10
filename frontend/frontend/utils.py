import datetime
import threading

import feedparser
import opml
import requests
from pydantic import BaseModel

from frontend.env_vars import BACKEND_PORT, BACKEND_URL, DATA_FOLDER


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


def prepare_for_template(video):
    return {
        "id": video.id,
        "vid_url": video.vid_url,
        "thumb_url": video.thumb_url,
        "vid_path": video.vid_path,
        "thumb_path": video.thumb_path,
        "pub_date": video.pub_date,
        "pub_date_human": video.pub_date_human,
        "title": video.title,
        "views": place_value(video.views),
        "description": video.description,
        "channel": video.channel,
        "progress_percentage": progress_percentage(video),
        "size": format_video_size(video),
    }
