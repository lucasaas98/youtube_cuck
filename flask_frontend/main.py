from flask import Flask, request, render_template, make_response
from Model import get_db_access, engine
from Model import YoutubeVideo, JsonData, VideoFlag, RSSFeedDate, Playlist, PlaylistVideo, ThreadPool, Base
import requests
import opml
import feedparser
import threading
import os

# Flask APP
application = Flask(__name__)

# backend_ip = os.getenv("YT_CUCK_BACKEND_SERVICE_HOST")
# backend_port = os.getenv("YT_CUCK_BACKEND_SERVICE_PORT")

# The landing page
@application.route('/')
def index():
    data = get_recent_videos(0)
    data = ([[youtube_video.id, youtube_video.vid_url, youtube_video.thumb_url,
              youtube_video.vid_path, youtube_video.thumb_path, youtube_video.pub_date,
              youtube_video.pub_date_human, youtube_video.rating, youtube_video.title,
              place_value(youtube_video.views), youtube_video.description, youtube_video.channel] for youtube_video in data], 0, get_rss_date().date_human if get_rss_date else "DateForHumans" )
    return render_template('yt_cuck.html', data=data)


@application.route('/page/<page>')
def next_page(page):
    data = get_recent_videos(page)
    data = ([[youtube_video.id, youtube_video.vid_url, youtube_video.thumb_url,
              youtube_video.vid_path, youtube_video.thumb_path, youtube_video.pub_date,
              youtube_video.pub_date_human, youtube_video.rating, youtube_video.title,
              place_value(youtube_video.views), youtube_video.description, youtube_video.channel] for youtube_video in data], int(page), get_rss_date().date_human if get_rss_date else "DateForHumans")
    return render_template('yt_cuck_page.html', data=data)


@application.route("/video/<identifier>")
def video_watch(identifier):
    youtube_video = get_db_video(identifier)
    data = {
        'title': youtube_video.title,
        'views': place_value(youtube_video.views),
        'rating': youtube_video.rating,
        'vid_path': youtube_video.vid_path,
        'channel_name': youtube_video.channel,
        'date': youtube_video.pub_date_human,
        'description': youtube_video.description.split("\n")
    }
    return render_template('cuck_video.html', data=data, length=len(data['description']))


@application.route("/channel/<channel_name>")
def channel_video_watch(channel_name):
    data = get_db_channel_video(channel_name)
    data = [channel_name, [[youtube_video.id, youtube_video.vid_url, youtube_video.thumb_url,
                            youtube_video.vid_path, youtube_video.thumb_path, youtube_video.pub_date,
                            youtube_video.pub_date_human, youtube_video.rating, youtube_video.title,
                            place_value(youtube_video.views), youtube_video.description, youtube_video.channel] for youtube_video in data]]
    return render_template('cuck_channel.html', data=data)


@application.route("/subs")
def get_subs():
    data = get_all_channels()
    sorted_by_second = sorted(data, key=lambda tup: tup[0].strip())
    return render_template('cuck_subs.html', data=sorted_by_second)


@application.route('/add', methods=['POST'])
def add_channel():
    form_data = request.form
    channel_name = form_data['channel_name']
    channel_id = form_data['channel_id']
    feed_url = f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}'
    if is_valid_url(feed_url):
        fi = open('/data/subscription_manager', 'r')
        sub_data = fi.readlines()
        fi.close()
        fo = open('/data/subscription_manager', 'w')
        data = sub_data[0]
        data += sub_data[1].split("</outline></body></opml>")[0]
        data += f'<outline text="{channel_name}" title="{channel_name}" type="rss" xmlUrl="{feed_url}" />'
        data += "</outline></body></opml>"
        fo.write(data)
        fo.close()
        return make_response("Channel Added.", 200)
    else:
        return make_response("There was an error adding that channel, make sure the channel ID is correct.", 400)


@application.route('/refresh_rss', methods=['POST'])
def refresh_rss():
    response, thread = get_rss_feed()
    if response:
        thread.join()
    return make_response("True", 200)


@application.before_first_request
def ready_up_server():
    try:
        os.system("mkdir -p /data/videos/")
        os.system("mkdir -p /data/thumbnails/")
    except Exception as e:
        print("Unable to create folders")
    try:
        os.system('cp subscription_manager /data/subscription_manager')
    except Exception as e:
        print("Unable to copy subscription_manager")
    Base.metadata.create_all(engine)
    t1 = threading.Thread(target=ready_up_request)
    t1.start()


def get_rss_feed():
    t1 = threading.Thread(target=send_request_rss)
    t1.start()
    return True, t1

def send_request_rss():
    return requests.post(f'http://yt-cuck-backend:5020/api/refresh_rss')

def ready_up_request():
    return requests.post(f'http://yt-cuck-backend:5020/api/startup')


def place_value(number):
    return ("{:,}".format(number))


def get_db_video(identifier):
    try:
        session = get_db_access()
        data = session.query(YoutubeVideo).filter_by(id=identifier).first()
        return data
    except Exception as error:
        print(
            "Failed to select videos from downloaded_videos table with id={identifier}", error)
        return []


def get_db_channel_video(channel_name):
    try:
        session = get_db_access()
        data = session.query(YoutubeVideo).filter_by(channel=channel_name).order_by(YoutubeVideo.pub_date.desc())
        return data
    except Exception as error:
        print(
            f"Failed to select videos from downloaded_videos table from {channel_name}", error)
        return []


def get_recent_videos(page):
    try:
        session = get_db_access()
        selection = (int(page)+1) * 35
        data = session.query(YoutubeVideo).filter(YoutubeVideo.vid_path != 'NA').order_by(YoutubeVideo.pub_date.desc()).limit(35).offset(selection-35).all()
        return data
    except Exception as error:
        print("Failed to select recent videos from downloaded_videos table", error)
        return []


def get_rss_date():
    try:
        session = get_db_access()
        data = session.query(RSSFeedDate).order_by(RSSFeedDate.id.desc()).limit(1).first()
        if data:
            return data
        else: 
            return RSSFeedDate()
    except Exception as error:
        print("Failed to select recent videos from rss_feed_date table", error)
        return []
    
    
def get_all_channels():
    data = open("/data/subscription_manager", "r")

    nested = opml.parse(data)
    
    all_channels = list()
    for channel in nested[0]:
        real_id = channel.xmlUrl.split("=")[1]
        all_channels.append((channel.title, real_id))
    return all_channels

def is_valid_url(feed_url):
    video_feed = None
    video_feed = feedparser.parse(feed_url)
    if(video_feed['status'] == 200):
        return True
    else:
        return False
        
if __name__ == '__main__':
    application.run(host='0.0.0.0',port=5010)
