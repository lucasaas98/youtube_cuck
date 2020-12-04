from flask import Flask, request, render_template, make_response, g
from rss_info import GetData
import json
import os
from subprocess import Popen, PIPE
import sqlite3
from datetime import datetime
import time
import requests
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
import threading
from tqdm import tqdm

# Don't download videos older than:
two_days = 172800
eight_hours = 8*3600
# Remove videos older than:
four_days = two_days * 2

# Name of the database in use
DATABASE = 'yt_cuck.db'


# Flask APP
app = Flask(__name__)


# Initializing flag and making it accessible
def get_video_flag():
    flag = getattr(g, '_getting_video', None)
    if flag is None:
        flag = g._getting_video = False
    return flag


# A way to get the database without thread problems (flask uses workers and workers might not have access to global vars)
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db


def get_json():
    json = getattr(g, '_json_data', None)
    if json is None:
        json = g._json_data = GetData().get_data()
    return json


# The landing page
@app.route('/')
def index():
    data = get_recent_videos(0)
    data = (data, 0)
    return render_template('yt_cuck.html', data=data)

@app.route('/page/<page>')
def next_page(page):
    data = get_recent_videos(page)
    data = (data, int(page))
    return render_template('yt_cuck_page.html', data=data)

@app.route("/video/<identifier>")
def video_watch(identifier):
    data = get_db_video(identifier)
    return render_template('cuck_video.html', data=data[0])


@app.route("/channel/<channel_name>")
def channel_video_watch(channel_name):
    data = get_db_channel_video(channel_name)
    data = [channel_name, data]
    return render_template('cuck_channel.html', data=data)


# This function is used to update the json with the most recent videos
# directly from the RSS feed
def get_rss_feed():
    with app.app_context():
        date = datetime.now()
        date_str = datetime.strftime(date, "%a %B %d, %Y %I:%M %p GMT")
        print(f"[{date_str}] Getting RSS feed!")
        setattr(g, '_json_data', GetData().get_data())
        print("RSS feed updated!")
        if not get_video_flag():
            thread = threading.Thread(target=get_video)
            thread.start()


# This function is used to get the videos and thumbnails to the program and it also
# inserts all the relevant data to the database
def get_video():
    with app.app_context():
        print("Downloading videos!")
        setattr(g, "_getting_video", True)
        try:
            data = get_downloaded_videos()
            down_vid_urls = [x[1] for x in data]
            min_date = time.time() - two_days
            json_video_data = get_json()
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
                        print("There was an error with the download, trying again later")
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

                    insert_video(url, thumb_url, video_path, thumb_path, pub_date,
                                 human_date, rating, title, views, description, channel_name)
        except Exception as e:
            e.with_traceback()
        finally:
            setattr(g, "_getting_video", False)
            print("Videos Downloaded!")


# This function calls youtube-dl to download a video. Might replace with the python wrapper.
def download_video(url, filename):
    try:
        p = Popen([f"youtube-dl -f 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080]mp4' {url} -o static/videos/{filename}"], shell=True, stdout=PIPE, stderr=PIPE)
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
    with open(f"static/thumbnails/{filename}.jpg", "wb") as f:
        f.write(r.content)


# This function will be called on schedule and will remove videos older than X ammount of time.
def remove_old_videos():
    with app.app_context():
        min_pub_date = time.time() - four_days
        records = get_expired_videos(min_pub_date)
        for expired_video in records:
            file_path = os.path.join("static/videos",expired_video[1] )
            thumb_path = os.path.join("static/thumbnails",expired_video[2] )
            os.remove(file_path)
            os.remove(thumb_path)
            expire_video(expired_video[0])


def insert_video(url, thumb_url, video_path, thumb_path, pub_date, human_date, rating, title, views, description, channel_name):
    with app.app_context():
        try:
            conn = get_db()
            cursor = conn.cursor()
            sql = """INSERT INTO downloaded_videos 
                    (vid_url,thumb_url,vid_path,thumb_path, pub_date, pub_date_human, rating, title, views, description, channel) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);"""
            data_tuple = (url, thumb_url, video_path, thumb_path, pub_date,
                          human_date, rating, title, views, description, channel_name)
            cursor.execute(sql, data_tuple)
            conn.commit()
            cursor.close()
        except sqlite3.Error as error:
            print("Failed to insert video into downloaded_videos table", error)


def get_downloaded_videos():
    with app.app_context():
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("""SELECT * from downloaded_videos""")
            return cursor.fetchall()
        except sqlite3.Error as error:
            print("Failed to select from downloaded_videos table", error)
            return []


def expire_video(identifier):
    with app.app_context():
        try:
            conn = get_db()
            cursor = conn.cursor()
            sql_update = """UPDATE downloaded_videos SET vid_path = 'NA', thumb_path = 'NA' where id = ?"""
            cursor.execute(sql_update, (identifier,))
            conn.commit()
        except sqlite3.Error as error:
            print(
                f"Failed to update downloaded_videos table with id={identifier}", error)


def get_expired_videos(date):
    with app.app_context():
        try:
            conn = get_db()
            cursor = conn.cursor()
            sql = """SELECT id, vid_path, thumb_path from downloaded_videos WHERE pub_date < ? AND vid_path != 'NA'"""
            cursor.execute(sql, (date,))
            return cursor.fetchall()
        except sqlite3.Error as error:
            print("Failed to select expired videos from downloaded_videos table", error)
            return []


def get_db_video(identifier):
    with app.app_context():
        try:
            conn = get_db()
            cursor = conn.cursor()
            sql = """SELECT * FROM downloaded_videos WHERE id = ?"""
            cursor.execute(sql, (identifier,))
            return cursor.fetchall()
        except sqlite3.Error as error:
            print("Failed to select expired videos from downloaded_videos table", error)
            return []


def get_db_channel_video(channel_name):
    with app.app_context():
        try:
            conn = get_db()
            cursor = conn.cursor()
            sql = """SELECT * FROM downloaded_videos WHERE channel = ? ORDER BY pub_date DESC"""
            cursor.execute(sql, (channel_name,))
            return cursor.fetchall()
        except sqlite3.Error as error:
            print(
                f"Failed to select videos from downloaded_videos table from {channel_name}", error)
            return []


def get_recent_videos(page):
    with app.app_context():
        try:
            conn = get_db()
            cursor = conn.cursor()
            selection = (int(page)+1) * 35
            prev_sel = selection-35
            sql = """SELECT * from downloaded_videos WHERE vid_path NOT LIKE 'NA' ORDER BY pub_date DESC"""
            cursor.execute(sql)
            return cursor.fetchall()[prev_sel:selection]
        except sqlite3.Error as error:
            print("Failed to select recent videos from downloaded_videos table", error)
            return []


def update_view_count(video_data):
    with app.app_context():
        try:
            conn = get_db()
            cursor = conn.cursor()
            url = video_data['video_url']
            views = int(video_data['views'])
            rating = float(video_data['rating'])
            sql_update = """UPDATE downloaded_videos SET views = ?, rating = ? where vid_url = ?"""
            cursor.execute(sql_update, (views, rating, url))
            conn.commit()
        except sqlite3.Error as error:
            print(
                f"Failed to update downloaded_videos table with vid_url={video_data['video_url']}", error)


# This function makes sure to close the database connection whenever flask is closed
@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


@app.before_first_request
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


if __name__ == '__main__':
    app.run(host='0.0.0.0')
