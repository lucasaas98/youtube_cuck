// Ultra-fast minimalist hamburger menu - zero animations, maximum performance
document.addEventListener("DOMContentLoaded", function () {
    const hamburger = document.getElementById("hamburger-menu");
    const navMenu = document.getElementById("nav-menu");

    if (!hamburger || !navMenu) {
        return;
    }

    // Instant toggle - no animations
    function toggleMenu() {
        const isOpen = hamburger.classList.contains("active");

        if (isOpen) {
            hamburger.classList.remove("active");
            navMenu.classList.remove("active");
            navMenu.style.display = "none";
        } else {
            hamburger.classList.add("active");
            navMenu.classList.add("active");
            navMenu.style.display = "flex";
        }
    }

    // Click to toggle
    hamburger.addEventListener("click", function (event) {
        event.stopPropagation();
        toggleMenu();
    });

    // Close when clicking outside
    document.addEventListener("click", function (event) {
        if (
            !hamburger.contains(event.target) &&
            !navMenu.contains(event.target) &&
            hamburger.classList.contains("active")
        ) {
            toggleMenu();
        }
    });

    // Close when clicking nav links
    navMenu.addEventListener("click", function (event) {
        if (event.target.tagName === "A") {
            toggleMenu();
        }
    });

    // Close on escape key
    document.addEventListener("keydown", function (event) {
        if (event.key === "Escape" && hamburger.classList.contains("active")) {
            toggleMenu();
        }
    });

    // Close menu on window resize to desktop
    window.addEventListener("resize", function () {
        if (window.innerWidth > 768 && hamburger.classList.contains("active")) {
            toggleMenu();
        }
    });
});
