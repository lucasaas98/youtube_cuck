import json
import logging as _logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from time import time as current_time

from backend.engine import session_scope
from backend.logging import logging
from backend.models import YoutubeVideo
from backend.repo import (
    get_pending_download_jobs,
    get_retry_download_jobs,
    update_download_job_status,
)
from backend.utils import (
    confirm_video_name,
    download_thumbnail,
    download_video,
    extract_video_info,
    get_video_size,
    video_type,
)

logger = logging.getLogger(__name__)
logger.setLevel(_logging.INFO)


class DownloadService:
    def __init__(self, max_concurrent_downloads=3):
        """
        Initialize the download service.

        :param max_concurrent_downloads: Maximum number of concurrent downloads
        """
        self.max_concurrent_downloads = max_concurrent_downloads
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent_downloads)
        self.active_downloads = {}
        self.running = False
        self.service_thread = None

    def start(self):
        """Start the download service."""
        if self.running:
            logger.warning("Download service is already running")
            return

        self.running = True
        logger.info(
            f"Starting download service with {self.max_concurrent_downloads} max concurrent downloads"
        )
        self.service_thread = threading.Thread(target=self._process_download_queue)
        self.service_thread.daemon = True
        self.service_thread.start()
        logger.info("Download service thread started successfully")

    def stop(self):
        """Stop the download service."""
        logger.info("Stopping download service...")
        self.running = False
        if self.service_thread:
            self.service_thread.join(timeout=10)
        self.executor.shutdown(wait=True)
        logger.info("Download service stopped successfully")

    def _process_download_queue(self):
        """Main loop to process download jobs."""
        logger.info("Download service queue processor thread started")

        while self.running:
            try:
                # Check if we can start more downloads
                active_count = len(self.active_downloads)
                available_slots = self.max_concurrent_downloads - active_count

                if available_slots <= 0:
                    time.sleep(5)
                    continue

                # Get pending jobs first, then retry jobs
                pending_jobs = get_pending_download_jobs(limit=available_slots)
                if not pending_jobs:
                    retry_jobs = get_retry_download_jobs(limit=available_slots)
                    jobs_to_process = retry_jobs
                else:
                    jobs_to_process = pending_jobs

                if not jobs_to_process:
                    time.sleep(10)  # Wait longer if no jobs
                    continue

                # Process available jobs
                for job in jobs_to_process[:available_slots]:
                    if not self.running:
                        break

                    future = self.executor.submit(self._process_download_job, job)
                    self.active_downloads[job.id] = future

                    # Clean up completed futures
                    completed_jobs = []
                    for job_id, future in self.active_downloads.items():
                        if future.done():
                            completed_jobs.append(job_id)

                    for job_id in completed_jobs:
                        del self.active_downloads[job_id]

            except Exception as e:
                logger.error(f"Error in download queue processor: {e}")
                time.sleep(5)

        logger.info("Download service queue processor stopped")

    def _process_download_job(self, job):
        """
        Process a single download job.

        :param job: DownloadJob instance
        """
        logger.info(f"Starting download job {job.id} for video: {job.video_title}")

        try:
            # Mark job as downloading
            update_download_job_status(job.id, "downloading")

            # Parse video data
            video_data = json.loads(job.video_data) if job.video_data else {}

            # Check if video already exists
            existing_video = self._check_existing_video(job.video_url)
            if (
                existing_video
                and existing_video.vid_path
                and existing_video.vid_path != "NA"
            ):
                logger.info(
                    f"Video {job.video_title} already downloaded, marking job as completed"
                )
                update_download_job_status(job.id, "completed")
                return

            # Extract video info
            video_info = extract_video_info(job.video_url)
            video_type_result = video_type(video_info)

            # Handle different video types
            if video_type_result in ["livestream", "premiere"]:
                self._process_livestream_job(job, video_data)
            else:
                self._process_regular_video_job(job, video_data, video_type_result)

            update_download_job_status(job.id, "completed")
            logger.info(
                f"Successfully completed download job {job.id} for video: {job.video_title}"
            )

        except Exception as e:
            error_message = str(e)
            logger.error(f"Failed to process download job {job.id}: {error_message}")
            update_download_job_status(job.id, "failed", error_message)

    def _check_existing_video(self, video_url):
        """Check if video already exists in database."""
        try:
            with session_scope() as session:
                video = (
                    session.query(YoutubeVideo)
                    .filter(YoutubeVideo.vid_url == video_url)
                    .first()
                )
                return video
        except Exception as e:
            logger.error(f"Error checking existing video: {e}")
            return None

    def _process_livestream_job(self, job, video_data):
        """Process a livestream/premiere job."""
        try:
            # Check if video already exists
            existing_video = self._check_existing_video(job.video_url)

            if existing_video:
                # Update existing video if needed
                logger.info(f"Livestream {job.video_title} already exists in database")
                return

            # Create livestream entry
            video_object = YoutubeVideo(
                vid_url=job.video_url,
                thumb_url=video_data.get("thumbnail", ""),
                pub_date=int(video_data.get("epoch_date", current_time())),
                pub_date_human=video_data.get("human_date", ""),
                title=job.video_title,
                views=int(video_data.get("views", 0)),
                description=video_data.get("description", ""),
                channel=job.channel_name,
                livestream=True,
                short=False,
                inserted_at=int(current_time()),
                vid_path="NA",  # Livestreams don't have immediate video files
            )

            with session_scope() as session:
                session.add(video_object)
                session.commit()
                logger.info(f"Added livestream entry for {job.video_title}")

        except Exception as e:
            raise Exception(f"Failed to process livestream job: {e}")

    def _process_regular_video_job(self, job, video_data, video_type_result):
        """Process a regular video download job."""
        try:
            file_name = job.video_url.split("=")[1]

            # Download video
            download_result = download_video(job.video_url, file_name)
            if download_result != 0:
                raise Exception(f"YT_DLP failed to download video {job.video_url}")

            # Confirm video file exists
            if not confirm_video_name(file_name):
                raise Exception(f"Failed to confirm video file for {job.video_url}")

            vid_path = f"{file_name}.mp4"
            thumb_path = f"{file_name}.jpg"

            # Download thumbnail
            thumbnail_url = video_data.get("thumbnail", "")
            if thumbnail_url:
                download_thumbnail(thumbnail_url, thumb_path)

            # Get video size
            size = get_video_size(vid_path)

            now = int(current_time())

            # Check if video already exists, update or create
            existing_video = self._check_existing_video(job.video_url)

            if existing_video:
                # Update existing video
                with session_scope() as session:
                    video = (
                        session.query(YoutubeVideo)
                        .filter(YoutubeVideo.vid_url == job.video_url)
                        .first()
                    )
                    if video:
                        video.vid_path = vid_path
                        video.thumb_path = thumb_path
                        video.downloaded_at = now
                        video.size = size
                        if not video.title or video.title == "":
                            video.title = job.video_title
                        if not video.channel or video.channel == "":
                            video.channel = job.channel_name
                        session.commit()
                        logger.info(
                            f"Updated existing video entry for {job.video_title}"
                        )
            else:
                # Create new video entry
                video_object = YoutubeVideo(
                    vid_url=job.video_url,
                    vid_path=vid_path,
                    thumb_url=thumbnail_url,
                    thumb_path=thumb_path,
                    pub_date=int(video_data.get("epoch_date", now)),
                    pub_date_human=video_data.get("human_date", ""),
                    title=job.video_title,
                    views=int(video_data.get("views", 0)),
                    description=video_data.get("description", ""),
                    channel=job.channel_name,
                    livestream=False,
                    short=video_type_result == "short",
                    inserted_at=now,
                    downloaded_at=now,
                    size=size,
                )

                with session_scope() as session:
                    session.add(video_object)
                    session.commit()
                    logger.info(f"Added new video entry for {job.video_title}")

        except Exception as e:
            raise Exception(f"Failed to process regular video job: {e}")

    def get_active_download_count(self):
        """Get the number of currently active downloads."""
        return len(self.active_downloads)

    def get_service_status(self):
        """Get the status of the download service."""
        return {
            "running": self.running,
            "active_downloads": self.get_active_download_count(),
            "max_concurrent": self.max_concurrent_downloads,
        }


# Global download service instance
_download_service = None


def get_download_service():
    """Get the global download service instance."""
    global _download_service
    if _download_service is None:
        _download_service = DownloadService()
    return _download_service


def start_download_service():
    """Start the global download service."""
    logger.info("Starting global download service...")
    service = get_download_service()
    service.start()
    logger.info("Global download service started")


def stop_download_service():
    """Stop the global download service."""
    logger.info("Stopping global download service...")
    service = get_download_service()
    service.stop()
    logger.info("Global download service stopped")


def queue_download(video_url, video_title, channel_name, video_data, priority=0):
    """
    Queue a video for download.

    :param video_url: URL of the video
    :param video_title: Title of the video
    :param channel_name: Channel name
    :param video_data: Video data from RSS
    :param priority: Download priority
    :return: Tuple of (success, message, job_id)
    """
    from backend.repo import create_download_job

    return create_download_job(
        video_url, video_title, channel_name, video_data, priority
    )
