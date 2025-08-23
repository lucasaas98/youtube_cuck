import datetime
import functools
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


def log_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger.info(f"Entering function {func.__name__}")
        result = func(*args, **kwargs)
        logger.info(f"Exiting function {func.__name__}")
        return result

    return wrapper


class Progress(BaseModel):
    time: float
    id: str


@log_decorator
def get_rss_feed():
    t1 = threading.Thread(target=send_request_rss)
    t1.start()
    return True, t1


@log_decorator
def send_request_rss():
    return requests.post(f"http://{BACKEND_URL}:{BACKEND_PORT}/api/refresh_rss")


@log_decorator
def ready_up_request():
    return requests.post(f"http://{BACKEND_URL}:{BACKEND_PORT}/api/startup")


@log_decorator
def keep_video_request(video_id):
    return requests.get(
        f"http://{BACKEND_URL}:{BACKEND_PORT}/api/fetch_and_keep/{video_id}"
    )


@log_decorator
def unkeep_video_request(video_id):
    return requests.get(f"http://{BACKEND_URL}:{BACKEND_PORT}/api/unkeep/{video_id}")


@log_decorator
def get_queue_size():
    data = requests.get(
        f"http://{BACKEND_URL}:{BACKEND_PORT}/api/working_threads"
    ).json()
    return (data["size"], data["still_fetching"])


@log_decorator
def place_value(number):
    return "{:,}".format(number)


@log_decorator
def get_all_channels():
    data = open(f"{DATA_FOLDER}/subscription_manager", "r")

    nested = opml.parse(data)

    all_channels = list()
    for channel in nested[0]:
        real_id = channel.xmlUrl.split("=")[1]
        all_channels.append((channel.title, real_id))
    return all_channels


@log_decorator
def is_valid_url(feed_url):
    video_feed = None
    video_feed = feedparser.parse(feed_url)
    if video_feed["status"] == 200:
        return True
    else:
        return False


@log_decorator
def progress_percentage(video):
    return (
        (video.progress_seconds / video.size * 100)
        if video.progress_seconds and video.size
        else 0
    )


@log_decorator
def format_video_size(video):
    return str(datetime.timedelta(seconds=video.size)) if video.size else ""


@log_decorator
def prepare_for_template(video, main_page=False):
    is_live_without_video = video.vid_path == "NA" and video.livestream

    vid_thumb_path = video.thumb_path if video.thumb_path else "NA"

    thumb_path = (
        "/thumbnails/" + vid_thumb_path
        if not is_live_without_video
        else "/static/livestream-coming.png"
    )

    return {
        "id": video.id,
        "vid_url": video.vid_url,
        "vid_path": video.vid_path,
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


@log_decorator
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
        "is_short": video.short,
        "keep": video.keep,
        "video_id": video.id,
    }


class PaginationInfo(BaseModel):
    current_page: int
    total_pages: int
    total_items: int
    items_per_page: int
    has_prev: bool
    has_next: bool
    prev_page: int | None = None
    next_page: int | None = None


@log_decorator
def calculate_pagination(
    current_page: int, total_items: int, items_per_page: int = 35
) -> PaginationInfo:
    """Calculate pagination metadata"""
    total_pages = max(1, (total_items + items_per_page - 1) // items_per_page)
    current_page = max(0, min(current_page, total_pages - 1))

    has_prev = current_page > 0
    has_next = current_page < total_pages - 1
    prev_page = current_page - 1 if has_prev else None
    next_page = current_page + 1 if has_next else None

    return PaginationInfo(
        current_page=current_page,
        total_pages=total_pages,
        total_items=total_items,
        items_per_page=items_per_page,
        has_prev=has_prev,
        has_next=has_next,
        prev_page=prev_page,
        next_page=next_page,
    )


@log_decorator
def get_pagination_range(
    current_page: int, total_pages: int, max_links: int = 5
) -> list:
    """Get a range of page numbers to display in pagination"""
    if total_pages <= max_links:
        return list(range(total_pages))

    # Calculate start and end of range
    half_links = max_links // 2
    start = max(0, current_page - half_links)
    end = min(total_pages, start + max_links)

    # Adjust start if we're near the end
    if end - start < max_links:
        start = max(0, end - max_links)

    return list(range(start, end))


@log_decorator
def preview_channel_info_frontend(channel_input):
    """
    Preview channel information by calling the backend API.

    :param channel_input: Channel URL, channel ID, or channel name
    :type channel_input: str
    :return: A dictionary containing channel information or error
    :rtype: dict
    """
    try:
        response = requests.post(
            f"http://{BACKEND_URL}:{BACKEND_PORT}/api/preview_channel",
            params={"channel_input": channel_input},
        )

        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json()
            return {
                "success": False,
                "error": error_data.get("error", "Unknown error occurred"),
            }
    except Exception as e:
        logger.error(f"Error previewing channel: {e}")
        return {"success": False, "error": "Failed to connect to backend service"}
