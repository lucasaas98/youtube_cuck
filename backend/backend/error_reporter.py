"""
Comprehensive error reporting and recovery utilities for YouTube video downloads.
"""

import json
import logging
import os
import time
import traceback
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from backend.download_monitor import download_monitor, resource_monitor
from backend.env_vars import DATA_FOLDER
from backend.logging import logging as backend_logging

logger = backend_logging.getLogger(__name__)


class ErrorReporter:
    """Comprehensive error reporting and analysis system."""

    def __init__(self):
        self.error_log_file = os.path.join(
            DATA_FOLDER, "error_reports", "download_errors.json"
        )
        self.summary_file = os.path.join(
            DATA_FOLDER, "error_reports", "error_summary.json"
        )
        self.recovery_log_file = os.path.join(
            DATA_FOLDER, "error_reports", "recovery_actions.json"
        )

        # Ensure error reports directory exists
        os.makedirs(os.path.dirname(self.error_log_file), exist_ok=True)

        # Error categories for classification
        self.error_categories = {
            "network": [
                "connection",
                "timeout",
                "dns",
                "ssl",
                "certificate",
                "unreachable",
            ],
            "youtube_api": ["403", "429", "quota", "rate limit", "api key"],
            "video_unavailable": [
                "private",
                "deleted",
                "removed",
                "unavailable",
                "not found",
            ],
            "download_failed": ["extractor", "format", "codec", "corrupted"],
            "disk_space": ["no space", "disk full", "insufficient space"],
            "permission": ["permission denied", "access denied", "forbidden"],
            "system_overload": ["memory", "cpu", "resource"],
            "ffmpeg": ["ffmpeg", "ffprobe", "conversion", "audio", "video processing"],
        }

    def log_error(
        self,
        error_type: str,
        error_msg: str,
        video_url: str = None,
        channel: str = None,
        additional_context: Dict = None,
    ):
        """Log a detailed error report."""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_msg,
            "video_url": video_url,
            "channel": channel,
            "category": self._categorize_error(error_msg),
            "traceback": (
                traceback.format_exc()
                if traceback.format_exc().strip() != "NoneType: None"
                else None
            ),
            "system_info": self._get_system_context(),
            "additional_context": additional_context or {},
        }

        try:
            # Load existing errors
            errors = self._load_error_log()
            errors.append(error_entry)

            # Keep only last 1000 errors to prevent file from growing too large
            if len(errors) > 1000:
                errors = errors[-1000:]

            # Save updated errors
            with open(self.error_log_file, "w") as f:
                json.dump(errors, f, indent=2)

            logger.info(f"Logged error: {error_type} - {error_msg[:100]}...")

        except Exception as e:
            logger.error(f"Failed to log error: {e}")

    def _categorize_error(self, error_msg: str) -> str:
        """Categorize error based on message content."""
        error_lower = error_msg.lower()

        for category, keywords in self.error_categories.items():
            for keyword in keywords:
                if keyword in error_lower:
                    return category

        return "unknown"

    def _get_system_context(self) -> Dict:
        """Get current system context for error reporting."""
        try:
            system_status = resource_monitor.get_system_status()
            download_stats = download_monitor.get_stats_summary()

            return {
                "cpu_percent": system_status.get("cpu_percent", 0),
                "memory_percent": system_status.get("memory", {}).get(
                    "percent_used", 0
                ),
                "disk_percent": system_status.get("disk", {}).get("percent_used", 0),
                "is_overloaded": system_status.get("is_overloaded", False),
                "recent_success_rate": download_stats.get(
                    "recent_success_rate_percent", 0
                ),
                "total_downloads": download_stats.get("total_downloads", 0),
            }
        except Exception as e:
            logger.warning(f"Failed to get system context: {e}")
            return {}

    def _load_error_log(self) -> List[Dict]:
        """Load existing error log."""
        try:
            if os.path.exists(self.error_log_file):
                with open(self.error_log_file, "r") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load error log: {e}")

        return []

    def generate_error_summary(self, hours: int = 24) -> Dict:
        """Generate a summary of errors from the last N hours."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        errors = self._load_error_log()

        # Filter recent errors
        recent_errors = []
        for error in errors:
            try:
                error_time = datetime.fromisoformat(error["timestamp"])
                if error_time >= cutoff_time:
                    recent_errors.append(error)
            except (KeyError, ValueError):
                continue

        # Analyze errors
        summary = {
            "time_period_hours": hours,
            "total_errors": len(recent_errors),
            "errors_by_category": Counter(
                error.get("category", "unknown") for error in recent_errors
            ),
            "errors_by_type": Counter(
                error.get("error_type", "unknown") for error in recent_errors
            ),
            "most_common_errors": self._get_most_common_errors(recent_errors),
            "affected_channels": self._get_affected_channels(recent_errors),
            "error_trend": self._get_error_trend(recent_errors),
            "recommendations": self._generate_recommendations(recent_errors),
            "generated_at": datetime.now().isoformat(),
        }

        # Save summary
        try:
            with open(self.summary_file, "w") as f:
                json.dump(summary, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save error summary: {e}")

        return summary

    def _get_most_common_errors(
        self, errors: List[Dict], limit: int = 10
    ) -> List[Dict]:
        """Get the most common error messages."""
        error_counter = Counter()

        for error in errors:
            # Normalize error message for grouping
            msg = error.get("error_message", "")[:200]  # Truncate for grouping
            error_counter[msg] += 1

        return [
            {"message": msg, "count": count}
            for msg, count in error_counter.most_common(limit)
        ]

    def _get_affected_channels(self, errors: List[Dict]) -> Dict:
        """Get channels most affected by errors."""
        channel_errors = defaultdict(list)

        for error in errors:
            channel = error.get("channel")
            if channel:
                channel_errors[channel].append(error.get("category", "unknown"))

        return {
            channel: {
                "error_count": len(error_list),
                "error_categories": dict(Counter(error_list)),
            }
            for channel, error_list in channel_errors.items()
        }

    def _get_error_trend(self, errors: List[Dict]) -> List[Dict]:
        """Get hourly error trend."""
        hourly_counts = defaultdict(int)

        for error in errors:
            try:
                error_time = datetime.fromisoformat(error["timestamp"])
                hour_key = error_time.strftime("%Y-%m-%d %H:00")
                hourly_counts[hour_key] += 1
            except (KeyError, ValueError):
                continue

        return [
            {"hour": hour, "error_count": count}
            for hour, count in sorted(hourly_counts.items())
        ]

    def _generate_recommendations(self, errors: List[Dict]) -> List[str]:
        """Generate recommendations based on error patterns."""
        recommendations = []
        error_categories = Counter(error.get("category", "unknown") for error in errors)

        # Analyze patterns and generate recommendations
        if error_categories.get("network", 0) > len(errors) * 0.3:
            recommendations.append(
                "High network errors detected. Consider checking internet connection stability."
            )

        if error_categories.get("youtube_api", 0) > len(errors) * 0.2:
            recommendations.append(
                "YouTube API errors detected. Consider implementing longer delays between requests."
            )

        if error_categories.get("disk_space", 0) > 0:
            recommendations.append(
                "Disk space issues detected. Clean up old videos or increase storage capacity."
            )

        if error_categories.get("system_overload", 0) > len(errors) * 0.1:
            recommendations.append(
                "System overload detected. Consider reducing concurrent downloads or upgrading hardware."
            )

        # Check for rate limiting patterns
        rate_limit_errors = sum(
            1
            for error in errors
            if "rate limit" in error.get("error_message", "").lower()
        )
        if rate_limit_errors > len(errors) * 0.1:
            recommendations.append(
                "Rate limiting detected. Consider reducing download frequency or using proxy rotation."
            )

        if not recommendations:
            recommendations.append(
                "No specific issues detected. Monitor for patterns over time."
            )

        return recommendations

    def log_recovery_action(
        self,
        action_type: str,
        description: str,
        success: bool,
        additional_data: Dict = None,
    ):
        """Log recovery actions taken."""
        recovery_entry = {
            "timestamp": datetime.now().isoformat(),
            "action_type": action_type,
            "description": description,
            "success": success,
            "additional_data": additional_data or {},
        }

        try:
            # Load existing recovery log
            recovery_log = []
            if os.path.exists(self.recovery_log_file):
                with open(self.recovery_log_file, "r") as f:
                    recovery_log = json.load(f)

            recovery_log.append(recovery_entry)

            # Keep only last 500 entries
            if len(recovery_log) > 500:
                recovery_log = recovery_log[-500:]

            with open(self.recovery_log_file, "w") as f:
                json.dump(recovery_log, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to log recovery action: {e}")

    def get_error_report(self, hours: int = 24) -> Dict:
        """Get comprehensive error report."""
        summary = self.generate_error_summary(hours)

        # Add system health information
        system_status = resource_monitor.get_system_status()
        download_stats = download_monitor.get_stats_summary()

        report = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "time_period_hours": hours,
                "report_version": "1.0",
            },
            "error_summary": summary,
            "system_health": {
                "current_status": system_status,
                "download_performance": download_stats,
                "health_score": self._calculate_health_score(
                    summary, system_status, download_stats
                ),
            },
            "recovery_suggestions": self._get_recovery_suggestions(summary),
        }

        return report

    def _calculate_health_score(
        self, error_summary: Dict, system_status: Dict, download_stats: Dict
    ) -> float:
        """Calculate overall system health score (0-100)."""
        score = 100.0

        # Deduct points for errors
        total_errors = error_summary.get("total_errors", 0)
        if total_errors > 0:
            score -= min(30, total_errors * 2)  # Max 30 points for errors

        # Deduct points for low success rate
        success_rate = download_stats.get("recent_success_rate_percent", 100)
        if success_rate < 90:
            score -= (90 - success_rate) * 0.5

        # Deduct points for system overload
        if system_status.get("is_overloaded", False):
            score -= 20

        # Deduct points for high resource usage
        cpu_percent = system_status.get("cpu_percent", 0)
        memory_percent = system_status.get("memory", {}).get("percent_used", 0)
        disk_percent = system_status.get("disk", {}).get("percent_used", 0)

        if cpu_percent > 80:
            score -= (cpu_percent - 80) * 0.5
        if memory_percent > 80:
            score -= (memory_percent - 80) * 0.5
        if disk_percent > 90:
            score -= (disk_percent - 90) * 2

        return max(0, min(100, score))

    def _get_recovery_suggestions(self, error_summary: Dict) -> List[Dict]:
        """Get specific recovery suggestions based on error patterns."""
        suggestions = []

        error_categories = error_summary.get("errors_by_category", {})

        for category, count in error_categories.items():
            if count > 5:  # Only suggest for significant error counts
                suggestion = self._get_category_suggestion(category, count)
                if suggestion:
                    suggestions.append(suggestion)

        return suggestions

    def _get_category_suggestion(self, category: str, count: int) -> Optional[Dict]:
        """Get specific suggestion for error category."""
        suggestions_map = {
            "network": {
                "priority": "high",
                "action": "Check network connectivity and DNS settings",
                "description": f"{count} network-related errors detected",
                "automated_action": "restart_network_monitoring",
            },
            "youtube_api": {
                "priority": "high",
                "action": "Implement rate limiting and request throttling",
                "description": f"{count} YouTube API errors detected",
                "automated_action": "enable_aggressive_rate_limiting",
            },
            "disk_space": {
                "priority": "critical",
                "action": "Free up disk space immediately",
                "description": f"{count} disk space errors detected",
                "automated_action": "cleanup_old_videos",
            },
            "system_overload": {
                "priority": "medium",
                "action": "Reduce system load or upgrade hardware",
                "description": f"{count} system overload errors detected",
                "automated_action": "reduce_concurrent_downloads",
            },
        }

        return suggestions_map.get(category)

    def cleanup_old_reports(self, days: int = 30):
        """Clean up error reports older than specified days."""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)

            # Clean error log
            errors = self._load_error_log()
            filtered_errors = []

            for error in errors:
                try:
                    error_time = datetime.fromisoformat(error["timestamp"])
                    if error_time >= cutoff_time:
                        filtered_errors.append(error)
                except (KeyError, ValueError):
                    continue

            if len(filtered_errors) != len(errors):
                with open(self.error_log_file, "w") as f:
                    json.dump(filtered_errors, f, indent=2)

                logger.info(
                    f"Cleaned up {len(errors) - len(filtered_errors)} old error reports"
                )

        except Exception as e:
            logger.error(f"Failed to cleanup old reports: {e}")


# Global error reporter instance
error_reporter = ErrorReporter()


def report_download_error(error_type: str, error_msg: str, video_url: str = None, video_title: str = None, channel: str = None, **kwargs):
    """Convenience function to report download errors."""
    # Handle case where video_title is passed as positional argument
    if video_title is not None and 'video_title' not in kwargs:
        kwargs['video_title'] = video_title
    error_reporter.log_error(error_type, error_msg, video_url, channel, kwargs)


def report_recovery_action(action_type: str, description: str, success: bool, **kwargs):
    """Convenience function to report recovery actions."""
    error_reporter.log_recovery_action(action_type, description, success, kwargs)


def get_system_health_report(hours: int = 24) -> Dict:
    """Get comprehensive system health report."""
    return error_reporter.get_error_report(hours)
