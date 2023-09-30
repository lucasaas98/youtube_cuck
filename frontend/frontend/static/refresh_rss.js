function refresh_rss() {
    but = document.getElementById("rss_ref");
    var url = "refresh_rss";
    var request = new XMLHttpRequest();
    request.open('POST', url, true);
    request.onload = function () { // request successful
        var jsonResponse = JSON.parse(request.responseText);
        if (jsonResponse.text == "True") {
            window.location.reload(true);
        }
    };
    request.send();
}