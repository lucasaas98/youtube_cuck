import atexit
from concurrent.futures import ThreadPoolExecutor
import logging as _logging

from apscheduler.schedulers.background import BackgroundScheduler

import uvicorn
from fastapi import FastAPI


from backend.engine import close_engine
from backend.logging import logging
from backend.utils import get_rss_feed, remove_old_videos, get_queue_size, video_download_thread
from backend.env_vars import PORT, DATA_FOLDER
import os

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
    return {"text": "First start setup initialized!"}


@app.get("/api/working_threads")
def startup():
    size = get_queue_size()
    return {"size": size, "still_fetching": size != 0}


def activate_schedule():
    scheduler = BackgroundScheduler()
    # Schedule to remove videos older than X time
    scheduler.add_job(func=remove_old_videos, trigger="interval", seconds=3600)
    # Schedule to get RSS feed automatically
    # scheduler.add_job(func=get_rss_feed, trigger="interval", seconds=600)
    scheduler.start()

    # Shut down the scheduler when exiting the app
    atexit.register(scheduler.shutdown)
    atexit.register(close_engine)
    remove_old_videos()
    get_rss_feed()


if __name__ == "__main__":
    uvicorn.run("server:app", port=PORT, reload=True)
