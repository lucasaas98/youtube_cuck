var player = document.getElementById("video_player");
// Initialize enhanced video player
// window.onload = function () {
//     initializeChapters();
//     setupKeyboardControls();
//     setupProgressSaving();
// };

window.onload = function () {
    // Setup auto-scroll on play functionality
    setupAutoScrollOnPlay();

    window.onkeydown = function (gfg) {
        gfg.preventDefault();
        handleKeyPress(gfg);
    };

    // f = 70;l = 76;k = 75;j = 74;down_arrow = 40;up_arrow = 38;left_arrow = 37;right_arrow = 39;space_bar = 32;
    function handleKeyPress(gfg) {
        // if (
        //     gfg.target.tagName === "INPUT" ||
        //     gfg.target.tagName === "TEXTAREA" ||
        //     gfg.target.closest(".modal") !== null ||
        //     gfg.target.closest(".modal-content") !== null ||
        //     document.querySelector(".modal[style*='block']") !== null
        // ) {
        //     return;
        // }
        switch (gfg.keyCode) {
            case 32:
            case 75:
                if (!player.paused) {
                    player.pause();
                } else {
                    player.play();
                }
                break;
            case 39:
                player.currentTime = player.currentTime + 5;
                console.log("+5 secs");
                break;
            case 37:
                player.currentTime = player.currentTime - 5;
                console.log("-5 secs");
                break;
            case 74:
                player.currentTime = player.currentTime - 10;
                console.log("-10 secs");
                break;
            case 76:
                player.currentTime = player.currentTime + 10;
                console.log("+10 secs");
                break;
            case 70:
                if (!document.fullscreenElement) {
                    player.requestFullscreen();
                    console.log("Fullscreen");
                } else {
                    document.exitFullscreen();
                    console.log("Not fullscreen");
                }
                break;
            case 38:
                if (player.volume <= 0.95) {
                    player.volume = player.volume + 0.05;
                }
                break;
            case 40:
                if (player.volume >= 0.05) {
                    player.volume = player.volume - 0.05;
                }
                break;
        }
    }
};

function setupAutoScrollOnPlay() {
    if (!player) return;

    // Add play event listener to handle auto-scroll
    player.addEventListener("play", function () {
        // Check if video is out of view (user has scrolled down)
        const videoRect = player.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const navHeight =
            document.querySelector(".nav_bar")?.offsetHeight || 60;

        // If the video is completely above the viewport or mostly out of view
        // Also consider if we've scrolled significantly past the video
        const isVideoOutOfView =
            videoRect.bottom < navHeight || // Video is above the nav bar
            videoRect.top < -videoRect.height * 0.3 || // Video is mostly scrolled past
            window.scrollY > videoRect.height + navHeight; // We've scrolled significantly

        // Optional debug logging (uncomment for debugging)
        // console.log("Video play detected - checking scroll position:", {
        //     videoRect: videoRect,
        //     scrollY: window.scrollY,
        //     navHeight: navHeight,
        //     isVideoOutOfView: isVideoOutOfView
        // });

        if (isVideoOutOfView) {
            // Scroll to the video smoothly, accounting for nav bar
            const viewer = document.querySelector(".viewer");
            if (viewer) {
                const offsetTop = viewer.offsetTop - navHeight - 10; // 10px padding
                // console.log("Auto-scrolling to video at offset:", offsetTop);
                window.scrollTo({
                    top: Math.max(0, offsetTop),
                    behavior: "smooth",
                });
            }
        }
    });
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

function start_at(progress) {
    console.log("Starting at progress: " + progress);
    if (player && progress > 0) {
        player.currentTime = progress;
    }
}

function add_progress_listener(video_id) {
    window.currentVideoId = video_id;
    console.log("Progress tracking enabled for video ID:", video_id);
}

// Cleanup on page unload
window.addEventListener("beforeunload", function () {
    if (progressUpdateInterval) {
        clearInterval(progressUpdateInterval);
    }
});

// Chapter functionality
function parseChapters(description) {
    if (!description || typeof description !== "string") {
        console.log("No valid description provided for chapter parsing");
        return [];
    }

    console.log(
        "Parsing chapters from description:",
        description.substring(0, 200) + "...",
    );
    const chapters = [];
    const lines = description.split(/\r?\n/); // Handle both \n and \r\n

    for (const line of lines) {
        // Match timestamp patterns like "0:00", "12:06", "1:23:45"
        // Also handle potential whitespace variations
        const match = line.trim().match(/^(\d{1,2}:\d{2}(?::\d{2})?)\s+(.+)$/);
        if (match) {
            const timeString = match[1];
            const title = match[2].trim();

            // Skip if title is too short or empty
            if (title.length < 2) {
                continue;
            }

            console.log(`Found chapter: ${timeString} - ${title}`);

            // Convert time string to seconds
            const timeParts = timeString.split(":").map(Number);
            let seconds = 0;

            // Validate time parts are valid numbers
            if (timeParts.some(isNaN)) {
                console.warn(`Invalid time format: ${timeString}`);
                continue;
            }

            if (timeParts.length === 2) {
                // MM:SS format
                seconds = timeParts[0] * 60 + timeParts[1];
            } else if (timeParts.length === 3) {
                // HH:MM:SS format
                seconds =
                    timeParts[0] * 3600 + timeParts[1] * 60 + timeParts[2];
            } else {
                console.warn(`Unsupported time format: ${timeString}`);
                continue;
            }

            // Validate seconds are reasonable (not negative, not too large)
            if (seconds < 0 || seconds > 86400) {
                // Max 24 hours
                console.warn(
                    `Invalid timestamp: ${timeString} (${seconds} seconds)`,
                );
                continue;
            }

            chapters.push({
                time: seconds,
                timeString: timeString,
                title: title,
            });
        }
    }

    console.log(`Total chapters found: ${chapters.length}`);

    // Remove duplicate timestamps
    const uniqueChapters = chapters.filter(
        (chapter, index, arr) =>
            index === 0 || chapter.time !== arr[index - 1].time,
    );

    return uniqueChapters.sort((a, b) => a.time - b.time);
}

function createChapterList(chapters) {
    const chapterList = document.getElementById("chapter-list");
    const chapterItems = document.getElementById("chapter-items");

    if (!chapterList || !chapterItems) {
        console.warn("Chapter list elements not found in DOM");
        return;
    }

    if (chapters.length === 0) {
        chapterList.style.display = "none";
        return;
    }

    // Clear existing chapters
    chapterItems.innerHTML = "";

    chapters.forEach((chapter, index) => {
        const chapterItem = document.createElement("div");
        chapterItem.className = "chapter-item";
        chapterItem.dataset.time = chapter.time;
        chapterItem.dataset.index = index;
        chapterItem.setAttribute("tabindex", "0"); // Make keyboard accessible
        chapterItem.setAttribute("role", "button");
        chapterItem.setAttribute(
            "aria-label",
            `Jump to ${chapter.title} at ${chapter.timeString}`,
        );

        // Escape HTML in title to prevent XSS
        const escapedTitle = chapter.title
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#39;");

        chapterItem.innerHTML = `
            <span class="chapter-timestamp">${chapter.timeString}</span>
            <span class="chapter-title-text">${escapedTitle}</span>
        `;

        const clickHandler = () => {
            seekToChapter(chapter.time);
            updateActiveChapter(index);
            showNotification(`Jumped to: ${chapter.title}`, "info");
        };

        chapterItem.addEventListener("click", clickHandler);

        // Add keyboard support
        chapterItem.addEventListener("keydown", (e) => {
            if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                clickHandler();
            }
        });

        chapterItems.appendChild(chapterItem);
    });

    // Show the chapter list
    chapterList.style.display = "block";
    console.log(`Created chapter list with ${chapters.length} items`);
}

function seekToChapter(time) {
    if (!player) {
        console.warn("Video player not available for seeking");
        return;
    }

    try {
        // Ensure time is within video bounds
        const duration = player.duration;
        if (duration && time > duration) {
            console.warn(
                `Chapter time ${time}s exceeds video duration ${duration}s`,
            );
            time = Math.max(0, duration - 1);
        }

        player.currentTime = Math.max(0, time);

        // Only autoplay if user has interacted with video before
        if (player.paused && window.userHasInteracted) {
            player.play().catch((e) => {
                console.log("Autoplay prevented:", e);
            });
        }
    } catch (error) {
        console.error("Error seeking to chapter:", error);
        showNotification("Error jumping to chapter", "error");
    }
}

function updateActiveChapter(activeIndex) {
    const chapterItems = document.querySelectorAll(".chapter-item");
    chapterItems.forEach((item, index) => {
        if (index === activeIndex) {
            item.classList.add("active");
        } else {
            item.classList.remove("active");
        }
    });
}

function updateChapterProgress() {
    if (!player || !window.chapters || window.chapters.length === 0) return;

    const currentTime = player.currentTime;
    let activeChapterIndex = -1;

    // Find the current chapter based on video time
    for (let i = window.chapters.length - 1; i >= 0; i--) {
        if (currentTime >= window.chapters[i].time) {
            activeChapterIndex = i;
            break;
        }
    }

    if (
        activeChapterIndex !== -1 &&
        activeChapterIndex !== window.currentChapterIndex
    ) {
        updateActiveChapter(activeChapterIndex);
        window.currentChapterIndex = activeChapterIndex;
    }
}

function initializeChapters() {
    console.log("Initializing chapters...");

    // Wait a bit for DOM to be fully ready
    setTimeout(() => {
        const descriptionElement = document.getElementById(
            "description-content",
        );
        if (!descriptionElement) {
            console.log("Description element not found");
            return;
        }

        // Get the description text, handling different ways it might be stored
        let description =
            descriptionElement.textContent ||
            descriptionElement.innerText ||
            "";

        // If description is still empty, try getting it from data attributes or other sources
        if (!description.trim()) {
            const parentInfo = descriptionElement.closest(".info");
            if (parentInfo) {
                description =
                    parentInfo.textContent || parentInfo.innerText || "";
            }
        }

        console.log("Description text length:", description.length);

        if (!description.trim()) {
            console.log("No description text found");
            return;
        }

        // Parse chapters from description
        const chapters = parseChapters(description);

        if (chapters.length > 0) {
            console.log(
                `Found ${chapters.length} chapters, creating chapter list`,
            );
            window.chapters = chapters;
            window.currentChapterIndex = -1;

            createChapterList(chapters);

            // Add time update listener for chapter progress
            if (player) {
                // Remove existing listener to avoid duplicates
                player.removeEventListener("timeupdate", updateChapterProgress);
                player.addEventListener("timeupdate", updateChapterProgress);
                console.log("Added timeupdate listener for chapter progress");
            }

            // Track user interaction for autoplay
            if (!window.userHasInteracted) {
                const trackInteraction = () => {
                    window.userHasInteracted = true;
                    player.removeEventListener("play", trackInteraction);
                    player.removeEventListener("click", trackInteraction);
                };
                player.addEventListener("play", trackInteraction);
                player.addEventListener("click", trackInteraction);
            }
        } else {
            console.log("No chapters found in description");
            // Hide chapter list if it exists
            const chapterList = document.getElementById("chapter-list");
            if (chapterList) {
                chapterList.style.display = "none";
            }
        }
    }, 100);
}

// Initialize chapters when the page loads
document.addEventListener("DOMContentLoaded", function () {
    if (player) {
        initializeChapters();
        setupProgressSaving();
        setupAutoScrollOnPlay();
    }
});

// Initialize video enhancements
// addVideoEnhancements();
