// Simple video filtering functionality without AJAX
document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("search-input");
    const searchBtn = document.getElementById("search-btn");
    const clearBtn = document.getElementById("clear-search-btn");
    const sortBySelect = document.getElementById("sort-by");
    const sortOrderSelect = document.getElementById("sort-order");
    const filterKeptSelect = document.getElementById("filter-kept");
    const includeShortsCheckbox = document.getElementById("include-shorts");
    const includeDeletedCheckbox = document.getElementById("include-deleted");

    // Update sort order options based on sort by selection
    function updateSortOrderOptions() {
        const sortBy = sortBySelect.value;

        // Clear existing options
        sortOrderSelect.innerHTML = "";

        if (sortBy === "title") {
            // For title sorting
            sortOrderSelect.innerHTML = `
                <option value="asc">A to Z</option>
                <option value="desc">Z to A</option>
            `;
        } else if (sortBy === "views") {
            // For view count sorting
            sortOrderSelect.innerHTML = `
                <option value="desc">Most Views</option>
                <option value="asc">Least Views</option>
            `;
        } else {
            // For date-based sorting (downloaded_at, pub_date)
            sortOrderSelect.innerHTML = `
                <option value="desc">Newest First</option>
                <option value="asc">Oldest First</option>
            `;
        }

        // Try to maintain current selection if possible
        const urlParams = new URLSearchParams(window.location.search);
        const currentOrder = urlParams.get("sort_order") || "desc";
        if (sortOrderSelect.querySelector(`option[value="${currentOrder}"]`)) {
            sortOrderSelect.value = currentOrder;
        }
    }

    // Navigate to new URL with updated parameters
    function navigateWithFilters() {
        const url = new URL(window.location.origin + "/");

        // Add search parameter if present
        const searchValue = searchInput.value.trim();
        if (searchValue) {
            url.searchParams.set("search", searchValue);
        }

        // Add sorting parameters
        url.searchParams.set("sort_by", sortBySelect.value);
        url.searchParams.set("sort_order", sortOrderSelect.value);

        // Add filter parameters
        if (filterKeptSelect.value) {
            url.searchParams.set("filter_kept", filterKeptSelect.value);
        }

        url.searchParams.set("include_shorts", includeShortsCheckbox.checked);
        url.searchParams.set("include_deleted", includeDeletedCheckbox.checked);

        // Always reset to page 0 when filters change
        url.searchParams.delete("page");

        // Navigate to the new URL
        window.location.href = url.toString();
    }

    // Handle search button click
    searchBtn.addEventListener("click", function (e) {
        e.preventDefault();
        navigateWithFilters();
    });

    // Handle Enter key in search input
    searchInput.addEventListener("keypress", function (e) {
        if (e.key === "Enter") {
            e.preventDefault();
            navigateWithFilters();
        }
    });

    // Handle clear button
    clearBtn.addEventListener("click", function (e) {
        e.preventDefault();
        searchInput.value = "";
        navigateWithFilters();
    });

    // Handle filter changes
    sortBySelect.addEventListener("change", function () {
        updateSortOrderOptions();
        navigateWithFilters();
    });

    sortOrderSelect.addEventListener("change", function () {
        navigateWithFilters();
    });

    filterKeptSelect.addEventListener("change", function () {
        navigateWithFilters();
    });

    includeShortsCheckbox.addEventListener("change", function () {
        navigateWithFilters();
    });

    includeDeletedCheckbox.addEventListener("change", function () {
        navigateWithFilters();
    });

    // Initialize sort order options on page load
    updateSortOrderOptions();

    // Enhance pagination links to preserve filters
    function enhancePaginationLinks() {
        const paginationLinks = document.querySelectorAll(
            ".pagination-btn[href]",
        );
        paginationLinks.forEach((link) => {
            link.addEventListener("click", function (e) {
                e.preventDefault();

                // Get the page number from the href
                const href = this.getAttribute("href");
                let pageNum = 0;

                if (href !== "/") {
                    const match = href.match(/\/page\/(\d+)/);
                    if (match) {
                        pageNum = parseInt(match[1]);
                    }
                }

                // Build URL with current filters and new page
                const url = new URL(window.location.origin + "/");

                // Preserve current filters
                const currentParams = new URLSearchParams(
                    window.location.search,
                );
                currentParams.forEach((value, key) => {
                    if (key !== "page") {
                        url.searchParams.set(key, value);
                    }
                });

                // Add page parameter if not page 0
                if (pageNum > 0) {
                    url.searchParams.set("page", pageNum);
                }

                // Navigate to the new URL
                window.location.href = url.toString();
            });
        });
    }

    // Enhance pagination links after page load
    enhancePaginationLinks();
});
