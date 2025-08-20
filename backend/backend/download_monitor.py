"""
Download monitoring and rate limiting utilities for YouTube video downloads.
"""

import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Optional

import psutil

from backend.env_vars import DATA_FOLDER
from backend.logging import logging

logger = logging.getLogger(__name__)


class DownloadMonitor:
    """Monitor download performance and system resources."""

    def __init__(self):
        self.download_stats = {
            "total_downloads": 0,
            "successful_downloads": 0,
            "failed_downloads": 0,
            "total_size_mb": 0,
            "start_time": time.time(),
        }
        self.recent_downloads = deque(maxlen=100)  # Keep last 100 downloads
        self._lock = threading.Lock()

    def record_download_attempt(self, video_url: str, file_name: str):
        """Record the start of a download attempt."""
        with self._lock:
            self.download_stats["total_downloads"] += 1
            self.recent_downloads.append(
                {
                    "url": video_url,
                    "file_name": file_name,
                    "start_time": time.time(),
                    "status": "started",
                }
            )

    def record_download_success(self, video_url: str, file_size_mb: float):
        """Record a successful download."""
        with self._lock:
            self.download_stats["successful_downloads"] += 1
            self.download_stats["total_size_mb"] += file_size_mb

            # Update recent downloads
            for download in reversed(self.recent_downloads):
                if download["url"] == video_url and download["status"] == "started":
                    download["status"] = "success"
                    download["end_time"] = time.time()
                    download["size_mb"] = file_size_mb
                    break

    def record_download_failure(self, video_url: str, error_msg: str):
        """Record a failed download."""
        with self._lock:
            self.download_stats["failed_downloads"] += 1

            # Update recent downloads
            for download in reversed(self.recent_downloads):
                if download["url"] == video_url and download["status"] == "started":
                    download["status"] = "failed"
                    download["end_time"] = time.time()
                    download["error"] = error_msg
                    break

    def get_success_rate(self) -> float:
        """Get the overall success rate as a percentage."""
        total = self.download_stats["total_downloads"]
        if total == 0:
            return 0.0
        return (self.download_stats["successful_downloads"] / total) * 100

    def get_recent_success_rate(self, minutes: int = 60) -> float:
        """Get success rate for recent downloads within the specified time window."""
        cutoff_time = time.time() - (minutes * 60)
        recent_total = 0
        recent_successful = 0

        with self._lock:
            for download in self.recent_downloads:
                if download.get("end_time", 0) > cutoff_time:
                    recent_total += 1
                    if download["status"] == "success":
                        recent_successful += 1

        if recent_total == 0:
            return 0.0
        return (recent_successful / recent_total) * 100

    def get_stats_summary(self) -> Dict:
        """Get a summary of download statistics."""
        runtime_hours = (time.time() - self.download_stats["start_time"]) / 3600

        return {
            "total_downloads": self.download_stats["total_downloads"],
            "successful_downloads": self.download_stats["successful_downloads"],
            "failed_downloads": self.download_stats["failed_downloads"],
            "success_rate_percent": self.get_success_rate(),
            "recent_success_rate_percent": self.get_recent_success_rate(),
            "total_size_gb": round(self.download_stats["total_size_mb"] / 1024, 2),
            "runtime_hours": round(runtime_hours, 2),
            "avg_downloads_per_hour": (
                round(self.download_stats["total_downloads"] / runtime_hours, 2)
                if runtime_hours > 0
                else 0
            ),
        }


class RateLimiter:
    """Rate limiter to prevent overwhelming YouTube's servers."""

    def __init__(self, max_requests: int = 30, time_window: int = 60):
        """
        Initialize rate limiter.

        Args:
            max_requests: Maximum number of requests allowed in the time window
            time_window: Time window in seconds
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self._lock = threading.Lock()
        self.consecutive_failures = 0
        self.last_failure_time = 0

    def can_make_request(self) -> bool:
        """Check if a request can be made without exceeding the rate limit."""
        with self._lock:
            now = time.time()

            # Remove old requests outside the time window
            while self.requests and self.requests[0] <= now - self.time_window:
                self.requests.popleft()

            # Check if we're within the rate limit
            if len(self.requests) < self.max_requests:
                return True

            return False

    def record_request(self):
        """Record that a request was made."""
        with self._lock:
            self.requests.append(time.time())

    def record_failure(self, is_rate_limit_error: bool = False):
        """Record a failed request and adjust rate limiting if needed."""
        with self._lock:
            self.consecutive_failures += 1
            self.last_failure_time = time.time()

            if is_rate_limit_error:
                # Reduce rate limit temporarily on 429 errors
                self.max_requests = max(5, self.max_requests // 2)
                logger.warning(
                    f"Rate limit hit, reducing max requests to {self.max_requests}"
                )

    def record_success(self):
        """Record a successful request."""
        with self._lock:
            self.consecutive_failures = 0

            # Gradually increase rate limit back to normal after successes
            if self.max_requests < 30:
                self.max_requests = min(30, self.max_requests + 1)

    def get_wait_time(self) -> float:
        """Get the recommended wait time before the next request."""
        with self._lock:
            if not self.requests:
                return 0.0

            # Basic rate limiting
            if len(self.requests) >= self.max_requests:
                oldest_request = self.requests[0]
                wait_time = self.time_window - (time.time() - oldest_request)
                if wait_time > 0:
                    return wait_time

            # Exponential backoff for consecutive failures
            if self.consecutive_failures > 0:
                backoff_time = min(
                    300, 2 ** min(self.consecutive_failures, 8)
                )  # Max 5 minutes
                time_since_failure = time.time() - self.last_failure_time
                if time_since_failure < backoff_time:
                    return backoff_time - time_since_failure

            return 0.0


class SystemResourceMonitor:
    """Monitor system resources to prevent overloading."""

    @staticmethod
    def get_disk_usage() -> Dict:
        """Get disk usage information for the data folder."""
        try:
            usage = psutil.disk_usage(DATA_FOLDER)
            return {
                "total_gb": round(usage.total / (1024**3), 2),
                "used_gb": round(usage.used / (1024**3), 2),
                "free_gb": round(usage.free / (1024**3), 2),
                "percent_used": round((usage.used / usage.total) * 100, 2),
            }
        except Exception as error:
            logger.error(f"Failed to get disk usage: {error}")
            return {}

    @staticmethod
    def get_memory_usage() -> Dict:
        """Get memory usage information."""
        try:
            memory = psutil.virtual_memory()
            return {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "percent_used": memory.percent,
            }
        except Exception as error:
            logger.error(f"Failed to get memory usage: {error}")
            return {}

    @staticmethod
    def get_cpu_usage() -> float:
        """Get current CPU usage percentage."""
        try:
            return psutil.cpu_percent(interval=1)
        except Exception as error:
            logger.error(f"Failed to get CPU usage: {error}")
            return 0.0

    @staticmethod
    def is_system_overloaded() -> bool:
        """Check if the system is overloaded and downloads should be paused."""
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            if cpu_percent > 90:
                logger.warning(f"High CPU usage: {cpu_percent}%")
                return True

            # Check memory usage
            memory = psutil.virtual_memory()
            if memory.percent > 90:
                logger.warning(f"High memory usage: {memory.percent}%")
                return True

            # Check disk space
            disk = psutil.disk_usage(DATA_FOLDER)
            disk_percent = (disk.used / disk.total) * 100
            if disk_percent > 95:
                logger.warning(f"Low disk space: {disk_percent}% used")
                return True

            return False

        except Exception as error:
            logger.error(f"Failed to check system resources: {error}")
            return False

    @classmethod
    def get_system_status(cls) -> Dict:
        """Get comprehensive system status."""
        return {
            "disk": cls.get_disk_usage(),
            "memory": cls.get_memory_usage(),
            "cpu_percent": cls.get_cpu_usage(),
            "is_overloaded": cls.is_system_overloaded(),
            "timestamp": datetime.now().isoformat(),
        }


# Global instances
download_monitor = DownloadMonitor()
rate_limiter = RateLimiter()
resource_monitor = SystemResourceMonitor()


def should_download_now() -> tuple[bool, str]:
    """
    Check if it's safe to start a download now.

    Returns:
        tuple: (can_download, reason_if_not)
    """
    # Check system resources
    if resource_monitor.is_system_overloaded():
        return False, "System is overloaded (high CPU/memory/disk usage)"

    # Check rate limiting
    if not rate_limiter.can_make_request():
        wait_time = rate_limiter.get_wait_time()
        return False, f"Rate limited, wait {wait_time:.1f} seconds"

    # Check recent success rate
    recent_success_rate = download_monitor.get_recent_success_rate(
        30
    )  # Last 30 minutes
    if (
        recent_success_rate < 50
        and download_monitor.download_stats["total_downloads"] > 10
    ):
        return False, f"Low recent success rate: {recent_success_rate:.1f}%"

    return True, ""


def wait_for_safe_download():
    """Wait until it's safe to perform a download."""
    max_wait = 300  # Maximum 5 minutes
    start_time = time.time()

    while time.time() - start_time < max_wait:
        can_download, reason = should_download_now()
        if can_download:
            return True

        logger.info(f"Waiting to download: {reason}")
        time.sleep(10)  # Check every 10 seconds

    logger.warning("Timeout waiting for safe download conditions")
    return False
