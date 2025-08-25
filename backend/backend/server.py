import atexit
import logging as _logging

import uvicorn
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI

from backend.download_service import (
    get_download_service,
    start_download_service,
    stop_download_service,
)
from backend.engine import close_engine
from backend.env_vars import PORT
from backend.logging import logging
from backend.repo import (
    add_channel_to_db,
    add_video_to_playlist,
    create_playlist,
    delete_old_download_jobs,
    delete_playlist,
    get_all_playlists,
    get_download_job_stats,
    get_download_jobs_paginated,
    get_filtered_videos,
    get_playlist_by_name,
    get_playlist_videos,
    remove_channel_from_db,
    remove_video_from_playlist,
    retry_download_job,
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


@app.on_event("startup")
async def startup_event():
    """Start the download service when the application starts."""
    logger.info("Starting download service and scheduler on application startup...")
    activate_schedule()
    logger.info("Download service and scheduler started successfully")


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
    from backend.download_service import queue_download
    from backend.repo import get_video_by_id

    try:
        # Get video info from database
        video_data = get_video_by_id(video_id)
        if not video_data:
            return {"error": "Video not found"}, 404

        video = video_data[0]

        # If video is already downloaded, just mark as kept
        if video.vid_path and video.vid_path != "NA":
            # Use the original download_and_keep logic for already downloaded videos
            download_and_keep(video_id)
            return {"text": "Video marked as kept!"}

        # Create video data for queue
        video_info = {
            "video_url": video.vid_url,
            "title": video.title,
            "thumbnail": video.thumb_url,
            "epoch_date": str(video.pub_date),
            "human_date": video.pub_date_human,
            "views": str(video.views),
            "description": video.description,
        }

        success, message, job_id = queue_download(
            video_url=video.vid_url,
            video_title=video.title,
            channel_name=video.channel,
            video_data=video_info,
            priority=10,  # High priority for keep requests
        )

        if success:
            # Also mark the video as kept in the database
            from backend.engine import session_scope
            from backend.models import YoutubeVideo

            with session_scope() as session:
                session.query(YoutubeVideo).filter(YoutubeVideo.id == video.id).update(
                    {"keep": True}
                )
                session.commit()

            return {
                "text": f"Video queued for download and marked as kept! Job ID: {job_id}"
            }
        else:
            return {"error": message}, 400

    except Exception as e:
        logger.error(f"Error in fetch_and_keep: {e}")
        # Fallback to original behavior if queue fails
        download_and_keep(video_id)
        return {"text": "Video processed using fallback method!"}


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
    import xml.etree.ElementTree as ET
    from xml.dom import minidom

    try:
        # First add to database
        db_success, db_message = add_channel_to_db(
            channel_id, channel_url, channel_name
        )
        if not db_success:
            return {"success": False, "error": db_message}, 400

        # Then add to OPML file using proper XML parsing
        from backend.env_vars import DATA_FOLDER

        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        opml_file_path = f"{DATA_FOLDER}/subscription_manager"

        try:
            # Read and parse the existing OPML file
            with open(opml_file_path, "r") as f:
                content = f.read()

            # Parse XML properly
            root = ET.fromstring(content)

            # Find the main outline container (the one with subscriptions)
            body = root.find("body")
            main_outline = body.find("outline")

            # Escape special characters in channel name for XML
            escaped_name = (
                channel_name.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;")
            )

            # Create new channel outline element
            new_outline = ET.SubElement(main_outline, "outline")
            new_outline.set("text", escaped_name)
            new_outline.set("title", escaped_name)
            new_outline.set("type", "rss")
            new_outline.set("xmlUrl", feed_url)

            # Convert back to string with proper formatting
            rough_string = ET.tostring(root, encoding="unicode")

            # Pretty print for better formatting
            dom = minidom.parseString(rough_string)
            pretty_xml = dom.toprettyxml(indent="    ")

            # Clean up extra blank lines and XML declaration
            lines = [line for line in pretty_xml.split("\n") if line.strip()]
            # Remove XML declaration line and add our own
            if lines[0].startswith("<?xml"):
                lines = lines[1:]

            final_content = "\n".join(lines)

            # Write back to file
            with open(opml_file_path, "w") as f:
                f.write(final_content)

            logger.info(f"Successfully added channel {channel_name} to OPML file")
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
@app.get("/api/videos/filtered")
def get_videos_filtered(
    page: int = 0,
    items_per_page: int = 35,
    search_query: str = None,
    sort_by: str = "downloaded_at",
    sort_order: str = "desc",
    filter_kept: str = None,
    include_shorts: bool = True,
):
    """
    Get filtered and sorted videos with search capability.

    :param page: Page number (0-based)
    :param items_per_page: Number of items per page
    :param search_query: Search query for title, description, or channel
    :param sort_by: Field to sort by (downloaded_at, pub_date, title, views)
    :param sort_order: Sort order (asc or desc)
    :param filter_kept: Filter by keep status ('true', 'false', or None for all)
    :param include_shorts: Whether to include shorts
    :return: Filtered videos with pagination info
    """
    # Convert filter_kept string to boolean or None
    kept_filter = None
    if filter_kept == "true":
        kept_filter = True
    elif filter_kept == "false":
        kept_filter = False

    videos, total_count = get_filtered_videos(
        page=page,
        items_per_page=items_per_page,
        search_query=search_query,
        sort_by=sort_by,
        sort_order=sort_order,
        filter_kept=kept_filter,
        include_shorts=include_shorts,
    )

    # Convert videos to JSON-serializable format
    video_data = []
    for video in videos:
        video_data.append(
            {
                "id": video.id,
                "vid_url": video.vid_url,
                "vid_path": video.vid_path,
                "thumb_url": video.thumb_url,
                "thumb_path": video.thumb_path,
                "pub_date": video.pub_date,
                "pub_date_human": video.pub_date_human,
                "title": video.title,
                "views": video.views,
                "description": video.description,
                "channel": video.channel,
                "channel_id": video.channel_id,
                "short": video.short,
                "livestream": video.livestream,
                "progress_seconds": video.progress_seconds,
                "inserted_at": video.inserted_at,
                "downloaded_at": video.downloaded_at,
                "size": video.size,
                "keep": video.keep,
            }
        )

    total_pages = max(1, (total_count + items_per_page - 1) // items_per_page)

    return {
        "videos": video_data,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_items": total_count,
            "items_per_page": items_per_page,
            "has_prev": page > 0,
            "has_next": page < total_pages - 1,
        },
        "filters": {
            "search_query": search_query,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "filter_kept": filter_kept,
            "include_shorts": include_shorts,
        },
    }


@log_decorator
@app.get("/api/downloads/stats")
def get_download_stats():
    """Get download job statistics."""
    stats = get_download_job_stats()
    service = get_download_service()
    service_status = service.get_service_status()

    return {"job_stats": stats, "service_status": service_status}


@log_decorator
@app.get("/api/downloads/jobs")
def get_download_jobs(page: int = 0, items_per_page: int = 50, status: str = None):
    """Get download jobs with pagination and optional status filtering."""
    jobs, total_count = get_download_jobs_paginated(
        page=page, items_per_page=items_per_page, status_filter=status
    )

    # Convert jobs to JSON-serializable format
    job_data = []
    for job in jobs:
        job_data.append(
            {
                "id": job.id,
                "video_url": job.video_url,
                "video_title": job.video_title,
                "channel_name": job.channel_name,
                "status": job.status,
                "priority": job.priority,
                "created_at": job.created_at,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "error_message": job.error_message,
                "retry_count": job.retry_count,
                "max_retries": job.max_retries,
            }
        )

    total_pages = max(1, (total_count + items_per_page - 1) // items_per_page)

    return {
        "jobs": job_data,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "total_items": total_count,
            "items_per_page": items_per_page,
            "has_prev": page > 0,
            "has_next": page < total_pages - 1,
        },
    }


@log_decorator
@app.post("/api/downloads/retry/{job_id}")
def retry_download(job_id: int):
    """Retry a failed download job."""
    success, message = retry_download_job(job_id)
    if success:
        return {"text": message}
    else:
        return {"error": message}, 400


@log_decorator
@app.post("/api/downloads/queue/{video_id}")
def queue_video_download(video_id: str):
    """Queue a specific video for download (for manual downloads)."""
    from backend.download_service import queue_download
    from backend.repo import get_video_by_id

    try:
        # Get video info from database
        video_data = get_video_by_id(video_id)
        if not video_data:
            return {"error": "Video not found"}, 404

        video = video_data[0]

        # Create video data for queue
        video_info = {
            "video_url": video.vid_url,
            "title": video.title,
            "thumbnail": video.thumb_url,
            "epoch_date": str(video.pub_date),
            "human_date": video.pub_date_human,
            "views": str(video.views),
            "description": video.description,
        }

        success, message, job_id = queue_download(
            video_url=video.vid_url,
            video_title=video.title,
            channel_name=video.channel,
            video_data=video_info,
            priority=1,  # Higher priority for manual downloads
        )

        if success:
            return {"text": f"Video queued for download. Job ID: {job_id}"}
        else:
            return {"error": message}, 400

    except Exception as e:
        logger.error(f"Error queuing video download: {e}")
        return {"error": "Failed to queue video for download"}, 500


@log_decorator
def activate_schedule():
    scheduler = BackgroundScheduler()
    # Schedule to remove videos older than X time
    scheduler.add_job(func=remove_old_videos, trigger="interval", seconds=86400)
    # Schedule to clean up old download jobs (every 24 hours)
    scheduler.add_job(
        func=delete_old_download_jobs,
        trigger="interval",
        seconds=86400,
        kwargs={"days_old": 30},
    )
    # first_run = datetime.datetime.now() + datetime.timedelta(hours=1)
    # scheduler.add_job(func=download_old_livestreams, trigger="interval", seconds=86400, next_run_time=first_run)
    # Schedule to get RSS feed automatically
    # scheduler.add_job(func=get_rss_feed, trigger="interval", seconds=600)
    scheduler.start()

    # Start the download service
    start_download_service()

    # Shut down the scheduler when exiting the app
    atexit.register(scheduler.shutdown)
    # Shut down the download service when exiting the app
    atexit.register(stop_download_service)
    # Shut down the engine when exiting the app
    atexit.register(close_engine)


if __name__ == "__main__":
    uvicorn.run("server:app", port=PORT, reload=True)
