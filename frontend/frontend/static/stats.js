// Stats page JavaScript for real-time monitoring and updates

let autoRefreshInterval = null;
let isAutoRefreshEnabled = false;
const REFRESH_INTERVAL = 10000; // 10 seconds

// Initialize the stats page
document.addEventListener('DOMContentLoaded', function() {
    initializeProgressCircles();
    updateLastUpdatedTime();
    setupEventListeners();

    // Auto-refresh every 10 seconds if enabled
    setupAutoRefresh();
});

function setupEventListeners() {
    // Refresh button
    const refreshBtn = document.getElementById('refresh-stats');
    if (refreshBtn) {
        refreshBtn.addEventListener('click', refreshStats);
    }

    // Auto-refresh toggle
    const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
    if (autoRefreshToggle) {
        autoRefreshToggle.addEventListener('click', toggleAutoRefresh);
    }
}

function initializeProgressCircles() {
    // Set CSS custom properties for progress circles based on data attributes
    const progressCircles = document.querySelectorAll('.progress-circle[data-percentage]');

    progressCircles.forEach(circle => {
        const percentage = parseFloat(circle.getAttribute('data-percentage'));

        // Set CSS custom property for the conic gradient
        circle.style.setProperty('--percentage', percentage);

        // Set color based on percentage
        let color;
        if (percentage < 50) {
            color = '#4CAF50'; // Green for low usage
        } else if (percentage < 80) {
            color = '#FF9800'; // Orange for medium usage
        } else {
            color = '#f44336'; // Red for high usage
        }

        // Update the conic gradient
        circle.style.background = `conic-gradient(
            ${color} 0deg,
            ${color} ${percentage * 3.6}deg,
            var(--bg-tertiary) ${percentage * 3.6}deg,
            var(--bg-tertiary) 360deg
        )`;
    });
}

function updateSuccessRateColors() {
    // Update success rate colors based on values
    const successRates = document.querySelectorAll('.success-rate[data-rate]');

    successRates.forEach(element => {
        const rate = parseFloat(element.getAttribute('data-rate'));

        if (rate >= 90) {
            element.style.backgroundColor = '#4CAF50'; // Green
        } else if (rate >= 70) {
            element.style.backgroundColor = '#FF9800'; // Orange
        } else {
            element.style.backgroundColor = '#f44336'; // Red
        }
    });
}

function updateLastUpdatedTime() {
    const lastUpdatedElement = document.getElementById('last-updated');
    if (lastUpdatedElement) {
        const now = new Date();
        lastUpdatedElement.textContent = now.toLocaleTimeString();
    }
}

async function refreshStats() {
    const refreshBtn = document.getElementById('refresh-stats');

    // Show loading state
    if (refreshBtn) {
        refreshBtn.style.opacity = '0.6';
        refreshBtn.style.pointerEvents = 'none';
    }

    try {
        // Fetch fresh data from the API
        const response = await fetch('/api/stats/live');

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Update the page with new data
        updateStatsDisplay(data);
        updateLastUpdatedTime();

        // Show success feedback
        showNotification('Stats updated successfully', 'success');

    } catch (error) {
        console.error('Failed to refresh stats:', error);
        showNotification('Failed to refresh stats', 'error');
    } finally {
        // Restore button state
        if (refreshBtn) {
            refreshBtn.style.opacity = '1';
            refreshBtn.style.pointerEvents = 'auto';
        }
    }
}

function updateStatsDisplay(data) {
    // Update download status
    updateElement('queue-size', data.download_status?.queue_size || 0);
    updateElement('active-downloads', data.download_status?.active_downloads || 0);

    // Update download status indicator
    const statusElement = document.querySelector('.stat-value.downloading, .stat-value.idle');
    if (statusElement) {
        const isDownloading = data.download_status?.is_downloading;
        statusElement.textContent = isDownloading ? 'Active' : 'Idle';
        statusElement.className = `stat-value ${isDownloading ? 'downloading' : 'idle'}`;
    }

    // Update health status
    updateHealthStatus(data.health_status);

    // Update system resources
    updateSystemResources(data.system_status?.system);

    // Update progress circles
    initializeProgressCircles();

    // Update success rate colors
    updateSuccessRateColors();
}

function updateElement(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.textContent = value;
    }
}

function updateHealthStatus(healthData) {
    if (!healthData) return;

    // Update health status indicator
    const statusElements = document.querySelectorAll('.health-status');
    statusElements.forEach(element => {
        const indicator = element.querySelector('.status-indicator');
        const text = element.querySelector('span');

        if (indicator && text) {
            // Update classes
            element.className = `health-status ${healthData.status === 'healthy' ? 'healthy' : 'unhealthy'}`;
            text.textContent = healthData.status ? healthData.status.charAt(0).toUpperCase() + healthData.status.slice(1) : 'Unknown';
        }
    });

    // Update health score
    const scoreElement = document.querySelector('.score-value');
    if (scoreElement && healthData.system?.health_score !== undefined) {
        scoreElement.textContent = `${healthData.system.health_score.toFixed(1)}/100`;
    }
}

function updateSystemResources(systemData) {
    if (!systemData) return;

    // Update CPU progress circle
    if (systemData.cpu_percent !== undefined) {
        updateProgressCircle('cpu', systemData.cpu_percent);
    }

    // Update memory progress circle
    if (systemData.memory?.percent_used !== undefined) {
        updateProgressCircle('memory', systemData.memory.percent_used);
    }

    // Update disk progress circle
    if (systemData.disk?.percent_used !== undefined) {
        updateProgressCircle('disk', systemData.disk.percent_used);
    }
}

function updateProgressCircle(type, percentage) {
    // Find progress circle by looking for one that contains the type in its heading
    const resourceCards = document.querySelectorAll('.resource-card');

    resourceCards.forEach(card => {
        const heading = card.querySelector('h3');
        if (heading && heading.textContent.toLowerCase().includes(type)) {
            const circle = card.querySelector('.progress-circle');
            const text = card.querySelector('.progress-text');

            if (circle && text) {
                circle.setAttribute('data-percentage', percentage);
                text.textContent = `${percentage.toFixed(1)}%`;
            }
        }
    });
}

function setupAutoRefresh() {
    // Check if auto-refresh should be enabled by default
    const savedState = localStorage.getItem('stats-auto-refresh');
    if (savedState === 'enabled') {
        enableAutoRefresh();
    }
}

function toggleAutoRefresh() {
    if (isAutoRefreshEnabled) {
        disableAutoRefresh();
    } else {
        enableAutoRefresh();
    }
}

function enableAutoRefresh() {
    isAutoRefreshEnabled = true;

    const toggleBtn = document.getElementById('auto-refresh-toggle');
    if (toggleBtn) {
        toggleBtn.textContent = 'Auto-refresh: ON';
        toggleBtn.classList.add('active');
    }

    // Start the interval
    autoRefreshInterval = setInterval(refreshStats, REFRESH_INTERVAL);

    // Save state
    localStorage.setItem('stats-auto-refresh', 'enabled');

    showNotification('Auto-refresh enabled', 'info');
}

function disableAutoRefresh() {
    isAutoRefreshEnabled = false;

    const toggleBtn = document.getElementById('auto-refresh-toggle');
    if (toggleBtn) {
        toggleBtn.textContent = 'Auto-refresh: OFF';
        toggleBtn.classList.remove('active');
    }

    // Clear the interval
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }

    // Save state
    localStorage.setItem('stats-auto-refresh', 'disabled');

    showNotification('Auto-refresh disabled', 'info');
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;

    // Style the notification
    Object.assign(notification.style, {
        position: 'fixed',
        top: '20px',
        right: '20px',
        padding: '12px 20px',
        borderRadius: '6px',
        color: 'white',
        fontWeight: 'bold',
        zIndex: '10000',
        opacity: '0',
        transform: 'translateX(100%)',
        transition: 'all 0.3s ease-in-out'
    });

    // Set background color based on type
    switch (type) {
        case 'success':
            notification.style.backgroundColor = '#4CAF50';
            break;
        case 'error':
            notification.style.backgroundColor = '#f44336';
            break;
        case 'warning':
            notification.style.backgroundColor = '#FF9800';
            break;
        default:
            notification.style.backgroundColor = '#2196F3';
    }

    // Add to page
    document.body.appendChild(notification);

    // Animate in
    setTimeout(() => {
        notification.style.opacity = '1';
        notification.style.transform = 'translateX(0)';
    }, 100);

    // Remove after 3 seconds
    setTimeout(() => {
        notification.style.opacity = '0';
        notification.style.transform = 'translateX(100%)';

        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }, 3000);
}

// Handle visibility change to pause/resume auto-refresh when tab is not active
document.addEventListener('visibilitychange', function() {
    if (document.hidden) {
        // Tab is not active, pause auto-refresh
        if (autoRefreshInterval) {
            clearInterval(autoRefreshInterval);
        }
    } else {
        // Tab is active again, resume auto-refresh if it was enabled
        if (isAutoRefreshEnabled && !autoRefreshInterval) {
            autoRefreshInterval = setInterval(refreshStats, REFRESH_INTERVAL);
        }
    }
});

// Handle page unload to clean up
window.addEventListener('beforeunload', function() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // R key to refresh
    if (event.key === 'r' || event.key === 'R') {
        if (!event.ctrlKey && !event.metaKey) { // Don't interfere with browser refresh
            event.preventDefault();
            refreshStats();
        }
    }

    // A key to toggle auto-refresh
    if (event.key === 'a' || event.key === 'A') {
        if (!event.ctrlKey && !event.metaKey) {
            event.preventDefault();
            toggleAutoRefresh();
        }
    }
});

// Add keyboard shortcuts help tooltip
function showKeyboardShortcuts() {
    const help = document.createElement('div');
    help.innerHTML = `
        <div style="position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%);
                    background: var(--bg-modal); padding: 20px; border-radius: 8px;
                    border: 2px solid var(--accent-color); z-index: 10001; color: var(--text-primary);">
            <h3 style="margin-top: 0; color: var(--primary-color);">Keyboard Shortcuts</h3>
            <p><strong>R</strong> - Refresh stats</p>
            <p><strong>A</strong> - Toggle auto-refresh</p>
            <p><strong>?</strong> - Show this help</p>
            <button onclick="this.parentElement.parentElement.remove()"
                    style="background: var(--primary-color); color: white; border: none;
                           padding: 8px 16px; border-radius: 4px; cursor: pointer; margin-top: 10px;">
                Close
            </button>
        </div>
        <div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%;
                    background: rgba(0,0,0,0.5); z-index: 10000;"
             onclick="this.parentElement.remove()"></div>
    `;
    document.body.appendChild(help);
}

// ? key to show help
document.addEventListener('keydown', function(event) {
    if (event.key === '?' || (event.shiftKey && event.key === '/')) {
        event.preventDefault();
        showKeyboardShortcuts();
    }
});

// Export functions for potential external use
window.StatsPage = {
    refresh: refreshStats,
    toggleAutoRefresh: toggleAutoRefresh,
    showNotification: showNotification
};
