var player = document.getElementById('video_player');

window.onload = function () {
    window.onkeydown = function (gfg) {
        gfg.preventDefault();
        handleKeyPress(gfg);
    };

    // f = 70;l = 76;k = 75;j = 74;down_arrow = 40;up_arrow = 38;left_arrow = 37;right_arrow = 39;space_bar = 32;
    function handleKeyPress(gfg) {
        switch (gfg.keyCode) {
            case 32:
            case 75:
                if (!player.paused) {
                    player.pause();
                } else {
                    player.play();
                };
                break;
            case 39:
                player.currentTime = player.currentTime + 5
                console.log("+5 secs");
                break;
            case 37:
                player.currentTime = player.currentTime - 5
                console.log("-5 secs");
                break;
            case 74:
                player.currentTime = player.currentTime - 10
                console.log("-10 secs");
                break;
            case 76:
                player.currentTime = player.currentTime + 10
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
    };
};

function start_at(progress) {
    console.log("progress: " + progress)
    player.currentTime = progress;
}

function add_progress_listener(video_id) {
    var video = document.getElementById("video_player");
    video.addEventListener('timeupdate', function () {
        var xhr = new XMLHttpRequest();
        xhr.open('POST', '../save_progress', true);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.onload = function () {
            if (xhr.status === 200) {
                var data = JSON.parse(xhr.responseText);
                console.log('Progress saved');
            }
        };
        xhr.onerror = function () {
            console.error('Error saving progress: ', xhr.statusText);
        };
        xhr.send(JSON.stringify({ time: video.currentTime, id: video_id }));
    });
}

