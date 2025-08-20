"""
Configuration for download error handling, retry policies, and system limits.
"""

import os
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""

    max_retries: int = 3
    base_delay: float = 2.0  # seconds
    max_delay: float = 300.0  # 5 minutes max
    exponential_base: float = 2.0
    jitter: bool = True  # Add random jitter to delays


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    max_requests_per_minute: int = 30
    max_requests_per_hour: int = 1000
    rate_limit_backoff_factor: float = 0.5  # Reduce rate by this factor when hit
    rate_limit_recovery_rate: int = 1  # Requests to add back per success


@dataclass
class SystemLimitsConfig:
    """Configuration for system resource limits."""

    max_cpu_percent: float = 90.0
    max_memory_percent: float = 90.0
    min_free_disk_gb: float = 5.0
    min_free_disk_percent: float = 5.0
    max_concurrent_downloads: int = 3
    disk_check_interval: int = 300  # seconds


@dataclass
class TimeoutConfig:
    """Configuration for various timeouts."""

    socket_timeout: int = 60
    download_timeout: int = 1800  # 30 minutes
    extraction_timeout: int = 30
    thumbnail_timeout: int = 30
    ffprobe_timeout: int = 30


@dataclass
class QualityConfig:
    """Configuration for video quality and format preferences."""
    max_height: int = 1080
    preferred_formats: List[str] = None
    fallback_formats: List[str] = None
    max_file_size_mb: Optional[int] = None

    def __post_init__(self):
        if self.preferred_formats is None:
            self.preferred_formats = [
                "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]",
                "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "best[height<=1080][ext=mp4]"
            ]
        if self.fallback_formats is None:
            self.fallback_formats = [
                "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
                "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "best[height<=720][ext=mp4]",
                "bestvideo[height<=480]+bestaudio/best[height<=480]",
                "best[height<=480]",
                "best[ext=mp4]",
                "best",
                "worst"
            ]


@dataclass
class ErrorHandlingConfig:
    """Configuration for error handling behavior."""

    # Errors that should not trigger retries
    permanent_errors: List[str] = None

    # Errors that should trigger rate limit backoff
    rate_limit_errors: List[str] = None

    # Errors that indicate video unavailability
    unavailable_errors: List[str] = None

    # Maximum consecutive failures before pausing downloads
    max_consecutive_failures: int = 10

    # Time to pause downloads after max failures (seconds)
    failure_pause_duration: int = 3600  # 1 hour

    def __post_init__(self):
        if self.permanent_errors is None:
            self.permanent_errors = [
                "Private video",
                "Video unavailable",
                "This video has been removed",
                "This video is not available",
                "Video not found",
                "deleted",
                "removed",
                "copyright",
                "suspended",
                "terminated",
            ]

        if self.rate_limit_errors is None:
            self.rate_limit_errors = [
                "HTTP Error 429",
                "Too Many Requests",
                "rate limit",
                "quota exceeded",
            ]

        if self.unavailable_errors is None:
            self.unavailable_errors = [
                "Private video",
                "Video unavailable",
                "This video has been removed",
                "This video is not available",
                "Video not found",
            ]


@dataclass
class MonitoringConfig:
    """Configuration for download monitoring."""

    stats_retention_hours: int = 168  # 7 days
    alert_failure_rate_threshold: float = 0.3  # 30% failure rate
    alert_check_interval: int = 900  # 15 minutes
    log_stats_interval: int = 3600  # 1 hour
    cleanup_old_stats: bool = True


class DownloadConfig:
    """Main configuration class for download system."""

    def __init__(self):
        self.retry = RetryConfig()
        self.rate_limit = RateLimitConfig()
        self.system_limits = SystemLimitsConfig()
        self.timeouts = TimeoutConfig()
        self.quality = QualityConfig()
        self.error_handling = ErrorHandlingConfig()
        self.monitoring = MonitoringConfig()

        # Load overrides from environment variables
        self._load_from_env()

    def _load_from_env(self):
        """Load configuration overrides from environment variables."""
        # Retry configuration
        if os.getenv("MAX_RETRIES"):
            self.retry.max_retries = int(os.getenv("MAX_RETRIES"))
        if os.getenv("RETRY_BASE_DELAY"):
            self.retry.base_delay = float(os.getenv("RETRY_BASE_DELAY"))
        if os.getenv("RETRY_MAX_DELAY"):
            self.retry.max_delay = float(os.getenv("RETRY_MAX_DELAY"))

        # Rate limiting
        if os.getenv("MAX_REQUESTS_PER_MINUTE"):
            self.rate_limit.max_requests_per_minute = int(
                os.getenv("MAX_REQUESTS_PER_MINUTE")
            )
        if os.getenv("MAX_REQUESTS_PER_HOUR"):
            self.rate_limit.max_requests_per_hour = int(
                os.getenv("MAX_REQUESTS_PER_HOUR")
            )

        # System limits
        if os.getenv("MAX_CPU_PERCENT"):
            self.system_limits.max_cpu_percent = float(os.getenv("MAX_CPU_PERCENT"))
        if os.getenv("MAX_MEMORY_PERCENT"):
            self.system_limits.max_memory_percent = float(
                os.getenv("MAX_MEMORY_PERCENT")
            )
        if os.getenv("MIN_FREE_DISK_GB"):
            self.system_limits.min_free_disk_gb = float(os.getenv("MIN_FREE_DISK_GB"))
        if os.getenv("MAX_CONCURRENT_DOWNLOADS"):
            self.system_limits.max_concurrent_downloads = int(
                os.getenv("MAX_CONCURRENT_DOWNLOADS")
            )

        # Timeouts
        if os.getenv("SOCKET_TIMEOUT"):
            self.timeouts.socket_timeout = int(os.getenv("SOCKET_TIMEOUT"))
        if os.getenv("DOWNLOAD_TIMEOUT"):
            self.timeouts.download_timeout = int(os.getenv("DOWNLOAD_TIMEOUT"))

        # Quality
        if os.getenv("MAX_VIDEO_HEIGHT"):
            self.quality.max_height = int(os.getenv("MAX_VIDEO_HEIGHT"))
        if os.getenv("MAX_FILE_SIZE_MB"):
            self.quality.max_file_size_mb = int(os.getenv("MAX_FILE_SIZE_MB"))

    def get_yt_dlp_options(self, filename: str) -> Dict:
        """Get yt-dlp options based on current configuration."""
        # Create comprehensive format string with all fallbacks
        all_formats = self.quality.preferred_formats + self.quality.fallback_formats
        format_string = "/".join(all_formats)

        options = {
            'format': format_string,
            'outtmpl': f'%(title).200s.%(ext)s',  # Limit filename length
            'quiet': True,
            'no_warnings': False,
            'ignoreerrors': False,
            'overwrites': True,
            'noprogress': True,
            'socket_timeout': self.timeouts.socket_timeout,
            'retries': self.retry.max_retries,
            'fragment_retries': self.retry.max_retries,
            'extractaudio': False,
            'audioformat': 'best',
            'embed_subs': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'subtitleslangs': ['en'],
            'writedescription': False,
            'writeinfojson': False,
            'writethumbnail': False,
            'geo_bypass': True,
            'nocheckcertificate': True,
            'prefer_ffmpeg': True,
            'keepvideo': False,
            'force_generic_extractor': False,
            'extractor_retries': self.retry.max_retries,
        }

        # Add file size limit if configured
        if self.quality.max_file_size_mb:
            options['max_filesize'] = self.quality.max_file_size_mb * 1024 * 1024

        return options

    def should_retry_error(self, error_msg: str) -> bool:
        """Check if an error should trigger a retry."""
        error_lower = error_msg.lower()

        # Don't retry permanent errors
        for permanent_error in self.error_handling.permanent_errors:
            if permanent_error.lower() in error_lower:
                return False

        return True

    def is_rate_limit_error(self, error_msg: str) -> bool:
        """Check if an error indicates rate limiting."""
        error_lower = error_msg.lower()

        for rate_error in self.error_handling.rate_limit_errors:
            if rate_error.lower() in error_lower:
                return True

        return False

    def is_video_unavailable_error(self, error_msg: str) -> bool:
        """Check if an error indicates the video is unavailable."""
        error_lower = error_msg.lower()

        for unavailable_error in self.error_handling.unavailable_errors:
            if unavailable_error.lower() in error_lower:
                return True

        return False

    def get_user_agents(self) -> List[str]:
        """Get list of user agents to rotate through."""
        return [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Android 14; Mobile; rv:121.0) Gecko/121.0 Firefox/121.0",
            "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        ]


# Global configuration instance
config = DownloadConfig()
