import threading

import feedparser
import opml
import requests
import uvicorn
from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing_extensions import Annotated
from frontend.cache import (
    cache_videos,
    fetch_video_from_cache,
    is_video_cached,
)

from frontend.env_vars import BACKEND_PORT, BACKEND_URL, DATA_FOLDER, PORT
from frontend.repo import (
    get_channel_videos,
    get_recent_shorts,
    get_recent_videos,
    get_rss_date,
    get_video_by_id,
    update_video_progress,
)

app = FastAPI()

templates = Jinja2Templates(directory="frontend/templates")
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    data = get_recent_videos(0, True)
    rss_date = get_rss_date()
    (queue_size, queue_fetching) = get_queue_size()

    data = (
        [
            {
                "id": youtube_video.id,
                "vid_url": youtube_video.vid_url,
                "thumb_url": youtube_video.thumb_url,
                "vid_path": youtube_video.vid_path,
                "thumb_path": youtube_video.thumb_path,
                "pub_date": youtube_video.pub_date,
                "pub_date_human": youtube_video.pub_date_human,
                "rating": None,
                "title": youtube_video.title,
                "views": place_value(youtube_video.views),
                "description": youtube_video.description,
                "channel": youtube_video.channel,
            }
            for youtube_video in data
        ],
        0,
        rss_date.date_human,
        queue_size,
        queue_fetching,
    )
    return templates.TemplateResponse(
        "yt_cuck.html", {"request": request, "data": data, "is_short": False}
    )


@app.get("/shorts", response_class=HTMLResponse)
async def get_shorts(request: Request):
    data = get_recent_shorts(0)
    rss_date = get_rss_date()
    (queue_size, queue_fetching) = get_queue_size()

    data = (
        [
            {
                "id": youtube_video.id,
                "vid_url": youtube_video.vid_url,
                "thumb_url": youtube_video.thumb_url,
                "vid_path": youtube_video.vid_path,
                "thumb_path": youtube_video.thumb_path,
                "pub_date": youtube_video.pub_date,
                "pub_date_human": youtube_video.pub_date_human,
                "rating": None,
                "title": youtube_video.title,
                "views": place_value(youtube_video.views),
                "description": youtube_video.description,
                "channel": youtube_video.channel,
            }
            for youtube_video in data
        ],
        0,
        rss_date.date_human,
        queue_size,
        queue_fetching,
    )
    return templates.TemplateResponse(
        "yt_cuck.html", {"request": request, "data": data, "is_short": True}
    )


@app.get("/page/{page}", response_class=HTMLResponse)
async def next_page(page, request: Request):
    videos = get_recent_videos(page, True)
    rss_date = get_rss_date()
    (queue_size, queue_fetching) = get_queue_size()

    data = (
        [
            {
                "id": youtube_video.id,
                "vid_url": youtube_video.vid_url,
                "thumb_url": youtube_video.thumb_url,
                "vid_path": youtube_video.vid_path,
                "thumb_path": youtube_video.thumb_path,
                "pub_date": youtube_video.pub_date,
                "pub_date_human": youtube_video.pub_date_human,
                "rating": None,
                "title": youtube_video.title,
                "views": place_value(youtube_video.views),
                "description": youtube_video.description,
                "channel": youtube_video.channel,
            }
            for youtube_video in videos
        ],
        int(page),
        rss_date.date_human,
        queue_size,
        queue_fetching,
    )
    return templates.TemplateResponse(
        "yt_cuck_page.html", {"request": request, "data": data}
    )


@app.get("/video/{identifier}", response_class=HTMLResponse)
async def video_watch(request: Request, identifier: str):
    youtube_video = get_video_by_id(identifier)
    file_url = f"../videos/{youtube_video.vid_path}"

    if is_video_cached(int(identifier)):
        file_url = f"../cached-video/{identifier}"

    data = {
        "title": youtube_video.title,
        "views": place_value(youtube_video.views),
        "rating": None,
        "file_url": file_url,
        "channel_name": youtube_video.channel,
        "date": youtube_video.pub_date_human,
        "description": youtube_video.description.split("\n"),
        "id": youtube_video.id,
        "progress": youtube_video.progress_seconds or 0,
    }
    return templates.TemplateResponse(
        "cuck_video.html",
        {"request": request, "data": data, "length": len(data["description"])},
    )


@app.get("/cached-video/{identifier}")
async def serve_video(identifier: str):
    video = fetch_video_from_cache(int(identifier))
    return StreamingResponse(video)


@app.get("/channel/{channel_name}", response_class=HTMLResponse)
async def channel_video_watch(request: Request, channel_name: str):
    data = get_channel_videos(channel_name)
    data = [
        channel_name,
        [
            {
                "id": youtube_video.id,
                "vid_url": youtube_video.vid_url,
                "thumb_url": youtube_video.thumb_url,
                "vid_path": youtube_video.vid_path,
                "thumb_path": youtube_video.thumb_path,
                "pub_date": youtube_video.pub_date,
                "pub_date_human": youtube_video.pub_date_human,
                "rating": None,
                "title": youtube_video.title,
                "views": place_value(youtube_video.views),
                "description": youtube_video.description,
                "channel": youtube_video.channel,
            }
            for youtube_video in data
        ],
    ]
    return templates.TemplateResponse(
        "cuck_channel.html", {"request": request, "data": data}
    )


@app.get("/subs", response_class=HTMLResponse)
async def get_subs(request: Request):
    data = get_all_channels()
    sorted_by_lowercase_name = [
        {"title": x[0], "id": x[1]}
        for x in sorted(data, key=lambda tup: tup[0].strip().lower())
    ]
    return templates.TemplateResponse(
        "cuck_subs.html", {"request": request, "data": sorted_by_lowercase_name}
    )


@app.post("/add", status_code=200)
async def add_channel(
    channel_name: Annotated[str, Form()],
    channel_id: Annotated[str, Form()],
    response: Response,
):
    feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    if is_valid_url(feed_url):
        fi = open(f"{DATA_FOLDER}/subscription_manager", "r")
        sub_data = fi.readlines()
        fi.close()
        fo = open(f"{DATA_FOLDER}/subscription_manager", "w")
        data = sub_data[0]
        data += sub_data[1].split("</outline></body></opml>")[0]
        data += f'<outline text="{channel_name}" title="{channel_name}" type="rss" xmlUrl="{feed_url}" />'
        data += "</outline></body></opml>"
        fo.write(data)
        fo.close()
        return {"text": "Channel added!"}
    else:
        response.status_code = 400
        return {
            "text": "There was an error adding that channel, make sure the channel ID is correct."
        }


@app.post("/refresh_rss", status_code=200)
async def refresh_rss():
    get_rss_feed()
    return {"text": "True"}


class Progress(BaseModel):
    time: float
    id: str


@app.post("/save_progress")
async def save_progress(progress: Progress):
    update_video_progress(progress.id, progress.time)
    return {"message": "Progress updated"}


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


@app.on_event("startup")
async def ready_up_server():
    t1 = threading.Thread(target=ready_up_request)
    t1.start()
    # start caching videos
    cache_videos(20)


if __name__ == "__main__":
    uvicorn.run("server:app", port=PORT, reload=True)
