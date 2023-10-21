function keep(video_id) {
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "GET", "../keep/" + video_id, false );
    xmlHttp.send( null );
    return xmlHttp.responseText;
}

function unkeep(video_id) {
    var xmlHttp = new XMLHttpRequest();
    xmlHttp.open( "GET", "../unkeep/" + video_id, false );
    xmlHttp.send( null );
    return xmlHttp.responseText;
}

function handleKeep(cb, video_id) {
    if(cb.checked) {
        keep(video_id);
    } else {
        unkeep(video_id);
    }
}