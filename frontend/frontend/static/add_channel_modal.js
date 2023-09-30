var modal = document.getElementById("myModal");
var btn = document.getElementById("add");
var span = document.getElementsByClassName("close")[0];

add.onclick = function () {
    modal.style.display = "block";
}

span.onclick = function () {
    modal.style.display = "none";
}

window.onclick = function (event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}

function formSubmit(event) {
    var url = "../add";
    var request = new XMLHttpRequest();
    request.open('POST', url, true);
    request.onload = function () {
        if (request.status == 400) {
            alert('The channel id is invalid!');
        } else {
            var jsonResponse = JSON.parse(request.responseText);
            alert(jsonResponse.text);
            modal.style.display = "none";
        }
    };
    request.onerror = function() {
        alert('Network error, please try again');
    };
    request.send(new FormData(event.target));
    event.preventDefault();
}

function attachFormSubmitEvent(formId) {
    document.getElementById(formId).addEventListener("submit", formSubmit);
}

attachFormSubmitEvent("channel_form");