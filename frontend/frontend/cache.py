import os

from frontend.repo import get_last_videos

from frontend.logging import logging
from frontend.env_vars import DATA_FOLDER

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

video_cache = {}

def cache_videos(number_to_cache):
    logging.debug(f"Caching {number_to_cache} videos")
    # cache recent videos
    videos = get_last_videos(number_to_cache)
    for video in videos:
        cache_video(video.id, video.vid_path)

    # collect the ids of the videos and delete from cache the ones that are no longer the "last videos"
    last_video_ids = [video.id for video in videos]
    for video_id in list(video_cache.keys()):
        if video_id not in last_video_ids:
            del video_cache[video_id]
            logging.debug(f"Deleted video {video_id} from cache")


def cache_video(identifier, path):
    path = f"{DATA_FOLDER}/videos/{path}"
    logging.debug(f"Caching video {identifier} from path {path}")
    if os.path.exists(path):
        # read video from file path and add to a var to be added to cache later
        with open(path, "rb") as f:
            video_data = f.read()
        video_cache[identifier] = video_data
        logging.debug(f"Video {identifier} cached successfully")
    else:
        logging.debug(f"Video {identifier} not found at path {path}")


def fetch_video_from_cache(identifier):
    logging.debug(f"Fetching video {identifier} from cache")
    video_data = video_cache.get(identifier)
    def generator():
        yield video_data
    return generator()


def is_video_cached(identifier):
    logging.debug(f"Checking if video {identifier} is cached")
    is_cached = identifier in video_cache
    logging.debug(f"video {identifier} is not cached")
    return is_cached
