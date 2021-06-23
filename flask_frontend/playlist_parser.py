from html.parser import HTMLParser
import json

class YoutubePlaylistParser(HTMLParser):

    def __init__(self, playlist_id):
        HTMLParser.__init__(self)
        self.start_a = False
        self.current_index = 0
        self.playlist_id = playlist_id
        self.data = {}

    def handle_starttag(self, tag, attrs):
        if tag == "a":
           for name, value in attrs:
               if name == "href":
                    if self.playlist_id in value and "index" in value:
                        index = value.split("index=")[1].split("&t=")[0].strip()
                        url = value.split("&list")[0].strip()
                        self.data[index] = { 'url':url, 
                                        'title':None}
                        self.start_a = True
                        self.current_index = index
        if self.start_a and tag == "span":
            flag = False
            for name, value in attrs:
                if name == 'id' and value=="video-title":
                    flag = True
                if flag:
                    if name == "title":
                        self.data[self.current_index]['title'] = value
                        self.start_a = False

def parse_playlist(html_file_path, playlist_id):
    #html_file can be obtained by scrolling down a playlist on youtube until all videos appear on the page and saving the same page to the device.
    #playlist_id has to be of the format "list=XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" and can be found in any of the url of the videos from that playlist

    fi = open(html_file_path, 'r')

    parser = YoutubePlaylistParser(playlist_id)
    for line in fi:
        parser.feed(line)

    return parser.data