from flask import Flask, request, render_template, make_response, g
import time
import os
import json
from subprocess import Popen, PIPE
from datetime import datetime
import requests
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
import threading
from tqdm import tqdm
import feedparser
import opml
import dateutil.parser as date_parser

from Model import get_db_access
from Model import YoutubeVideo, JsonData, VideoFlag, RSSFeedDate, Playlist, PlaylistVideo


application = Flask(__name__)


# Don't download videos older than:
delay_time = 172800 / 4

# Remove videos older than:
remove_date = delay_time * 2


@application.route('/api/refresh_rss', methods=['POST'])
def refresh_rss():
    response, thread = get_rss_feed()
    if response:
        thread.join()
    return make_response(str(response), 200)


@application.route('/api/startup', methods=['POST'])
def startup():
    activate_schedule()
    return make_response("Server is now starting", 200)


def activate_schedule():
    scheduler = BackgroundScheduler()
    # Schedule to remove videos older than X time
    scheduler.add_job(func=remove_old_videos, trigger="interval", seconds=3600)
    # Schedule to get RSS feed automatically
    scheduler.add_job(func=get_rss_feed, trigger="interval", seconds=600)
    scheduler.start()

    # Shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())
    remove_old_videos()
    get_rss_feed()


def remove_old_videos():
    min_pub_date = time.time() - remove_date
    records = get_expired_videos(min_pub_date)
    for expired_video in records:
        file_path = os.path.join("/data/videos", expired_video[1])
        if not os.path.exists(file_path):
            file_path = os.path.join("/data/videos", expired_video[1].split(".")[0])
        os.remove(file_path)
        thumb_path = os.path.join("/data/thumbnails", expired_video[2])

        os.remove(thumb_path)
        expire_video(expired_video[0])



# This function is used to update the json file with the most recent videos
# directly from the RSS feed
def get_rss_feed():
    date = datetime.now()
    date_str = datetime.strftime(date, "%d/%m/%Y, %H:%M:%S GMT")
    print(f"[{date_str}] Getting RSS feed!")
    update_rss_date(date_str)
    new_json = get_data()
    old_json = get_json()
    if not are_there_new_videos(new_json, old_json):
        print("There are no new videos!")
        return (False, None)
    else:
        print("There are videos to download!")
        if not get_video_flag():
            update_json(new_json)
            thread = threading.Thread(target=get_video)
            thread.start()
            return (True, thread)
        return (False, None)


def get_data():
    threads = []

    data = open("/data/subscription_manager", "r")

    nested = opml.parse(data)

    all_channels = dict()

    for idx, channel in enumerate(nested[0]):
        channel_name = channel.title
        thread = getter_thread(idx, channel, channel_name)
        threads.append(thread)
        thread.start()

    for t in threads:
        t.join()
        all_channels[t.channel_name] = t.data

    return all_channels

class getter_thread(threading.Thread):
    def __init__(self, threadID, channel, channel_name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.channel = channel
        self.channel_name = channel_name
        self.data = list()

    def run(self):
        self.data = get_channel_data(self.channel)

def get_channel_data(channel):
    
    channel_data = list()
    video_feed = feedparser.parse(channel.xmlUrl)

    for entry in video_feed['entries']:
        thumbnail = entry['media_thumbnail']
        date = date_parser.parse(entry['published'])
        human_readable_date = datetime.strftime(
            date, "%a %B %d, %Y %I:%M %p GMT")
        epoch_date = datetime.strftime(date, "%s")
        description = entry['summary']
        rating = entry['media_starrating']
        views = entry['media_statistics']
        video_url = entry['link']
        title = entry['title']
        all_info = {
            "title": title,
            "thumbnail": thumbnail[0]['url'],
            "human_date": human_readable_date,
            "epoch_date": epoch_date,
            "description": description,
            "rating": rating['average'],
            "views": views['views'],
            "video_url": video_url
        }
        channel_data.append(all_info)
    return channel_data

def are_there_new_videos(new_json, old_json):
    # if not old_json:
    #     return True
    # if old_json.keys() != new_json.keys():
    #     return True
    # for channel in new_json.keys():
    #     for idx, video in enumerate(new_json[channel]):
    #         if video['video_url'] != old_json[channel][idx]['video_url']:
    #             return True
    return True


# This function is used to get the videos and thumbnails to the program and it also
# inserts all the relevant data to the database
def get_video():
    print("Downloading videos!")
    update_video_flag(1)
    try:
        data = get_db_access().query(YoutubeVideo).all()
        down_vid_urls = [x.vid_url for x in data]
        min_date = time.time() - delay_time
        json_video_data = json.loads(get_json())
        for channel in tqdm(json_video_data.keys()):
            for video in json_video_data[channel]:
                url = video['video_url']
                if url in down_vid_urls:
                    update_view_count(video)
                    continue
                if float(video['epoch_date']) < min_date:
                    continue
                file_name = url.split('=')[1]
                if not download_video(url, file_name):
                    print(
                        "There was an error with the download, trying again later")
                    continue
                print("Video downloaded successfully")
                thumb_url = video['thumbnail']
                download_thumbnail(thumb_url, file_name)

                pub_date = int(video['epoch_date'])
                human_date = video['human_date']
                channel_name = channel
                rating = float(video['rating'])
                title = video['title']
                views = int(video['views'])
                description = video['description']
                video_path = f"{file_name}.mp4"
                thumb_path = f"{file_name}.jpg"
                
                session = get_db_access()
                session.add(YoutubeVideo(vid_url=url,
                                            vid_path=video_path,
                                            thumb_url=thumb_url,
                                            thumb_path=thumb_path,
                                            pub_date=pub_date,
                                            pub_date_human=human_date,
                                            rating=rating,
                                            title=title,
                                            views=views,
                                            description=description,
                                            channel=channel_name))

                session.commit()
    except Exception as e:
        e.with_traceback()
    finally:
        update_video_flag(0)
        print("Videos Downloaded!")


# This function calls youtube-dl to download a video. Might replace with the python wrapper.
def download_video(url, filename):
    try:
        p = Popen(
            [f"youtube-dl -f 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]mp4' {url} -o /data/videos/{filename}"], shell=True, stdout=PIPE, stderr=PIPE)
        output, err = p.communicate()
        str_check = "does not pass filter islive != true"
        if str_check in str(output) or str_check in str(err):
            return False
        rc = p.returncode
        if rc == 0:
            return True
        else:
            return False
    except Exception as e:
        e.with_traceback()


# This functions downloads the thumbnail with a url
def download_thumbnail(url, filename):
    r = requests.get(url)
    with open(f"/data/thumbnails/{filename}.jpg", "wb") as f:
        f.write(r.content)

def expire_video(identifier):
    try:
        session = get_db_access()
        updated_rec = session.query(YoutubeVideo).filter_by(id=1).first()
        updated_rec.vid_path = 'NA'
        updated_rec.thumb_path = 'NA'
        session.commit()
    except Exception as error:
        print(
            f"Failed to update downloaded_videos table with id={identifier}", error)


def get_expired_videos(date):
    try:
        session = get_db_access()
        data = session.query(YoutubeVideo).filter_by(vid_path='NA', pub_date=date).all()
        return data
    except Exception as error:
        print("Failed to select expired videos from downloaded_videos table", error)
        return []


def get_db_video(identifier):
    try:
        session = get_db_access()
        data = session.query(YoutubeVideo).filter_by(id=identifier).all()
        return data
    except Exception as error:
        print(
            "Failed to select videos from downloaded_videos table with id={identifier}", error)
        return []


def get_db_channel_video(channel_name):
    try:
        session = get_db_access()
        data = session.query(YoutubeVideo).filter_by(channel=channel_name).order_by(YoutubeVideo.pub_date.desc()).all()
        return data
    except Exception as error:
        print(
            f"Failed to select videos from downloaded_videos table from {channel_name}", error)
        return []


def get_recent_videos(page):
    try:
        session = get_db_access()
        selection = (int(page)+1) * 35
        data = session.query(YoutubeVideo).filter_by(YoutubeVideo.vid_path != 'NA').order_by(YoutubeVideo.pub_date.desc()).limit(35).offset(selection-35).all()
        return data
    except Exception as error:
        print("Failed to select recent videos from downloaded_videos table", error)
        return []


def update_view_count(video_data):
    try:
        url = video_data['video_url']
        views = int(video_data['views'])
        rating = float(video_data['rating'])
        session = get_db_access()
        vid = session.query(YoutubeVideo).filter_by(vid_url=url).first()
        vid.views = views
        vid.rating = rating
        session.commit()
    except Exception as error:
        print(
            f"Failed to update downloaded_videos table with vid_url={video_data['video_url']}", error)


def get_rss_date():
    try:
        session = get_db_access()
        data = session.query(RSSFeedDate).order_by(RSSFeedDate.id.desc()).limit(1).first()
        return data
    except Exception as error:
        print("Failed to select recent videos from rss_feed_date table", error)
        return []


def update_rss_date(date_str):
    try:
        session = get_db_access()
        data = session.query(RSSFeedDate).order_by(RSSFeedDate.id.desc()).limit(1).all()
        if data == []:
            insert_rss_date(date_str)
        else:
            data[0].date_human = date_str
            session.commit()
    except Exception as error:
        print(f"Failed to update rss_feed_date table", error)


def insert_rss_date(date_str):
    try:
        session = get_db_access()
        session.add(RSSFeedDate(date_human=date_str))
        session.commit()
    except Exception as error:
        print("Failed to insert video into downloaded_videos table", error)


def get_json():
    try:
        session = get_db_access()
        data = session.query(JsonData).order_by(JsonData.id.desc()).limit(1).first()
        if data:
            return data.rss_feed_json
        return data
    except Exception as error:
        print("Failed to select recent videos from json_data table", error)
        return []


def update_json(json_data):
    try:
        session = get_db_access()
        data = session.query(JsonData).order_by(JsonData.id.desc()).limit(1).all()
        if data == []:
            insert_json(json_data)
        else:
            data[0].rss_feed_json = json.dumps(json_data)
            session.commit()
    except Exception as error:
        print("Failed to update json_data table", error)


def insert_json(json_data):
    try:
        session = get_db_access()
        json_str = json.dumps(json_data)
        session.add(JsonData(rss_feed_json=json_str))
        session.commit()
    except Exception as error:
        print("Failed to insert jsondata into JsonData table", error)


def get_video_flag():
    try:
        session = get_db_access()
        data = session.query(VideoFlag).order_by(VideoFlag.id.desc()).limit(1).all()
        if data == []:
            return False
        if data[0].flag == 0:
            return False
        else:
            return True
    except Exception as error:
        print("Failed to select from video_flag table", error)
        return True


def update_video_flag(flag):
    try:
        session = get_db_access()
        data = session.query(VideoFlag).order_by(VideoFlag.id.desc()).limit(1).all()
        if data == []:
            insert_video_flag(flag)
        else:
            data[0].flag = flag
            session.commit()
    except Exception as error:
        print("Failed to update json_data table", error)


def insert_video_flag(flag):
    try:
        session = get_db_access()
        session.add(VideoFlag(flag=flag))
        session.commit()
    except Exception as error:
        print("Failed to insert flag into video_flag table", error)


if __name__ == '__main__':
    application.run(host='0.0.0.0',port=5020)
