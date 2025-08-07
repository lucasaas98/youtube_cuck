var player = document.getElementById("video_player");
var progressBar = null;
var volumeBar = null;
var currentTimeDisplay = null;
var durationDisplay = null;
var playPauseBtn = null;
var fullscreenBtn = null;
var muteBtn = null;
var settingsBtn = null;
var isFullscreen = false;
var lastVolumeBeforeMute = 1;
var progressUpdateInterval = null;

// Initialize enhanced video player
window.onload = function () {
    initializePlayer();
    setupKeyboardControls();
    setupProgressSaving();
    setupResponsivePlayer();
};

function initializePlayer() {
    if (!player) return;

    // Add loading state
    player.classList.add("loading");

    // Remove loading state when video is ready
    player.addEventListener("loadedmetadata", function () {
        player.classList.remove("loading");
        updateDuration();
    });

    // Handle video loading errors gracefully
    player.addEventListener("error", function (e) {
        console.error("Video loading error:", e);
        showNotification(
            "Error loading video. Please try refreshing the page.",
            "error",
        );
        player.classList.remove("loading");
    });

    // Update progress as video plays
    player.addEventListener("timeupdate", updateProgress);

    // Handle video end
    player.addEventListener("ended", function () {
        showNotification("Video finished playing", "info");
        // Could add auto-next functionality here
    });

    // Handle play/pause
    player.addEventListener("play", function () {
        updatePlayButton(true);
    });

    player.addEventListener("pause", function () {
        updatePlayButton(false);
    });

    // Handle volume changes
    player.addEventListener("volumechange", updateVolumeDisplay);

    // Handle fullscreen changes
    document.addEventListener("fullscreenchange", handleFullscreenChange);
    document.addEventListener("webkitfullscreenchange", handleFullscreenChange);
    document.addEventListener("mozfullscreenchange", handleFullscreenChange);
    document.addEventListener("MSFullscreenChange", handleFullscreenChange);
}

function setupKeyboardControls() {
    document.addEventListener("keydown", function (event) {
        // Only handle video controls if:
        // 1. Not in an input field, textarea, or modal
        // 2. Target is video player, body, or related video controls
        // 3. No modal is currently visible
        if (
            event.target.tagName === "INPUT" ||
            event.target.tagName === "TEXTAREA" ||
            event.target.closest(".modal") !== null ||
            event.target.closest(".modal-content") !== null ||
            document.querySelector(".modal[style*='block']") !== null
        ) {
            return;
        }

        // Only prevent default for video control keys
        var videoControlKeys = [
            32, 37, 38, 39, 40, 70, 74, 75, 76, 77, 67, 188, 190,
        ];
        // space, arrows, f, j, k, l, m, c, comma, period
        if (videoControlKeys.includes(event.keyCode)) {
            event.preventDefault();
            handleKeyPress(event);
        }
    });
}

function handleKeyPress(event) {
    if (!player) return;

    switch (event.keyCode) {
        case 32: // Space
        case 75: // K
            togglePlayPause();
            showNotification(player.paused ? "Paused" : "Playing", "info");
            break;
        case 39: // Right arrow
            skipTime(5);
            showNotification("+5 seconds", "info");
            break;
        case 37: // Left arrow
            skipTime(-5);
            showNotification("-5 seconds", "info");
            break;
        case 74: // J
            skipTime(-10);
            showNotification("-10 seconds", "info");
            break;
        case 76: // L
            skipTime(10);
            showNotification("+10 seconds", "info");
            break;
        case 190: // Period (>)
            skipTime(1);
            showNotification("+1 second", "info");
            break;
        case 188: // Comma (<)
            skipTime(-1);
            showNotification("-1 second", "info");
            break;
        case 70: // F
            toggleFullscreen();
            break;
        case 77: // M
            toggleMute();
            break;
        case 67: // C
            toggleCaptions();
            break;
        case 38: // Up arrow
            adjustVolume(0.05);
            break;
        case 40: // Down arrow
            adjustVolume(-0.05);
            break;
    }
}

function togglePlayPause() {
    if (!player) return;

    if (player.paused) {
        player.play().catch((error) => {
            console.error("Error playing video:", error);
            showNotification("Error playing video", "error");
        });
    } else {
        player.pause();
    }
}

function skipTime(seconds) {
    if (!player) return;

    var newTime = Math.max(
        0,
        Math.min(player.duration, player.currentTime + seconds),
    );
    player.currentTime = newTime;
    updateProgress();
}

function adjustVolume(delta) {
    if (!player) return;

    var newVolume = Math.max(0, Math.min(1, player.volume + delta));
    player.volume = newVolume;

    showNotification(`Volume: ${Math.round(newVolume * 100)}%`, "info");
}

function toggleMute() {
    if (!player) return;

    if (player.muted) {
        player.muted = false;
        player.volume = lastVolumeBeforeMute;
        showNotification("Unmuted", "info");
    } else {
        lastVolumeBeforeMute = player.volume;
        player.muted = true;
        showNotification("Muted", "info");
    }
}

function toggleFullscreen() {
    if (!player) return;

    if (!isFullscreen) {
        enterFullscreen();
    } else {
        exitFullscreen();
    }
}

function enterFullscreen() {
    var element = player;

    if (element.requestFullscreen) {
        element.requestFullscreen();
    } else if (element.webkitRequestFullscreen) {
        element.webkitRequestFullscreen();
    } else if (element.mozRequestFullScreen) {
        element.mozRequestFullScreen();
    } else if (element.msRequestFullscreen) {
        element.msRequestFullscreen();
    }
}

function exitFullscreen() {
    if (document.exitFullscreen) {
        document.exitFullscreen();
    } else if (document.webkitExitFullscreen) {
        document.webkitExitFullscreen();
    } else if (document.mozCancelFullScreen) {
        document.mozCancelFullScreen();
    } else if (document.msExitFullscreen) {
        document.msExitFullscreen();
    }
}

function handleFullscreenChange() {
    isFullscreen = !!(
        document.fullscreenElement ||
        document.webkitFullscreenElement ||
        document.mozFullScreenElement ||
        document.msFullscreenElement
    );

    showNotification(
        isFullscreen ? "Entered fullscreen" : "Exited fullscreen",
        "info",
    );
}

function toggleCaptions() {
    if (!player) return;

    var tracks = player.textTracks;
    var hasVisibleTrack = false;

    for (var i = 0; i < tracks.length; i++) {
        if (tracks[i].mode === "showing") {
            tracks[i].mode = "hidden";
            hasVisibleTrack = true;
        } else if (tracks[i].mode === "hidden") {
            tracks[i].mode = "showing";
        }
    }

    if (tracks.length === 0) {
        showNotification("No captions available", "warning");
    } else {
        showNotification(
            hasVisibleTrack ? "Captions hidden" : "Captions shown",
            "info",
        );
    }
}

function updateProgress() {
    if (!player || !player.duration) return;

    var progress = (player.currentTime / player.duration) * 100;
    updateCurrentTimeDisplay();
}

function updateCurrentTimeDisplay() {
    if (!player) return;

    var current = formatTime(player.currentTime);
    var duration = formatTime(player.duration);

    // Update any time displays if they exist
    if (currentTimeDisplay) {
        currentTimeDisplay.textContent = current;
    }
    if (durationDisplay) {
        durationDisplay.textContent = duration;
    }
}

function updateDuration() {
    if (!player) return;
    updateCurrentTimeDisplay();
}

function updatePlayButton(isPlaying) {
    if (playPauseBtn) {
        playPauseBtn.textContent = isPlaying ? "⏸️" : "▶️";
        playPauseBtn.setAttribute("aria-label", isPlaying ? "Pause" : "Play");
    }
}

function updateVolumeDisplay() {
    if (!player) return;

    var volume = player.muted ? 0 : player.volume;

    if (muteBtn) {
        muteBtn.textContent = volume === 0 ? "🔇" : volume < 0.5 ? "🔉" : "🔊";
        muteBtn.setAttribute("aria-label", player.muted ? "Unmute" : "Mute");
    }
}

function formatTime(seconds) {
    if (!seconds || isNaN(seconds)) return "0:00";

    var hours = Math.floor(seconds / 3600);
    var minutes = Math.floor((seconds % 3600) / 60);
    var secs = Math.floor(seconds % 60);

    if (hours > 0) {
        return `${hours}:${minutes.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
    } else {
        return `${minutes}:${secs.toString().padStart(2, "0")}`;
    }
}

function setupProgressSaving() {
    if (!player) return;

    // Save progress every 5 seconds instead of every timeupdate for better performance
    progressUpdateInterval = setInterval(function () {
        if (player.currentTime > 0 && !player.paused) {
            saveProgress();
        }
    }, 5000);

    // Save progress when video is paused or ended
    player.addEventListener("pause", saveProgress);
    player.addEventListener("ended", saveProgress);

    // Save progress when page is about to unload
    window.addEventListener("beforeunload", saveProgress);
}

function saveProgress() {
    if (!player || !window.currentVideoId) return;

    var xhr = new XMLHttpRequest();
    xhr.open("POST", "../save_progress", true);
    xhr.setRequestHeader("Content-Type", "application/json");
    xhr.onload = function () {
        if (xhr.status === 200) {
            console.log("Progress saved:", player.currentTime);
        }
    };
    xhr.onerror = function () {
        console.error("Error saving progress:", xhr.statusText);
    };
    xhr.send(
        JSON.stringify({
            time: player.currentTime,
            id: window.currentVideoId,
        }),
    );
}

function setupResponsivePlayer() {
    if (!player) return;

    // Handle orientation changes on mobile
    window.addEventListener("orientationchange", function () {
        setTimeout(function () {
            adjustPlayerSize();
        }, 500);
    });

    // Handle window resize
    window.addEventListener("resize", debounce(adjustPlayerSize, 250));

    // Initial size adjustment
    adjustPlayerSize();
}

function adjustPlayerSize() {
    if (!player) return;

    var viewer = document.querySelector(".viewer");
    if (!viewer) return;

    var isShorts = viewer.classList.contains("shorts");
    var viewportHeight = window.innerHeight;
    var viewportWidth = window.innerWidth;
    var navHeight = document.querySelector(".nav_bar")?.offsetHeight || 60;
    var infoHeight = document.querySelector(".div_info")?.offsetHeight || 200;

    var maxHeight = viewportHeight - navHeight - 40; // 40px for padding
    var maxWidth = viewportWidth - 40; // 40px for padding

    if (isShorts) {
        // For shorts, maintain 9:16 aspect ratio
        var shortsWidth = Math.min(400, maxWidth * 0.9);
        var shortsHeight = shortsWidth * (16 / 9);

        if (shortsHeight > maxHeight) {
            shortsHeight = maxHeight;
            shortsWidth = shortsHeight * (9 / 16);
        }

        player.style.width = shortsWidth + "px";
        player.style.height = shortsHeight + "px";
        player.style.objectFit = "contain";
    } else {
        // For regular videos, use responsive scaling
        player.style.width = "100%";
        player.style.height = "auto";
        player.style.maxHeight = maxHeight + "px";
        player.style.maxWidth = "100%";
        player.style.objectFit = "contain";
    }
}

function showNotification(message, type = "info") {
    // Remove existing notifications
    var existingNotifications = document.querySelectorAll(
        ".video-notification",
    );
    existingNotifications.forEach(function (notification) {
        notification.remove();
    });

    var notification = document.createElement("div");
    notification.className = "video-notification video-notification-" + type;
    notification.textContent = message;

    // Style the notification
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: var(--bg-modal);
        color: var(--text-primary);
        padding: 12px 20px;
        border-radius: var(--radius-medium);
        box-shadow: var(--shadow-large);
        z-index: 10000;
        font-size: var(--font-size-sm);
        font-weight: 600;
        border-left: 4px solid var(--primary-color);
        animation: slideInRight 0.3s ease, fadeOut 0.3s ease 2.7s;
        max-width: 300px;
        word-wrap: break-word;
    `;

    if (type === "error") {
        notification.style.borderLeftColor = "var(--danger-color)";
        notification.style.background = "rgba(199, 17, 17, 0.1)";
    } else if (type === "warning") {
        notification.style.borderLeftColor = "var(--warning-color)";
        notification.style.background = "rgba(255, 193, 7, 0.1)";
    }

    document.body.appendChild(notification);

    // Remove notification after 3 seconds
    setTimeout(function () {
        if (notification.parentNode) {
            notification.remove();
        }
    }, 3000);
}

// Add CSS animations for notifications
if (!document.getElementById("video-player-styles")) {
    var styles = document.createElement("style");
    styles.id = "video-player-styles";
    styles.textContent = `
        @keyframes slideInRight {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        @keyframes fadeOut {
            from {
                opacity: 1;
            }
            to {
                opacity: 0;
            }
        }

        .video-notification {
            transition: all 0.3s ease;
        }

        .video-notification:hover {
            transform: translateX(-5px);
            box-shadow: var(--shadow-large);
        }
    `;
    document.head.appendChild(styles);
}

// Utility functions
function debounce(func, wait) {
    var timeout;
    return function executedFunction(...args) {
        var later = function () {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Legacy functions for backward compatibility
function start_at(progress) {
    console.log("Starting at progress: " + progress);
    if (player && progress > 0) {
        player.currentTime = progress;
        showNotification(`Resumed at ${formatTime(progress)}`, "info");
    }
}

function add_progress_listener(video_id) {
    window.currentVideoId = video_id;
    console.log("Progress tracking enabled for video ID:", video_id);
}

// Picture-in-Picture support (if available)
function togglePictureInPicture() {
    if (!player) return;

    if ("pictureInPictureEnabled" in document) {
        if (document.pictureInPictureElement) {
            document
                .exitPictureInPicture()
                .then(() =>
                    showNotification("Exited Picture-in-Picture", "info"),
                )
                .catch((err) => console.error("Error exiting PiP:", err));
        } else {
            player
                .requestPictureInPicture()
                .then(() =>
                    showNotification("Entered Picture-in-Picture", "info"),
                )
                .catch((err) => console.error("Error entering PiP:", err));
        }
    } else {
        showNotification("Picture-in-Picture not supported", "warning");
    }
}

// Add Picture-in-Picture keyboard shortcut (P key)
document.addEventListener("keydown", function (event) {
    if (event.keyCode === 80 && !event.target.matches("input, textarea")) {
        // P key
        event.preventDefault();
        togglePictureInPicture();
    }
});

// Cleanup on page unload
window.addEventListener("beforeunload", function () {
    if (progressUpdateInterval) {
        clearInterval(progressUpdateInterval);
    }
});

// Initialize player quality detection and adaptation
function detectAndAdaptQuality() {
    if (!player) return;

    // Monitor network conditions and adapt accordingly
    if ("connection" in navigator) {
        var connection = navigator.connection;

        player.addEventListener("loadstart", function () {
            var effectiveType = connection.effectiveType;

            if (effectiveType === "slow-2g" || effectiveType === "2g") {
                showNotification(
                    "Slow connection detected. Video may buffer.",
                    "warning",
                );
            } else if (effectiveType === "4g") {
                showNotification("High-speed connection detected.", "info");
            }
        });
    }
}

// Initialize quality detection
detectAndAdaptQuality();

// Add video container enhancements
function addVideoEnhancements() {
    if (!player) return;

    var viewer = document.querySelector(".viewer");
    if (!viewer) return;

    // Add playing class when video plays
    player.addEventListener("play", function () {
        viewer.classList.add("playing");
    });

    player.addEventListener("pause", function () {
        viewer.classList.remove("playing");
    });

    player.addEventListener("ended", function () {
        viewer.classList.remove("playing");
    });

    // Add quality indicator if video metadata is available
    player.addEventListener("loadedmetadata", function () {
        addQualityIndicator();
        addTimeRemainingIndicator();
    });

    // Add loading progress ring
    addLoadingProgressRing();
}

function addQualityIndicator() {
    if (!player || document.querySelector(".video-quality-badge")) return;

    var quality = "HD";
    if (player.videoWidth && player.videoHeight) {
        if (player.videoHeight >= 2160) quality = "4K";
        else if (player.videoHeight >= 1440) quality = "2K";
        else if (player.videoHeight >= 1080) quality = "1080p";
        else if (player.videoHeight >= 720) quality = "720p";
        else if (player.videoHeight >= 480) quality = "480p";
        else quality = "360p";
    }

    var badge = document.createElement("div");
    badge.className = "video-quality-badge";
    badge.textContent = quality;

    var viewer = document.querySelector(".viewer");
    if (viewer) {
        viewer.style.position = "relative";
        viewer.appendChild(badge);
    }
}

function addTimeRemainingIndicator() {
    if (!player || document.querySelector(".time-remaining")) return;

    var timeIndicator = document.createElement("div");
    timeIndicator.className = "time-remaining";

    var viewer = document.querySelector(".viewer");
    if (viewer) {
        viewer.style.position = "relative";
        viewer.appendChild(timeIndicator);

        player.addEventListener("timeupdate", function () {
            var remaining = player.duration - player.currentTime;
            if (remaining > 0) {
                timeIndicator.textContent = "-" + formatTime(remaining);
            }
        });
    }
}

function addLoadingProgressRing() {
    if (!player || document.querySelector(".video-progress-ring")) return;

    var progressRing = document.createElement("div");
    progressRing.className = "video-progress-ring";
    progressRing.innerHTML = `
        <svg>
            <circle cx="30" cy="30" r="25"></circle>
        </svg>
    `;

    var viewer = document.querySelector(".viewer");
    if (viewer) {
        viewer.style.position = "relative";
        viewer.appendChild(progressRing);
    }
}

// Initialize video enhancements
addVideoEnhancements();
