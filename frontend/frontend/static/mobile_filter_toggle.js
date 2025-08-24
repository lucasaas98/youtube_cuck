// Mobile filter toggle functionality
document.addEventListener("DOMContentLoaded", function () {
    const toggleBtn = document.getElementById("filter-toggle");
    const filterContent = document.getElementById("filter-content");
    const toggleArrow = toggleBtn.querySelector(".filter-toggle-arrow");

    // Check if we're on mobile (based on screen width)
    function isMobileView() {
        return window.innerWidth <= 768;
    }

    // Initialize the filter state based on viewport
    function initializeFilterState() {
        if (isMobileView()) {
            // On mobile, start collapsed unless there are active filters
            const hasActiveFilters = checkForActiveFilters();
            if (hasActiveFilters) {
                showFilters();
            } else {
                hideFilters();
            }
            // Store the initial mobile state
            localStorage.setItem(
                "mobile-filters-collapsed",
                hasActiveFilters ? "false" : "true",
            );
        } else {
            // On desktop, always show filters
            showFilters();
        }
    }

    // Check if there are any active filters
    function checkForActiveFilters() {
        const urlParams = new URLSearchParams(window.location.search);
        const search = urlParams.get("search");
        const sortBy = urlParams.get("sort_by");
        const sortOrder = urlParams.get("sort_order");
        const filterKept = urlParams.get("filter_kept");
        const includeShorts = urlParams.get("include_shorts");

        return (
            search ||
            (sortBy && sortBy !== "downloaded_at") ||
            (sortOrder && sortOrder !== "desc") ||
            filterKept ||
            (includeShorts && includeShorts !== "true")
        );
    }

    // Show filters
    function showFilters() {
        filterContent.classList.add("show");
        toggleBtn.classList.add("active");
        toggleBtn.setAttribute("aria-expanded", "true");
        if (isMobileView()) {
            localStorage.setItem("mobile-filters-collapsed", "false");
        }
    }

    // Hide filters
    function hideFilters() {
        filterContent.classList.remove("show");
        toggleBtn.classList.remove("active");
        toggleBtn.setAttribute("aria-expanded", "false");
        if (isMobileView()) {
            localStorage.setItem("mobile-filters-collapsed", "true");
        }
    }

    // Toggle filter visibility
    function toggleFilters() {
        if (filterContent.classList.contains("show")) {
            hideFilters();
        } else {
            showFilters();
        }
    }

    // Handle toggle button click
    toggleBtn.addEventListener("click", function (e) {
        e.preventDefault();
        e.stopPropagation();
        toggleFilters();
    });

    // Handle window resize to adjust filter visibility
    let resizeTimeout;
    window.addEventListener("resize", function () {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(function () {
            initializeFilterState();
        }, 150);
    });

    // Accessibility: Handle keyboard navigation
    toggleBtn.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            toggleFilters();
        }
    });

    // Add accessibility attributes
    toggleBtn.setAttribute("aria-controls", "filter-content");
    toggleBtn.setAttribute("role", "button");
    filterContent.setAttribute("aria-labelledby", "filter-toggle");

    // Auto-collapse filters on mobile after applying filters
    // This helps save screen space after user makes their selection
    const filterControls = [
        document.getElementById("search-btn"),
        document.getElementById("clear-search-btn"),
        document.getElementById("sort-by"),
        document.getElementById("sort-order"),
        document.getElementById("filter-kept"),
        document.getElementById("include-shorts"),
    ];

    filterControls.forEach(function (control) {
        if (control) {
            control.addEventListener("change", function () {
                // Don't auto-collapse on change, let user keep it open if they want
                // They can manually close it using the toggle button
            });

            // Handle click events for buttons
            if (control.tagName === "BUTTON") {
                control.addEventListener("click", function () {
                    // Auto-collapse after search/clear actions
                    setTimeout(function () {
                        if (isMobileView()) {
                            hideFilters();
                        }
                    }, 200);
                });
            }
        }
    });

    // Initialize on page load
    initializeFilterState();

    // Update toggle button text to show active filter count
    function updateToggleButtonText() {
        const hasActiveFilters = checkForActiveFilters();
        const toggleText = toggleBtn.querySelector(".filter-toggle-text");

        if (hasActiveFilters) {
            toggleText.textContent = "Search & Filters (Active)";
            toggleBtn.style.backgroundColor = "var(--warning-color)";
        } else {
            toggleText.textContent = "Search & Filters";
            toggleBtn.style.backgroundColor = "var(--btn-primary-bg)";
        }
    }

    // Update button text on load
    updateToggleButtonText();
});
