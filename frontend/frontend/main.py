import threading

import uvicorn
from fastapi import FastAPI, Form, Request, Response
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing_extensions import Annotated
import os

from frontend.env_vars import DATA_FOLDER, PORT
from frontend.repo import (
    add_video_to_playlist,
    create_playlist,
    delete_playlist,
    get_all_playlists,
    get_channel_videos,
    get_playlist_by_name,
    get_playlist_videos,
    get_recent_shorts,
    get_recent_videos,
    get_rss_date,
    get_video_by_id,
    most_recent_video,
    most_recent_videos,
    remove_video_from_playlist,
    update_video_progress,
)
from frontend.utils import (
    Progress,
    get_all_channels,
    get_queue_size,
    get_rss_feed,
    is_valid_url,
    keep_video_request,
    log_decorator,
    prepare_for_template,
    prepare_for_watch,
    ready_up_request,
    unkeep_video_request,
)

app = FastAPI()

templates = Jinja2Templates(directory="frontend/templates")
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


@log_decorator
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    data = get_recent_videos(0)
    rss_date = get_rss_date()
    (queue_size, queue_fetching) = get_queue_size()

    data = (
        [prepare_for_template(youtube_video, True) for youtube_video in data],
        0,
        rss_date.date_human,
        queue_size,
        queue_fetching,
    )

    return templates.TemplateResponse(
        "yt_cuck.html", {"request": request, "data": data, "is_short": False}
    )


@log_decorator
@app.get("/shorts", response_class=HTMLResponse)
async def get_shorts(request: Request):
    data = get_recent_shorts(0)
    rss_date = get_rss_date()
    (queue_size, queue_fetching) = get_queue_size()

    data = (
        [prepare_for_template(video) for video in data],
        0,
        rss_date.date_human,
        queue_size,
        queue_fetching,
    )

    return templates.TemplateResponse(
        "yt_cuck.html", {"request": request, "data": data, "is_short": True}
    )


@log_decorator
@app.get("/page/{page}", response_class=HTMLResponse)
async def next_page(page, request: Request):
    videos = get_recent_videos(page)
    rss_date = get_rss_date()
    (queue_size, queue_fetching) = get_queue_size()

    data = (
        [prepare_for_template(video) for video in videos],
        int(page),
        rss_date.date_human,
        queue_size,
        queue_fetching,
    )

    return templates.TemplateResponse(
        "yt_cuck_page.html", {"request": request, "data": data}
    )


@log_decorator
@app.get("/video/{identifier}", response_class=HTMLResponse)
async def video_watch(request: Request, identifier: str):
    video = get_video_by_id(identifier)
    data = prepare_for_watch(video)

    return templates.TemplateResponse(
        "cuck_video.html",
        {"request": request, "data": data, "length": len(data["description"])},
    )


@log_decorator
@app.get("/push_{key}", response_class=HTMLResponse)
async def push_to_watch(request: Request, key: str):
    key_number = int(key)
    video = get_recent_videos(0)[key_number - 1]
    data = prepare_for_watch(video)

    return templates.TemplateResponse(
        "cuck_video.html",
        {"request": request, "data": data, "length": len(data["description"])},
    )


@log_decorator
@app.get("/channel/{channel_name}", response_class=HTMLResponse)
async def channel_video_watch(request: Request, channel_name: str):
    data = get_channel_videos(channel_name)
    data = [
        channel_name,
        [prepare_for_template(video) for video in data],
    ]

    return templates.TemplateResponse(
        "cuck_channel.html", {"request": request, "data": data}
    )


@log_decorator
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


@log_decorator
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


@log_decorator
@app.get("/most_recent_video", response_class=HTMLResponse)
async def most_recent_video_watch(request: Request):
    video = get_video_by_id(most_recent_video().vid_id)
    data = prepare_for_watch(video)

    return templates.TemplateResponse(
        "cuck_video.html",
        {"request": request, "data": data, "length": len(data["description"])},
    )


@log_decorator
@app.get("/most_recent_videos", response_class=HTMLResponse)
async def most_recent_videos_page(request: Request):
    data = most_recent_videos()
    data = [get_video_by_id(video.vid_id) for video in data]
    rss_date = get_rss_date()
    (queue_size, queue_fetching) = get_queue_size()

    data = (
        [prepare_for_template(video) for video in data],
        0,
        rss_date.date_human,
        queue_size,
        queue_fetching,
    )

    return templates.TemplateResponse(
        "yt_cuck.html", {"request": request, "data": data, "is_short": True}
    )


@log_decorator
@app.get("/keep/{video_id}")
async def keep_video(video_id: str):
    t1 = threading.Thread(target=keep_video_request, args=[video_id])
    t1.start()
    return {"text": "Video kept!"}


@log_decorator
@app.get("/unkeep/{video_id}")
async def unkeep_video(video_id: str):
    t1 = threading.Thread(target=unkeep_video_request, args=[video_id])
    t1.start()
    return {"text": "Video unkept!"}


@log_decorator
@app.post("/refresh_rss", status_code=200)
async def refresh_rss():
    get_rss_feed()

    return {"text": "True"}


@log_decorator
@app.post("/save_progress")
async def save_progress(progress: Progress):
    update_video_progress(progress.id, progress.time)

    return {"message": "Progress updated"}


@log_decorator
@app.get("/download/{video_id}")
async def download_video(video_id: str):
    video = get_video_by_id(video_id)
    if not video or not video.vid_path or video.vid_path == "NA":
        return {"error": "Video not found or not downloaded"}, 404

    video_file_path = os.path.join(DATA_FOLDER, "videos", video.vid_path)

    if not os.path.exists(video_file_path):
        return {"error": "Video file not found on disk"}, 404

    # Clean filename for download
    safe_filename = "".join(c for c in video.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_filename = safe_filename[:100]  # Limit length
    file_extension = os.path.splitext(video.vid_path)[1]
    download_filename = f"{safe_filename}{file_extension}"

    return FileResponse(
        path=video_file_path,
        filename=download_filename,
        media_type='application/octet-stream'
    )


@log_decorator
@app.get("/api/playlists")
async def get_playlists_api():
    playlists = get_all_playlists()
    return {"playlists": [{"id": playlist.id, "name": playlist.name} for playlist in playlists]}


@log_decorator
@app.get("/playlist", response_class=HTMLResponse)
async def get_playlists(request: Request):
    playlists = get_all_playlists()
    data = [(playlist.name, playlist.id) for playlist in playlists]
    return templates.TemplateResponse(
        "cuck_playlist.html", {"request": request, "data": data}
    )


@log_decorator
@app.get("/playlist/{playlist_name}", response_class=HTMLResponse)
async def get_playlist_videos_page(request: Request, playlist_name: str):
    playlist = get_playlist_by_name(playlist_name)
    if not playlist:
        return templates.TemplateResponse(
            "cuck_playlist.html", {"request": request, "data": [], "error": "Playlist not found"}
        )

    videos = get_playlist_videos(playlist_name)
    video_data = []
    for playlist_video, youtube_video in videos:
        # Format view count
        views_formatted = ""
        if youtube_video.views:
            views_count = youtube_video.views
            if views_count >= 1000000:
                views_formatted = f"{views_count / 1000000:.1f}M"
            elif views_count >= 1000:
                views_formatted = f"{views_count / 1000:.1f}K"
            else:
                views_formatted = str(views_count)

        video_data.append({
            "id": youtube_video.id,  # Internal ID for watch URL
            "title": playlist_video.title,
            "vid_url": playlist_video.vid_url,
            "vid_path": playlist_video.vid_path,
            "thumb_path": youtube_video.thumb_path,
            "channel": youtube_video.channel,
            "views": views_formatted,
            "pub_date": youtube_video.pub_date
        })

    return templates.TemplateResponse(
        "cuck_playlist_videos.html",
        {"request": request, "playlist_name": playlist_name, "videos": video_data}
    )


@log_decorator
@app.post("/playlist/create", status_code=200)
async def create_new_playlist(
    playlist_name: Annotated[str, Form()],
    response: Response,
):
    success, message = create_playlist(playlist_name)
    if success:
        return {"text": message}
    else:
        response.status_code = 400
        return {"text": message}


@log_decorator
@app.post("/playlist/{playlist_name}/delete", status_code=200)
async def delete_existing_playlist(playlist_name: str, response: Response):
    success, message = delete_playlist(playlist_name)
    if success:
        return {"text": message}
    else:
        response.status_code = 400
        return {"text": message}


@log_decorator
@app.post("/playlist/{playlist_name}/add_video", status_code=200)
async def add_video_to_existing_playlist(
    playlist_name: str,
    video_id: Annotated[str, Form()],
    response: Response,
):
    success, message = add_video_to_playlist(playlist_name, video_id)
    if success:
        return {"text": message}
    else:
        response.status_code = 400
        return {"text": message}


@log_decorator
@app.post("/playlist/{playlist_name}/remove_video", status_code=200)
async def remove_video_from_existing_playlist(
    playlist_name: str,
    video_url: Annotated[str, Form()],
    response: Response,
):
    success, message = remove_video_from_playlist(playlist_name, video_url)
    if success:
        return {"text": message}
    else:
        response.status_code = 400
        return {"text": message}


@log_decorator
@app.on_event("startup")
async def ready_up_server():
    t1 = threading.Thread(target=ready_up_request)
    t1.start()


if __name__ == "__main__":
    uvicorn.run("server:app", port=PORT, reload=True)
