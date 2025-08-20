import atexit
import logging as _logging

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from backend.download_config import config
from backend.download_monitor import download_monitor, resource_monitor
from backend.engine import close_engine
from backend.env_vars import PORT
from backend.logging import logging
from backend.repo import (
    add_channel_to_db,
    add_video_to_playlist,
    create_playlist,
    delete_playlist,
    get_all_playlists,
    get_playlist_by_name,
    get_playlist_videos,
    remove_channel_from_db,
    remove_video_from_playlist,
)
from backend.utils import (
    download_and_keep,
    get_queue_size,
    get_rss_feed,
    log_decorator,
    preview_channel_info,
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
    try:
        size = get_queue_size()
        return {"size": size, "still_fetching": size != 0}
    except Exception as e:
        logger.error(f"Failed to get queue size: {e}")
        return {"size": 0, "still_fetching": False}


@app.get("/api/download_status")
def get_download_status():
    """Get comprehensive download status including queue and active downloads."""
    try:
        from backend.download_monitor import download_monitor
        from backend.utils import video_executor

        queue_size = get_queue_size()
        stats = download_monitor.get_stats_summary()

        return {
            "queue_size": queue_size,
            "active_downloads": (
                len(video_executor._threads)
                if hasattr(video_executor, "_threads")
                else 0
            ),
            "max_workers": video_executor._max_workers,
            "stats": stats,
            "is_downloading": queue_size > 0 or stats.get("total_downloads", 0) > 0,
        }
    except Exception as e:
        logger.error(f"Failed to get download status: {e}")
        return {
            "queue_size": 0,
            "active_downloads": 0,
            "max_workers": 1,
            "stats": {},
            "is_downloading": False,
        }


@app.get("/api/system_status")
def get_system_status():
    """Get comprehensive system status for monitoring."""
    try:
        from backend.download_monitor import download_monitor, resource_monitor
        from backend.error_reporter import error_reporter

        system_status = resource_monitor.get_system_status()
        recent_errors = error_reporter.generate_error_summary(hours=1)

        return {
            "system": system_status,
            "recent_errors": {
                "total_errors": recent_errors.get("total_errors", 0),
                "error_categories": recent_errors.get("errors_by_category", {}),
                "most_common": recent_errors.get("most_common_errors", [])[:5],
            },
            "health_score": (
                error_reporter._calculate_health_score(
                    recent_errors, system_status, download_monitor.get_stats_summary()
                )
                if hasattr(error_reporter, "_calculate_health_score")
                else 100
            ),
        }
    except Exception as e:
        logger.error(f"Failed to get system status: {e}")
        return {
            "system": {},
            "recent_errors": {
                "total_errors": 0,
                "error_categories": {},
                "most_common": [],
            },
            "health_score": 0,
        }


@app.get("/api/download_history")
def get_download_history():
    """Get recent download history for monitoring."""
    try:
        from backend.download_monitor import download_monitor

        stats = download_monitor.get_stats_summary()
        recent_downloads = list(download_monitor.recent_downloads)[
            -20:
        ]  # Last 20 downloads

        return {
            "recent_downloads": recent_downloads,
            "statistics": stats,
            "success_rates": {
                "last_hour": download_monitor.get_recent_success_rate(60),
                "last_6_hours": download_monitor.get_recent_success_rate(360),
                "last_24_hours": download_monitor.get_recent_success_rate(1440),
                "overall": download_monitor.get_success_rate(),
            },
        }
    except Exception as e:
        logger.error(f"Failed to get download history: {e}")
        return {
            "recent_downloads": [],
            "statistics": {},
            "success_rates": {
                "last_hour": 0,
                "last_6_hours": 0,
                "last_24_hours": 0,
                "overall": 0,
            },
        }


@app.get("/api/download_status/widget")
def get_widget_status():
    """Lightweight endpoint for download status widget."""
    try:
        queue_size = get_queue_size()

        # Get basic download info without heavy processing
        from backend.utils import video_executor

        active_downloads = (
            len(video_executor._threads) if hasattr(video_executor, "_threads") else 0
        )

        return {
            "queue_size": queue_size,
            "active_downloads": active_downloads,
            "is_downloading": queue_size > 0 or active_downloads > 0,
            "timestamp": int(__import__("time").time()),
        }
    except Exception as e:
        logger.error(f"Failed to get widget status: {e}")
        return {
            "queue_size": 0,
            "active_downloads": 0,
            "is_downloading": False,
            "timestamp": int(__import__("time").time()),
        }


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


@app.get("/health")
def health_check():
    """Health check endpoint with system status."""
    system_status = resource_monitor.get_system_status()
    download_stats = download_monitor.get_stats_summary()

    # Determine overall health
    is_healthy = True
    issues = []

    if system_status.get("is_overloaded", False):
        is_healthy = False
        issues.append("System is overloaded")

    if download_stats.get("recent_success_rate_percent", 100) < 70:
        is_healthy = False
        issues.append(
            f"Low recent success rate: {download_stats.get('recent_success_rate_percent', 0):.1f}%"
        )

    disk_info = system_status.get("disk", {})
    if disk_info.get("percent_used", 0) > 95:
        is_healthy = False
        issues.append(
            f"Disk space critical: {disk_info.get('percent_used', 0):.1f}% used"
        )

    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "issues": issues,
        "system": system_status,
        "downloads": download_stats,
        "timestamp": system_status.get("timestamp"),
    }


@app.get("/stats")
def get_download_stats():
    """Get detailed download statistics."""
    return {
        "download_stats": download_monitor.get_stats_summary(),
        "system_status": resource_monitor.get_system_status(),
        "config": {
            "max_retries": config.retry.max_retries,
            "max_requests_per_minute": config.rate_limit.max_requests_per_minute,
            "max_concurrent_downloads": config.system_limits.max_concurrent_downloads,
            "max_video_height": config.quality.max_height,
        },
    }


@app.get("/stats/recent")
def get_recent_stats():
    """Get recent download performance metrics."""
    return {
        "success_rate_1h": download_monitor.get_recent_success_rate(60),
        "success_rate_6h": download_monitor.get_recent_success_rate(360),
        "success_rate_24h": download_monitor.get_recent_success_rate(1440),
        "overall_success_rate": download_monitor.get_success_rate(),
    }


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
            {"vid_url": v[0].vid_url, "vid_path": v[0].vid_path, "title": v[0].title}
            for v in videos
        ],
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
@app.post("/api/preview_channel")
def preview_channel(channel_input: str):
    result = preview_channel_info(channel_input)
    if result["success"]:
        return {"success": True, "channel_info": result["channel_info"]}
    else:
        return {"success": False, "error": result["error"]}, 400


@log_decorator
@app.post("/api/add_channel")
def add_channel_to_system(channel_id: str, channel_url: str, channel_name: str):
    """
    Add a channel to both the database and OPML subscription file.
    """
    try:
        # First add to database
        db_success, db_message = add_channel_to_db(
            channel_id, channel_url, channel_name
        )
        if not db_success:
            return {"success": False, "error": db_message}, 400

        # Then add to OPML file
        from backend.env_vars import DATA_FOLDER

        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

        try:
            with open(f"{DATA_FOLDER}/subscription_manager", "r") as fi:
                sub_data = fi.readlines()

            with open(f"{DATA_FOLDER}/subscription_manager", "w") as fo:
                data = sub_data[0]
                data += sub_data[1].split("</outline></body></opml>")[0]
                data += f'<outline text="{channel_name}" title="{channel_name}" type="rss" xmlUrl="{feed_url}" />'
                data += "</outline></body></opml>"
                fo.write(data)

            return {"success": True, "message": "Channel added successfully"}

        except Exception as e:
            # If OPML update fails, remove from database
            remove_channel_from_db(channel_id)
            logger.error(f"Failed to update OPML file: {e}")
            return {
                "success": False,
                "error": "Failed to update subscription file",
            }, 500

    except Exception as e:
        logger.error(f"Error adding channel: {e}")
        return {"success": False, "error": "Internal server error"}, 500


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
