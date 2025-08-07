// Enhanced keyboard controls with help overlay
var helpOverlay = null;
var helpVisible = false;

// Initialize keyboard controls help system
function initializeKeyboardHelp() {
    createHelpOverlay();
    setupHelpToggle();
}

function createHelpOverlay() {
    helpOverlay = document.createElement("div");
    helpOverlay.id = "keyboard-help-overlay";
    helpOverlay.className = "keyboard-help-overlay";
    helpOverlay.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0, 0, 0, 0.9);
        backdrop-filter: blur(5px);
        z-index: 10000;
        display: none;
        justify-content: center;
        align-items: center;
        animation: fadeIn 0.3s ease;
    `;

    var helpContent = document.createElement("div");
    helpContent.className = "keyboard-help-content";
    helpContent.style.cssText = `
        background: linear-gradient(135deg, var(--bg-modal) 0%, var(--bg-tertiary) 100%);
        border-radius: var(--radius-large);
        padding: 40px;
        max-width: 600px;
        max-height: 80vh;
        overflow-y: auto;
        box-shadow: var(--shadow-modal);
        border: 2px solid var(--border-primary);
        position: relative;
        animation: slideInUp 0.4s ease;
    `;

    var closeButton = document.createElement("button");
    closeButton.innerHTML = "&times;";
    closeButton.style.cssText = `
        position: absolute;
        top: 15px;
        right: 20px;
        background: none;
        border: none;
        font-size: 32px;
        color: var(--text-muted);
        cursor: pointer;
        padding: 5px;
        border-radius: 50%;
        width: 45px;
        height: 45px;
        display: flex;
        align-items: center;
        justify-content: center;
        transition: all var(--transition-fast);
    `;

    closeButton.addEventListener("mouseenter", function () {
        this.style.background = "var(--danger-color)";
        this.style.color = "var(--text-primary)";
        this.style.transform = "scale(1.1)";
    });

    closeButton.addEventListener("mouseleave", function () {
        this.style.background = "none";
        this.style.color = "var(--text-muted)";
        this.style.transform = "scale(1)";
    });

    closeButton.addEventListener("click", hideKeyboardHelp);

    var title = document.createElement("h2");
    title.textContent = "Keyboard Shortcuts";
    title.style.cssText = `
        color: var(--text-primary);
        margin-bottom: 30px;
        font-size: var(--font-size-2xl);
        text-align: center;
        border-bottom: 2px solid var(--primary-color);
        padding-bottom: 15px;
    `;

    var shortcuts = [
        { keys: ["Space", "K"], description: "Play/Pause video" },
        { keys: ["←", "→"], description: "Skip backward/forward 5 seconds" },
        { keys: ["J", "L"], description: "Skip backward/forward 10 seconds" },
        { keys: ["<", ">"], description: "Skip backward/forward 1 second" },
        { keys: ["↑", "↓"], description: "Volume up/down" },
        { keys: ["M"], description: "Mute/Unmute" },
        { keys: ["F"], description: "Toggle fullscreen" },
        { keys: ["P"], description: "Picture-in-Picture (if supported)" },
        { keys: ["C"], description: "Toggle captions" },
        { keys: ["?", "H"], description: "Show/hide this help" },
        { keys: ["Esc"], description: "Close modals/help" },
    ];

    var shortcutsList = document.createElement("div");
    shortcutsList.style.cssText = `
        display: grid;
        gap: 15px;
        grid-template-columns: 1fr;
    `;

    shortcuts.forEach(function (shortcut) {
        var item = document.createElement("div");
        item.style.cssText = `
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px 20px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: var(--radius-medium);
            border-left: 4px solid var(--primary-color);
            transition: all var(--transition-fast);
        `;

        item.addEventListener("mouseenter", function () {
            this.style.background = "rgba(255, 255, 255, 0.1)";
            this.style.transform = "translateX(5px)";
        });

        item.addEventListener("mouseleave", function () {
            this.style.background = "rgba(255, 255, 255, 0.05)";
            this.style.transform = "translateX(0)";
        });

        var keysContainer = document.createElement("div");
        keysContainer.style.cssText = `
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
        `;

        shortcut.keys.forEach(function (key) {
            var keyElement = document.createElement("kbd");
            keyElement.textContent = key;
            keyElement.style.cssText = `
                background: var(--bg-secondary);
                color: var(--text-primary);
                padding: 6px 12px;
                border-radius: var(--radius-small);
                font-family: monospace;
                font-size: var(--font-size-sm);
                font-weight: 600;
                border: 1px solid var(--border-primary);
                box-shadow: var(--shadow-small);
                min-width: 30px;
                text-align: center;
            `;
            keysContainer.appendChild(keyElement);
        });

        var description = document.createElement("span");
        description.textContent = shortcut.description;
        description.style.cssText = `
            color: var(--text-secondary);
            font-size: var(--font-size-base);
            flex: 1;
            margin-left: 20px;
        `;

        item.appendChild(keysContainer);
        item.appendChild(description);
        shortcutsList.appendChild(item);
    });

    var tip = document.createElement("div");
    tip.innerHTML = `
        <strong>💡 Pro Tip:</strong> Most shortcuts work only when the video player area is focused and no modals are open.
    `;
    tip.style.cssText = `
        margin-top: 25px;
        padding: 15px;
        background: linear-gradient(135deg, rgba(199, 17, 17, 0.1) 0%, rgba(199, 17, 17, 0.05) 100%);
        border-radius: var(--radius-medium);
        color: var(--text-secondary);
        font-size: var(--font-size-sm);
        text-align: center;
        border: 1px solid rgba(199, 17, 17, 0.2);
    `;

    helpContent.appendChild(closeButton);
    helpContent.appendChild(title);
    helpContent.appendChild(shortcutsList);
    helpContent.appendChild(tip);
    helpOverlay.appendChild(helpContent);

    document.body.appendChild(helpOverlay);

    // Add CSS animations
    if (!document.getElementById("keyboard-help-styles")) {
        var styles = document.createElement("style");
        styles.id = "keyboard-help-styles";
        styles.textContent = `
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }

            @keyframes slideInUp {
                from {
                    transform: translateY(50px);
                    opacity: 0;
                }
                to {
                    transform: translateY(0);
                    opacity: 1;
                }
            }

            .keyboard-help-overlay {
                scrollbar-width: thin;
                scrollbar-color: var(--primary-color) var(--bg-tertiary);
            }

            .keyboard-help-overlay::-webkit-scrollbar {
                width: 8px;
            }

            .keyboard-help-overlay::-webkit-scrollbar-track {
                background: var(--bg-tertiary);
                border-radius: var(--radius-small);
            }

            .keyboard-help-overlay::-webkit-scrollbar-thumb {
                background: var(--primary-color);
                border-radius: var(--radius-small);
            }

            .keyboard-help-overlay::-webkit-scrollbar-thumb:hover {
                background: var(--primary-color-hover);
            }

            @media screen and (max-width: 768px) {
                .keyboard-help-content {
                    margin: 20px;
                    padding: 25px 20px;
                    max-height: 90vh;
                }

                .keyboard-help-content h2 {
                    font-size: var(--font-size-xl);
                    margin-bottom: 20px;
                }

                .keyboard-help-content div[style*="grid"] > div {
                    padding: 12px 15px;
                }

                .keyboard-help-content kbd {
                    padding: 4px 8px;
                    font-size: var(--font-size-xs);
                    min-width: 25px;
                }
            }

            @media screen and (max-width: 480px) {
                .keyboard-help-content {
                    margin: 10px;
                    padding: 20px 15px;
                }

                .keyboard-help-content div[style*="flex"] {
                    flex-direction: column;
                    align-items: flex-start;
                    gap: 10px;
                }

                .keyboard-help-content span {
                    margin-left: 0 !important;
                }
            }
        `;
        document.head.appendChild(styles);
    }
}

function setupHelpToggle() {
    // Listen for help key combinations
    document.addEventListener("keydown", function (event) {
        // Don't trigger in input fields or when modals are open
        if (
            event.target.tagName === "INPUT" ||
            event.target.tagName === "TEXTAREA" ||
            event.target.closest(".modal:not(#keyboard-help-overlay)") !==
                null ||
            document.querySelector(
                '.modal[style*="block"]:not(#keyboard-help-overlay)',
            ) !== null
        ) {
            return;
        }

        // ? key (shift + /) or H key
        if ((event.keyCode === 191 && event.shiftKey) || event.keyCode === 72) {
            event.preventDefault();
            toggleKeyboardHelp();
        }

        // Escape key to close help
        if (event.keyCode === 27 && helpVisible) {
            event.preventDefault();
            hideKeyboardHelp();
        }
    });

    // Click outside to close
    if (helpOverlay) {
        helpOverlay.addEventListener("click", function (event) {
            if (event.target === helpOverlay) {
                hideKeyboardHelp();
            }
        });
    }
}

function toggleKeyboardHelp() {
    if (helpVisible) {
        hideKeyboardHelp();
    } else {
        showKeyboardHelp();
    }
}

function showKeyboardHelp() {
    if (!helpOverlay) return;

    helpOverlay.style.display = "flex";
    helpVisible = true;

    // Focus the help overlay for accessibility
    helpOverlay.setAttribute("tabindex", "-1");
    helpOverlay.focus();

    // Prevent body scroll
    document.body.style.overflow = "hidden";

    // Add escape key handler specifically for this overlay
    var escapeHandler = function (event) {
        if (event.keyCode === 27) {
            hideKeyboardHelp();
            document.removeEventListener("keydown", escapeHandler);
        }
    };
    document.addEventListener("keydown", escapeHandler);
}

function hideKeyboardHelp() {
    if (!helpOverlay) return;

    helpOverlay.style.display = "none";
    helpVisible = false;

    // Restore body scroll
    document.body.style.overflow = "";

    // Return focus to video player if it exists
    var player = document.getElementById("video_player");
    if (player) {
        player.focus();
    }
}

// Add visual indicator for keyboard shortcuts availability
function addKeyboardHelpIndicator() {
    var indicator = document.createElement("div");
    indicator.id = "keyboard-help-indicator";
    indicator.innerHTML = "⌨️ Press <kbd>?</kbd> for shortcuts";
    indicator.style.cssText = `
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: var(--bg-modal);
        color: var(--text-secondary);
        padding: 8px 12px;
        border-radius: var(--radius-medium);
        font-size: var(--font-size-xs);
        border: 1px solid var(--border-primary);
        cursor: pointer;
        transition: all var(--transition-fast);
        z-index: 1000;
        opacity: 0.7;
        user-select: none;
    `;

    indicator.querySelector("kbd").style.cssText = `
        background: var(--bg-secondary);
        padding: 2px 6px;
        border-radius: var(--radius-small);
        font-family: monospace;
        font-size: inherit;
        margin: 0 2px;
    `;

    indicator.addEventListener("mouseenter", function () {
        this.style.opacity = "1";
        this.style.transform = "translateY(-2px)";
    });

    indicator.addEventListener("mouseleave", function () {
        this.style.opacity = "0.7";
        this.style.transform = "translateY(0)";
    });

    indicator.addEventListener("click", showKeyboardHelp);

    document.body.appendChild(indicator);

    // Hide indicator after 5 seconds, show on hover over video
    setTimeout(function () {
        if (indicator.parentNode) {
            indicator.style.opacity = "0.3";
            indicator.style.transform = "translateY(10px)";
        }
    }, 5000);

    var player = document.getElementById("video_player");
    if (player) {
        player.addEventListener("mouseenter", function () {
            indicator.style.opacity = "0.7";
            indicator.style.transform = "translateY(0)";
        });

        player.addEventListener("mouseleave", function () {
            setTimeout(function () {
                indicator.style.opacity = "0.3";
                indicator.style.transform = "translateY(10px)";
            }, 2000);
        });
    }
}

// Enhanced keyboard navigation for accessibility
function enhanceKeyboardNavigation() {
    // Make video player focusable
    var player = document.getElementById("video_player");
    if (player) {
        player.setAttribute("tabindex", "0");

        // Add visual focus indicator
        player.addEventListener("focus", function () {
            this.style.outline = "3px solid var(--primary-color)";
            this.style.outlineOffset = "3px";
        });

        player.addEventListener("blur", function () {
            this.style.outline = "none";
        });
    }

    // Enhance modal navigation
    var modals = document.querySelectorAll(".modal");
    modals.forEach(function (modal) {
        // Trap focus within modal when open
        modal.addEventListener("keydown", function (event) {
            if (event.keyCode === 9) {
                // Tab key
                var focusableElements = modal.querySelectorAll(
                    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
                );

                var firstElement = focusableElements[0];
                var lastElement =
                    focusableElements[focusableElements.length - 1];

                if (event.shiftKey && document.activeElement === firstElement) {
                    event.preventDefault();
                    lastElement.focus();
                } else if (
                    !event.shiftKey &&
                    document.activeElement === lastElement
                ) {
                    event.preventDefault();
                    firstElement.focus();
                }
            }
        });
    });
}

// Initialize everything when DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
    initializeKeyboardHelp();
    addKeyboardHelpIndicator();
    enhanceKeyboardNavigation();
});

// Initialize if DOM already loaded
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
        initializeKeyboardHelp();
        addKeyboardHelpIndicator();
        enhanceKeyboardNavigation();
    });
} else {
    initializeKeyboardHelp();
    addKeyboardHelpIndicator();
    enhanceKeyboardNavigation();
}

// Export functions for potential external use
window.keyboardControls = {
    showHelp: showKeyboardHelp,
    hideHelp: hideKeyboardHelp,
    toggleHelp: toggleKeyboardHelp,
};
