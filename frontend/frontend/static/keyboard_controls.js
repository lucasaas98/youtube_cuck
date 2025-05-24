document.addEventListener('keydown', function(event) {
    // Only handle keypress if we're not in an input field
    if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA') {
        return;
    }

    // Convert key to lowercase for case-insensitive comparison
    const key = event.key.toLowerCase();

    // Determine if we're in a paginated view
    const inPaginatedView = window.location.pathname.includes('/page/');
    const prefix = inPaginatedView ? '../' : '';

    switch (key) {
        case 'a':
            // Open add channel modal
            const addButton = document.getElementById('add');
            if (addButton) {
                addButton.click();
            }
            break;

        case 'c':
            // Go to continue page
            window.location.href = prefix + 'most_recent_video';
            break;

        case 'h':
            // Go to home page
            window.location.href = inPaginatedView ? '../' : '/';
            break;

        case 'y':
            // Go to history (yesterdaY)
            window.location.href = prefix + 'most_recent_videos';
            break;

        case 's':
            // Go to subscriptions
            window.location.href = prefix + 'subs';
            break;

        case 't':
            // Go to shorTs
            window.location.href = prefix + 'shorts';
            break;

        case 'p':
            // Go to playlists
            window.location.href = prefix + 'playlist';
            break;
        case '1':
        case '2':
        case '3':
        case '4':
        case '5':
        case '6':
        case '7':
        case '8':
        case '9':
            const inHomePage = window.location.href.endsWith('/');
            if(inHomePage) {
                window.location.href = prefix + 'push_' + key;
            }
            break;
    }
});