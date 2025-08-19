var modal = document.getElementById("myModal");
var btn = document.getElementById("add");
var span = document.getElementsByClassName("close")[0];
var previewBtn = document.getElementById("preview_btn");
var confirmAddBtn = document.getElementById("confirm_add_btn");
var channelPreview = document.getElementById("channel_preview");
var previewContent = document.getElementById("preview_content");
var channelInput = document.getElementById("channel_input");

var currentChannelData = null;

add.onclick = function () {
    modal.style.display = "block";
    resetModal();
};

span.onclick = function () {
    modal.style.display = "none";
    resetModal();
};

window.onclick = function (event) {
    if (event.target == modal) {
        modal.style.display = "none";
        resetModal();
    }
};

function resetModal() {
    channelInput.value = "";
    channelPreview.style.display = "none";
    confirmAddBtn.style.display = "none";
    previewContent.innerHTML = "";
    currentChannelData = null;
    previewBtn.disabled = false;
    previewBtn.textContent = "Preview Channel";
}

previewBtn.onclick = function () {
    var channelInputValue = channelInput.value.trim();

    if (!channelInputValue) {
        alert("Please enter a channel URL, ID, or handle");
        return;
    }

    previewBtn.disabled = true;
    previewBtn.textContent = "Loading...";

    var formData = new FormData();
    formData.append("channel_input", channelInputValue);

    var request = new XMLHttpRequest();
    request.open("POST", "../api/preview_channel", true);
    request.onload = function () {
        previewBtn.disabled = false;
        previewBtn.textContent = "Preview Channel";

        if (request.status == 200) {
            var response = JSON.parse(request.responseText);
            if (response.success) {
                currentChannelData = response.channel_info;
                displayChannelPreview(currentChannelData);
            } else {
                alert("Error: " + response.error);
            }
        } else {
            var errorResponse = JSON.parse(request.responseText);
            alert(
                "Error: " +
                    (errorResponse.error || "Failed to preview channel"),
            );
        }
    };
    request.onerror = function () {
        previewBtn.disabled = false;
        previewBtn.textContent = "Preview Channel";
        alert("Network error, please try again");
    };
    request.send(formData);
};

function displayChannelPreview(channelData) {
    var html = '<div style="color: white; text-align: left;">';

    // Channel basic info
    html += '<div style="margin-bottom: 15px;">';
    if (channelData.thumbnail) {
        html +=
            '<img src="' +
            channelData.thumbnail +
            '" style="width: 80px; height: 80px; border-radius: 50%; float: left; margin-right: 15px;">';
    }
    html += "<div>";
    html +=
        '<h4 style="margin: 0; color: #fff;">' +
        escapeHtml(channelData.channel_name) +
        "</h4>";
    html +=
        '<p style="margin: 5px 0; font-size: 12px; color: #ccc;">ID: ' +
        escapeHtml(channelData.channel_id) +
        "</p>";
    if (channelData.subscriber_count > 0) {
        html +=
            '<p style="margin: 5px 0; font-size: 12px; color: #ccc;">Subscribers: ' +
            formatNumber(channelData.subscriber_count) +
            "</p>";
    }
    if (channelData.video_count > 0) {
        html +=
            '<p style="margin: 5px 0; font-size: 12px; color: #ccc;">Videos: ' +
            formatNumber(channelData.video_count) +
            "</p>";
    }
    html += "</div>";
    html += '<div style="clear: both;"></div>';
    html += "</div>";

    // RSS Feed status
    html += '<div style="margin-bottom: 15px;">';
    if (channelData.feed_working) {
        html += '<p style="color: #4CAF50; margin: 0;">✓ RSS feed working</p>';
    } else {
        html +=
            '<p style="color: #f44336; margin: 0;">⚠ RSS feed may not work (channel might be too new or have no videos)</p>';
    }
    html += "</div>";

    // Recent videos
    if (channelData.recent_videos && channelData.recent_videos.length > 0) {
        html += '<div style="margin-bottom: 15px;">';
        html +=
            '<h5 style="color: #fff; margin-bottom: 10px;">Recent Videos:</h5>';
        channelData.recent_videos.forEach(function (video, index) {
            html +=
                '<div style="margin-bottom: 8px; padding: 8px; background: rgba(255,255,255,0.1); border-radius: 4px;">';
            html +=
                '<p style="margin: 0; font-size: 13px; color: #fff;">' +
                escapeHtml(video.title) +
                "</p>";
            html +=
                '<p style="margin: 2px 0 0 0; font-size: 11px; color: #ccc;">' +
                formatDate(video.published) +
                "</p>";
            html += "</div>";
        });
        html += "</div>";
    }

    // Description (truncated)
    if (channelData.description) {
        var truncatedDesc =
            channelData.description.length > 200
                ? channelData.description.substring(0, 200) + "..."
                : channelData.description;
        html += '<div style="margin-bottom: 15px;">';
        html +=
            '<h5 style="color: #fff; margin-bottom: 5px;">Description:</h5>';
        html +=
            '<p style="font-size: 12px; color: #ccc; line-height: 1.4;">' +
            escapeHtml(truncatedDesc) +
            "</p>";
        html += "</div>";
    }

    html += "</div>";

    previewContent.innerHTML = html;
    channelPreview.style.display = "block";
    confirmAddBtn.style.display = "inline-block";
}

confirmAddBtn.onclick = function () {
    if (!currentChannelData) {
        alert("No channel data available");
        return;
    }

    confirmAddBtn.disabled = true;
    confirmAddBtn.textContent = "Adding...";

    var formData = new FormData();
    formData.append("channel_id", currentChannelData.channel_id);
    formData.append("channel_url", currentChannelData.channel_url);
    formData.append("channel_name", currentChannelData.channel_name);

    var request = new XMLHttpRequest();
    request.open("POST", "../api/add_channel_confirmed", true);
    request.onload = function () {
        confirmAddBtn.disabled = false;
        confirmAddBtn.textContent = "Add This Channel";

        if (request.status == 200) {
            var response = JSON.parse(request.responseText);
            if (response.success) {
                alert("Channel added successfully!");
                modal.style.display = "none";
                resetModal();
                // Reload the page to show the new channel
                window.location.reload();
            } else {
                alert("Error: " + response.error);
            }
        } else {
            var errorResponse = JSON.parse(request.responseText);
            alert("Error: " + (errorResponse.error || "Failed to add channel"));
        }
    };
    request.onerror = function () {
        confirmAddBtn.disabled = false;
        confirmAddBtn.textContent = "Add This Channel";
        alert("Network error, please try again");
    };
    request.send(formData);
};

function escapeHtml(text) {
    var map = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
    };
    return text.replace(/[&<>"']/g, function (m) {
        return map[m];
    });
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + "M";
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + "K";
    }
    return num.toString();
}

function formatDate(dateString) {
    try {
        var date = new Date(dateString);
        return date.toLocaleDateString();
    } catch (e) {
        return dateString;
    }
}
