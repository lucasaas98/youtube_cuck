import atexit
import logging as _logging

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from backend.engine import close_engine
from backend.env_vars import PORT
from backend.logging import logging
from backend.utils import (
    download_old_livestreams,
    get_queue_size,
    get_rss_feed,
    remove_old_videos,
    update_size_for_old_videos,
)

logger = logging.getLogger(__name__)
logger.setLevel(_logging.INFO)

app = FastAPI()


@app.post("/api/refresh_rss")
def refresh_rss():
    get_rss_feed()
    return {"text": "Refreshing RSS feed!"}


@app.post("/api/startup")
def startup():
    activate_schedule()
    get_rss_feed()
    remove_old_videos()
    download_old_livestreams()

    # TEMP: because we added the size column to the database, we need to update the size column for all videos
    # TODO: remove this after a few days
    update_size_for_old_videos()
    return {"text": "First start setup initialized!"}


@app.get("/api/working_threads")
def get_size():
    size = get_queue_size()
    return {"size": size, "still_fetching": size != 0}


def activate_schedule():
    scheduler = BackgroundScheduler()
    # Schedule to remove videos older than X time
    scheduler.add_job(func=remove_old_videos, trigger="interval", seconds=3600)
    scheduler.add_job(func=download_old_livestreams, trigger="interval", seconds=3600)
    # Schedule to get RSS feed automatically
    # scheduler.add_job(func=get_rss_feed, trigger="interval", seconds=600)
    scheduler.start()

    # Shut down the scheduler when exiting the app
    atexit.register(scheduler.shutdown)
    # Shut down the scheduler when exiting the app
    atexit.register(close_engine)


if __name__ == "__main__":
    uvicorn.run("server:app", port=PORT, reload=True)
