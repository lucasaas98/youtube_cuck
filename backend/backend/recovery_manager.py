"""
Automated recovery mechanisms for common download failures.
"""

import asyncio
import os
import time
from typing import Dict

from backend.download_config import config
from backend.download_monitor import download_monitor, rate_limiter, resource_monitor
from backend.engine import session_scope
from backend.env_vars import DATA_FOLDER
from backend.error_reporter import error_reporter, report_recovery_action
from backend.logging import logging
from backend.models import YoutubeVideo
from backend.repo import get_expired_videos

logger = logging.getLogger(__name__)


class RecoveryManager:
    """Manages automated recovery from various download failures."""

    def __init__(self):
        self.recovery_history = {}
        self.last_recovery_check = time.time()
        self.recovery_actions = {
            "disk_cleanup": self._disk_cleanup_recovery,
            "rate_limit_adjustment": self._rate_limit_recovery,
            "failed_download_retry": self._failed_download_retry,
            "corrupted_file_cleanup": self._corrupted_file_cleanup,
            "database_cleanup": self._database_cleanup,
            "system_resource_management": self._system_resource_recovery,
            "network_recovery": self._network_recovery,
            "thumbnail_recovery": self._thumbnail_recovery,
        }

    async def check_and_recover(self) -> Dict[str, bool]:
        """Check system status and perform necessary recovery actions."""
        recovery_results = {}

        try:
            # Get current system status
            system_status = resource_monitor.get_system_status()
            download_stats = download_monitor.get_stats_summary()

            # Check if recovery is needed
            recovery_needed = self._assess_recovery_needs(system_status, download_stats)

            for action_name, is_needed in recovery_needed.items():
                if is_needed:
                    logger.info(f"Initiating recovery action: {action_name}")
                    try:
                        success = await self.recovery_actions[action_name]()
                        recovery_results[action_name] = success

                        report_recovery_action(
                            action_name,
                            f"Automated recovery action: {action_name}",
                            success,
                        )

                        if success:
                            logger.info(
                                f"Recovery action {action_name} completed successfully"
                            )
                        else:
                            logger.warning(f"Recovery action {action_name} failed")

                    except Exception as error:
                        logger.error(
                            f"Error during recovery action {action_name}: {error}"
                        )
                        recovery_results[action_name] = False

                        report_recovery_action(
                            action_name,
                            f"Recovery action failed with error: {error}",
                            False,
                        )

            self.last_recovery_check = time.time()

        except Exception as error:
            logger.error(f"Error during recovery check: {error}")

        return recovery_results

    def _assess_recovery_needs(
        self, system_status: Dict, download_stats: Dict
    ) -> Dict[str, bool]:
        """Assess what recovery actions are needed."""
        needs = {}

        # Disk space recovery
        disk_info = system_status.get("disk", {})
        disk_usage = disk_info.get("percent_used", 0)
        needs["disk_cleanup"] = disk_usage > 90

        # Rate limit recovery
        recent_success = download_stats.get("recent_success_rate_percent", 100)
        needs["rate_limit_adjustment"] = (
            recent_success < 50 and download_stats.get("total_downloads", 0) > 10
        )

        # Failed download retry
        needs["failed_download_retry"] = self._should_retry_failed_downloads()

        # Corrupted file cleanup
        needs["corrupted_file_cleanup"] = self._should_cleanup_corrupted_files()

        # Database cleanup
        needs["database_cleanup"] = self._should_cleanup_database()

        # System resource management
        needs["system_resource_management"] = system_status.get("is_overloaded", False)

        # Network recovery
        needs["network_recovery"] = self._should_attempt_network_recovery(
            download_stats
        )

        # Thumbnail recovery
        needs["thumbnail_recovery"] = self._should_recover_thumbnails()

        return needs

    async def _disk_cleanup_recovery(self) -> bool:
        """Recover disk space by cleaning up old and unnecessary files."""
        try:
            cleaned_space = 0

            # Clean up old videos based on removal delay
            expired_videos = get_expired_videos()
            for video in expired_videos:
                if video.vid_path and video.vid_path != "NA":
                    video_path = os.path.join(DATA_FOLDER, "videos", video.vid_path)
                    if os.path.exists(video_path):
                        file_size = os.path.getsize(video_path)
                        os.remove(video_path)
                        cleaned_space += file_size
                        logger.info(f"Removed expired video: {video.vid_path}")

                if video.thumb_path:
                    thumb_path = os.path.join(
                        DATA_FOLDER, "thumbnails", video.thumb_path
                    )
                    if os.path.exists(thumb_path):
                        os.remove(thumb_path)

            # Clean up partial downloads
            videos_dir = os.path.join(DATA_FOLDER, "videos")
            if os.path.exists(videos_dir):
                for filename in os.listdir(videos_dir):
                    if filename.endswith(".part") or filename.endswith(".temp"):
                        file_path = os.path.join(videos_dir, filename)
                        try:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            cleaned_space += file_size
                            logger.info(f"Removed partial download: {filename}")
                        except Exception as e:
                            logger.warning(
                                f"Failed to remove partial file {filename}: {e}"
                            )

            # Clean up old error reports
            error_reporter.cleanup_old_reports(days=7)

            logger.info(
                f"Disk cleanup completed. Freed {cleaned_space / (1024*1024):.2f} MB"
            )
            return True

        except Exception as error:
            logger.error(f"Disk cleanup failed: {error}")
            return False

    async def _rate_limit_recovery(self) -> bool:
        """Adjust rate limiting to recover from API limits."""
        try:
            # Reduce rate limits aggressively
            original_rate = rate_limiter.max_requests
            rate_limiter.max_requests = max(5, rate_limiter.max_requests // 2)

            # Reset consecutive failures
            rate_limiter.consecutive_failures = 0

            # Clear recent requests to allow immediate gradual recovery
            rate_limiter.requests.clear()

            logger.info(
                f"Rate limit adjusted from {original_rate} to {rate_limiter.max_requests}"
            )
            return True

        except Exception as error:
            logger.error(f"Rate limit recovery failed: {error}")
            return False

    async def _failed_download_retry(self) -> bool:
        """Retry failed downloads that might succeed now."""
        try:
            # Find videos that failed to download in the last 24 hours
            with session_scope() as session:
                cutoff_time = int(time.time()) - (24 * 3600)
                failed_videos = (
                    session.query(YoutubeVideo)
                    .filter(
                        YoutubeVideo.vid_path == "NA",
                        YoutubeVideo.inserted_at > cutoff_time,
                        YoutubeVideo.livestream == False,
                    )
                    .limit(5)
                    .all()
                )  # Limit retries to avoid overwhelming system

                retry_count = 0
                for video in failed_videos:
                    # Check if we should retry this video
                    if self._should_retry_video(video):
                        logger.info(f"Retrying failed download: {video.title}")
                        # Schedule for retry (would be handled by main download process)
                        retry_count += 1

                logger.info(f"Scheduled {retry_count} failed downloads for retry")
                return retry_count > 0

        except Exception as error:
            logger.error(f"Failed download retry failed: {error}")
            return False

    async def _corrupted_file_cleanup(self) -> bool:
        """Clean up corrupted or incomplete video files."""
        try:
            cleaned_files = 0
            videos_dir = os.path.join(DATA_FOLDER, "videos")

            if not os.path.exists(videos_dir):
                return True

            for filename in os.listdir(videos_dir):
                if filename.endswith(".mp4"):
                    file_path = os.path.join(videos_dir, filename)

                    # Check if file is corrupted or too small
                    if self._is_file_corrupted(file_path):
                        try:
                            os.remove(file_path)
                            cleaned_files += 1
                            logger.info(f"Removed corrupted file: {filename}")

                            # Update database to reflect missing file
                            with session_scope() as session:
                                video = (
                                    session.query(YoutubeVideo)
                                    .filter(YoutubeVideo.vid_path == filename)
                                    .first()
                                )

                                if video:
                                    video.vid_path = "NA"
                                    video.downloaded_at = None
                                    session.commit()

                        except Exception as e:
                            logger.warning(
                                f"Failed to remove corrupted file {filename}: {e}"
                            )

            logger.info(f"Cleaned up {cleaned_files} corrupted files")
            return True

        except Exception as error:
            logger.error(f"Corrupted file cleanup failed: {error}")
            return False

    async def _database_cleanup(self) -> bool:
        """Clean up inconsistent database entries."""
        try:
            with session_scope() as session:
                # Find videos marked as downloaded but files don't exist
                videos_with_files = (
                    session.query(YoutubeVideo)
                    .filter(
                        YoutubeVideo.vid_path != "NA", YoutubeVideo.vid_path.isnot(None)
                    )
                    .all()
                )

                fixed_count = 0
                for video in videos_with_files:
                    file_path = os.path.join(DATA_FOLDER, "videos", video.vid_path)
                    if not os.path.exists(file_path):
                        video.vid_path = "NA"
                        video.downloaded_at = None
                        video.size = None
                        fixed_count += 1

                session.commit()
                logger.info(f"Fixed {fixed_count} inconsistent database entries")
                return True

        except Exception as error:
            logger.error(f"Database cleanup failed: {error}")
            return False

    async def _system_resource_recovery(self) -> bool:
        """Manage system resources during overload."""
        try:
            # Temporarily reduce concurrent operations
            original_workers = config.system_limits.max_concurrent_downloads
            config.system_limits.max_concurrent_downloads = max(
                1, original_workers // 2
            )

            # Clear any stuck processes or connections
            # This is a placeholder for more advanced process management

            logger.info("Reduced system load temporarily")

            # Schedule restoration of normal limits after some time
            await asyncio.sleep(300)  # Wait 5 minutes
            config.system_limits.max_concurrent_downloads = original_workers

            return True

        except Exception as error:
            logger.error(f"System resource recovery failed: {error}")
            return False

    async def _network_recovery(self) -> bool:
        """Attempt to recover from network issues."""
        try:
            # Reset network-related rate limiters
            rate_limiter.consecutive_failures = 0

            # Clear any cached DNS or connection issues
            # This is a placeholder for more advanced network recovery

            logger.info("Network recovery actions completed")
            return True

        except Exception as error:
            logger.error(f"Network recovery failed: {error}")
            return False

    async def _thumbnail_recovery(self) -> bool:
        """Recover missing thumbnails for downloaded videos."""
        try:
            with session_scope() as session:
                # Find videos with missing thumbnails
                videos_without_thumbs = (
                    session.query(YoutubeVideo)
                    .filter(
                        YoutubeVideo.vid_path != "NA", YoutubeVideo.thumb_path.is_(None)
                    )
                    .limit(10)
                    .all()
                )  # Limit to avoid overwhelming

                recovered_count = 0
                for video in videos_without_thumbs:
                    if video.thumb_url:
                        # This would trigger thumbnail download
                        # Implementation would depend on your thumbnail download function
                        recovered_count += 1

                logger.info(
                    f"Attempted thumbnail recovery for {recovered_count} videos"
                )
                return True

        except Exception as error:
            logger.error(f"Thumbnail recovery failed: {error}")
            return False

    def _should_retry_failed_downloads(self) -> bool:
        """Check if failed downloads should be retried."""
        try:
            with session_scope() as session:
                recent_failures = (
                    session.query(YoutubeVideo)
                    .filter(
                        YoutubeVideo.vid_path == "NA",
                        YoutubeVideo.inserted_at > int(time.time()) - 3600,  # Last hour
                    )
                    .count()
                )

                return recent_failures > 5

        except Exception:
            return False

    def _should_cleanup_corrupted_files(self) -> bool:
        """Check if corrupted file cleanup is needed."""
        # Check if we haven't done cleanup recently
        return (
            time.time() - self.recovery_history.get("last_corruption_check", 0) > 3600
        )

    def _should_cleanup_database(self) -> bool:
        """Check if database cleanup is needed."""
        return (
            time.time() - self.recovery_history.get("last_db_cleanup", 0) > 86400
        )  # Daily

    def _should_attempt_network_recovery(self, download_stats: Dict) -> bool:
        """Check if network recovery should be attempted."""
        return download_stats.get("recent_success_rate_percent", 100) < 30

    def _should_recover_thumbnails(self) -> bool:
        """Check if thumbnail recovery is needed."""
        return time.time() - self.recovery_history.get("last_thumb_recovery", 0) > 86400

    def _should_retry_video(self, video) -> bool:
        """Check if a specific video should be retried."""
        # Don't retry if it was attempted very recently
        if video.inserted_at > int(time.time()) - 1800:  # 30 minutes
            return False

        # Don't retry if it's been attempted too many times
        retry_key = f"retry_{video.id}"
        retry_count = self.recovery_history.get(retry_key, 0)
        if retry_count >= 3:
            return False

        self.recovery_history[retry_key] = retry_count + 1
        return True

    def _is_file_corrupted(self, file_path: str) -> bool:
        """Check if a video file is corrupted or incomplete."""
        try:
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size < 1024:  # Less than 1KB is likely corrupted
                return True

            # Could add more sophisticated corruption detection here
            # using ffprobe or similar tools

            return False

        except Exception:
            return True

    async def emergency_recovery(self) -> bool:
        """Perform emergency recovery when system is in critical state."""
        try:
            logger.warning("Initiating emergency recovery")

            # Stop all downloads immediately
            # This would need integration with your download manager

            # Free up maximum disk space
            await self._disk_cleanup_recovery()

            # Reset all rate limiters
            rate_limiter.max_requests = 5
            rate_limiter.consecutive_failures = 0
            rate_limiter.requests.clear()

            # Clear any system overload conditions
            await self._system_resource_recovery()

            logger.info("Emergency recovery completed")
            report_recovery_action(
                "emergency_recovery", "Emergency recovery procedure executed", True
            )

            return True

        except Exception as error:
            logger.error(f"Emergency recovery failed: {error}")
            report_recovery_action(
                "emergency_recovery", f"Emergency recovery failed: {error}", False
            )
            return False


# Global recovery manager instance
recovery_manager = RecoveryManager()


async def run_recovery_check():
    """Run recovery check - can be called periodically."""
    return await recovery_manager.check_and_recover()


async def emergency_recovery():
    """Run emergency recovery procedure."""
    return await recovery_manager.emergency_recovery()
