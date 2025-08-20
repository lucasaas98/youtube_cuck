// Download Status Widget JavaScript
// Provides real-time updates for download queue and status

class DownloadStatusWidget {
    constructor() {
        this.indicator = document.getElementById("download-indicator");
        this.text = document.getElementById("download-text");
        this.widget = document.getElementById("download-status-widget");
        this.updateInterval = null;
        this.isVisible = true;

        this.init();
    }

    init() {
        if (!this.indicator || !this.text || !this.widget) {
            console.warn("Download status widget elements not found");
            return;
        }

        // Make widget clickable to go to stats page
        this.widget.addEventListener("click", () => {
            window.location.href = "/stats";
        });

        // Add cursor pointer
        this.widget.style.cursor = "pointer";

        // Start periodic updates
        this.startUpdates();

        // Handle visibility changes
        document.addEventListener("visibilitychange", () => {
            if (document.hidden) {
                this.stopUpdates();
            } else {
                this.startUpdates();
            }
        });

        // Handle page unload
        window.addEventListener("beforeunload", () => {
            this.stopUpdates();
        });
    }

    startUpdates() {
        // Update immediately
        this.updateStatus();

        // Then update every 5 seconds
        this.updateInterval = setInterval(() => {
            this.updateStatus();
        }, 5000);
    }

    stopUpdates() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    async updateStatus() {
        try {
            const response = await fetch("/api/download_status/widget");

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.displayStatus(data);
        } catch (error) {
            console.error("Failed to update download status:", error);
            this.displayError();
        }
    }

    displayStatus(data) {
        const queueSize = data.queue_size || 0;
        const isDownloading = data.is_downloading || false;
        const activeDownloads = data.active_downloads || 0;

        // Update indicator
        this.indicator.className = `download-indicator ${isDownloading ? "active" : "idle"}`;

        // Update text
        let statusText;
        if (isDownloading) {
            if (activeDownloads > 0) {
                statusText = `Downloading ${activeDownloads} (${queueSize} queued)`;
            } else {
                statusText = `Processing (${queueSize} queued)`;
            }
        } else {
            if (queueSize > 0) {
                statusText = `Ready (${queueSize} queued)`;
            } else {
                statusText = "Idle";
            }
        }

        this.text.textContent = statusText;

        // Update widget title for accessibility
        this.widget.title = `Download Status: ${statusText}. Click to view detailed stats.`;

        // Add visual feedback based on queue size
        this.updateVisualFeedback(queueSize, isDownloading);
    }

    updateVisualFeedback(queueSize, isDownloading) {
        // Remove existing classes
        this.widget.classList.remove("high-queue", "medium-queue", "low-queue");

        // Add class based on queue size
        if (queueSize > 10) {
            this.widget.classList.add("high-queue");
        } else if (queueSize > 5) {
            this.widget.classList.add("medium-queue");
        } else if (queueSize > 0) {
            this.widget.classList.add("low-queue");
        }

        // Add downloading class if active
        if (isDownloading) {
            this.widget.classList.add("downloading");
        } else {
            this.widget.classList.remove("downloading");
        }
    }

    displayError() {
        this.indicator.className = "download-indicator error";
        this.text.textContent = "Status unavailable";
        this.widget.title =
            "Failed to get download status. Click to view stats page.";
    }

    show() {
        if (!this.isVisible) {
            this.widget.style.display = "flex";
            this.isVisible = true;
            this.startUpdates();
        }
    }

    hide() {
        if (this.isVisible) {
            this.widget.style.display = "none";
            this.isVisible = false;
            this.stopUpdates();
        }
    }

    destroy() {
        this.stopUpdates();
        if (this.widget) {
            this.widget.removeEventListener("click", this.handleClick);
        }
    }
}

// Enhanced styles for the widget states
const additionalStyles = `
<style>
.download-widget.downloading {
    background: rgba(76, 175, 80, 0.1);
    border-color: #4caf50;
}

.download-widget.high-queue {
    background: rgba(255, 152, 0, 0.1);
    border-color: #ff9800;
}

.download-widget.medium-queue {
    background: rgba(33, 150, 243, 0.1);
    border-color: #2196f3;
}

.download-widget.low-queue {
    background: rgba(156, 39, 176, 0.1);
    border-color: #9c27b0;
}

.download-indicator.error {
    background: #f44336;
    animation: blink 1s infinite;
}

@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0.3; }
}

.download-widget:hover .download-indicator.active {
    animation-duration: 1s;
}

/* Tooltip enhancement */
.download-widget::after {
    content: attr(title);
    position: absolute;
    bottom: 100%;
    left: 50%;
    transform: translateX(-50%);
    background: var(--bg-modal);
    color: var(--text-primary);
    padding: 6px 10px;
    border-radius: var(--radius-small);
    font-size: 0.75em;
    white-space: nowrap;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.3s;
    z-index: 1000;
    border: 1px solid var(--accent-color);
}

.download-widget:hover::after {
    opacity: 1;
}

/* Mobile responsive tooltip */
@media (max-width: 768px) {
    .download-widget::after {
        display: none;
    }
}
</style>
`;

// Initialize widget when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
    // Add additional styles
    document.head.insertAdjacentHTML("beforeend", additionalStyles);

    // Initialize the widget
    const downloadWidget = new DownloadStatusWidget();

    // Make it globally accessible for debugging
    window.downloadWidget = downloadWidget;

    // Auto-refresh page data every 30 seconds if on main pages
    const currentPath = window.location.pathname;
    const mainPages = ["/", "/shorts", "/most_recent_videos"];

    if (mainPages.includes(currentPath)) {
        setInterval(() => {
            // Refresh queue size display in the RSS section
            updateRSSQueueDisplay();
        }, 30000);
    }
});

// Function to update RSS queue display (integrates with existing RSS refresh)
async function updateRSSQueueDisplay() {
    try {
        const response = await fetch("/api/download_status/widget");
        if (response.ok) {
            const data = await response.json();
            const queueSize = data.queue_size || 0;
            const isDownloading = data.is_downloading || false;

            // Update any existing queue size displays in the RSS section
            const rssRefElement = document.getElementById("rss_ref");
            if (rssRefElement) {
                const text = rssRefElement.textContent;
                // Update the queue number if it exists in the text
                if (text.includes("Queue:")) {
                    const parts = text.split("Queue:");
                    if (parts.length === 2) {
                        rssRefElement.textContent = `${parts[0].trim()}Queue: ${queueSize}`;
                    }
                }

                // Update the active class based on downloading status
                if (isDownloading) {
                    rssRefElement.classList.add("active");
                } else {
                    rssRefElement.classList.remove("active");
                }
            }
        }
    } catch (error) {
        console.debug("Failed to update RSS queue display:", error);
    }
}

// Keyboard shortcut to toggle widget visibility
document.addEventListener("keydown", function (event) {
    // Ctrl+Shift+D to toggle download widget
    if (
        event.ctrlKey &&
        event.shiftKey &&
        (event.key === "D" || event.key === "d")
    ) {
        event.preventDefault();
        if (window.downloadWidget) {
            if (window.downloadWidget.isVisible) {
                window.downloadWidget.hide();
            } else {
                window.downloadWidget.show();
            }
        }
    }
});

// Export for potential external use
window.DownloadStatusWidget = DownloadStatusWidget;
