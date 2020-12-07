import feedparser
import opml
import dateutil.parser as date_parser
from datetime import datetime
import json
from time import time
import threading


class getter_thread(threading.Thread):
    def __init__(self, threadID, channel, channel_name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.channel = channel
        self.channel_name = channel_name
        self.data = list()

    def run(self):
        self.data = get_channel_data(self.channel)


class all_getter_thread(threading.Thread):
    def __init__(self, threadID, channel, channel_name):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.channel = channel
        self.channel_name = channel_name
        self.data = list()

    def run(self):
        self.data = get_all_channel_data(self.channel)


def get_all_channel_data(channel):

    channel_data = list()
    video_feed = feedparser.parse(channel.xmlUrl)

    # thumbnails= video_feed['entries'][0]['media_thumbnail']
    # date = video_feed['entries'][0]['published'] -> format: '2020-11-27T17:30:02+00:00'
    # description = video_feed['entries'][0]['summary']
    # rating 1-5 = video_feed['entries'][0]['media_starrating']
    # video_url = video_feed['entries'][0]['link']
    # views = video_feed['entries'][0]['media_statistics']

    for entry in video_feed['entries']:
        for key, item in entry.items():
            print(key, item)
        break
    return channel_data


def is_valid_url(feed_url):
    video_feed = None
    video_feed = feedparser.parse(feed_url)
    if(video_feed['status'] == 200):
        return True
    else:
        return False

def get_all_channels():
    data = open("subscription_manager", "r")

    nested = opml.parse(data)
    
    all_channels = list()
    # print(nested)
    for channel in nested[0]:
        real_id = channel.xmlUrl.split("=")[1]
        all_channels.append((channel.title, real_id))
    return all_channels

def get_channel_data(channel):

    channel_data = list()
    video_feed = feedparser.parse(channel.xmlUrl)

    # thumbnails= video_feed['entries'][0]['media_thumbnail']
    # date = video_feed['entries'][0]['published'] -> format: '2020-11-27T17:30:02+00:00'
    # description = video_feed['entries'][0]['summary']
    # rating 1-5 = video_feed['entries'][0]['media_starrating']
    # video_url = video_feed['entries'][0]['link']
    # views = video_feed['entries'][0]['media_statistics']

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


class GetData:
    def get_data(self):
        threads = []

        data = open("subscription_manager", "r")

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

        # json_object = json.dumps(all_channels, indent = 4)
        # json_object = json.

        return all_channels

    def get_all_data(self):
        threads = []

        data = open("subscription_manager_test", "r")

        nested = opml.parse(data)

        all_channels = dict()

        for idx, channel in enumerate(nested[0]):
            channel_name = channel.title
            thread = all_getter_thread(idx, channel, channel_name)
            threads.append(thread)
            thread.start()

        for t in threads:
            t.join()
            all_channels[t.channel_name] = t.data

        json_string = json.dumps(all_channels, indent=4)

        fo = open("json_out.json", "w")
        fo.write(json_string)


if __name__ == "__main__":
    GetData().get_all_data()
    # print(is_valid_url("https://www.youtube.com/feeds/videos.xml?channel_id=lmao"))
    # get_all_channels()