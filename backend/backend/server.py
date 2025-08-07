import atexit
import logging as _logging

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from backend.engine import close_engine
from backend.env_vars import PORT
from backend.logging import logging
from backend.repo import (
    add_video_to_playlist,
    create_playlist,
    delete_playlist,
    get_all_playlists,
    get_playlist_by_name,
    get_playlist_videos,
    remove_video_from_playlist,
)
from backend.utils import (
    download_and_keep,
    get_queue_size,
    get_rss_feed,
    log_decorator,
    remove_old_videos,
    unkeep,
)

logger = logging.getLogger(__name__)
logger.setLevel(_logging.INFO)

app = FastAPI()


@log_decorator
@app.post("/api/refresh_rss")
def refresh_rss():
    get_rss_feed()
    # download_old_livestreams()
    return {"text": "Refreshing RSS feed!"}


@log_decorator
@app.post("/api/startup")
def startup():
    activate_schedule()
    # get_rss_feed()
    remove_old_videos()
    # download_old_livestreams()

    return {"text": "First start setup initialized!"}


@log_decorator
@app.get("/api/working_threads")
def get_size():
    size = get_queue_size()
    return {"size": size, "still_fetching": size != 0}


@log_decorator
@app.get("/api/fetch_and_keep/{video_id}")
def get_video_and_keep(video_id: str):
    download_and_keep(video_id)
    return {"text": "Downloading video!"}


@log_decorator
@app.get("/api/unkeep/{video_id}")
def unkeep_video(video_id: str):
    unkeep(video_id)
    return {"text": "Downloading video!"}


@log_decorator
@app.get("/api/playlists")
def get_playlists():
    playlists = get_all_playlists()
    return {"playlists": [{"id": p[0].id, "name": p[0].name} for p in playlists]}


@log_decorator
@app.get("/api/playlist/{playlist_name}")
def get_playlist(playlist_name: str):
    playlist = get_playlist_by_name(playlist_name)
    if not playlist:
        return {"error": "Playlist not found"}, 404

    videos = get_playlist_videos(playlist_name)
    return {
        "playlist": {"id": playlist[0].id, "name": playlist[0].name},
        "videos": [
            {
                "vid_url": v[0].vid_url,
                "vid_path": v[0].vid_path,
                "title": v[0].title
            } for v in videos
        ]
    }


@log_decorator
@app.post("/api/playlist/create/{playlist_name}")
def create_new_playlist(playlist_name: str):
    success, message = create_playlist(playlist_name)
    if success:
        return {"text": message}
    else:
        return {"error": message}, 400


@log_decorator
@app.delete("/api/playlist/{playlist_name}")
def delete_existing_playlist(playlist_name: str):
    success, message = delete_playlist(playlist_name)
    if success:
        return {"text": message}
    else:
        return {"error": message}, 400


@log_decorator
@app.post("/api/playlist/{playlist_name}/add/{video_id}")
def add_video_to_existing_playlist(playlist_name: str, video_id: str):
    success, message = add_video_to_playlist(playlist_name, video_id)
    if success:
        return {"text": message}
    else:
        return {"error": message}, 400


@log_decorator
@app.delete("/api/playlist/{playlist_name}/remove/{video_url}")
def remove_video_from_existing_playlist(playlist_name: str, video_url: str):
    success, message = remove_video_from_playlist(playlist_name, video_url)
    if success:
        return {"text": message}
    else:
        return {"error": message}, 400


@log_decorator
def activate_schedule():
    scheduler = BackgroundScheduler()
    # Schedule to remove videos older than X time
    scheduler.add_job(func=remove_old_videos, trigger="interval", seconds=86400)
    # first_run = datetime.datetime.now() + datetime.timedelta(hours=1)
    # scheduler.add_job(func=download_old_livestreams, trigger="interval", seconds=86400, next_run_time=first_run)
    # Schedule to get RSS feed automatically
    # scheduler.add_job(func=get_rss_feed, trigger="interval", seconds=600)
    scheduler.start()

    # Shut down the scheduler when exiting the app
    atexit.register(scheduler.shutdown)
    # Shut down the scheduler when exiting the app
    atexit.register(close_engine)


if __name__ == "__main__":
    uvicorn.run("server:app", port=PORT, reload=True)
