import logging as _logging
from time import time

import feedparser
import opml

from backend.engine import session_scope
from backend.env_vars import DATA_FOLDER
from backend.logging import logging
from backend.models import Channel
from backend.repo import get_all_channels, get_real_all_videos

logger = logging.getLogger(__name__)
logger.setLevel(_logging.INFO)


def backfill_channels():
    """
    Parse the OPML file containing YouTube channel subscriptions and create channels.

    :return: A dictionary containing channel names as keys and their video data as values.
    :rtype: dict
    """
    data = open(f"{DATA_FOLDER}/subscription_manager", "r")
    nested = opml.parse(data)

    channels = [channel for channel in nested[0]]
    new_channels = []
    titles = []
    for channel in channels:
        try:
            channel_feed = feedparser.parse(channel.xmlUrl)
            channel_id = "UC" + channel_feed["feed"]["yt_channelid"]
            channel_urls = channel_feed["feed"]["links"]
            channel_url = [a["href"] for a in channel_urls if a["rel"] == "alternate"][
                0
            ]
            channel_name = channel_feed["feed"]["title"]

            new_channels.append(
                (
                    Channel(
                        channel_id=channel_id,
                        channel_url=channel_url,
                        channel_name=channel_name,
                        inserted_at=int(time()),
                    ),
                    channel.title,
                )
            )
            titles.append((channel_name, channel.title))
        except:
            logger.error(f"Failed to add channel {channel.title}")

    with session_scope() as session:
        session.add_all([a[0] for a in new_channels])
        session.commit()

    return titles


def backfill_video_channels(titles):
    with session_scope() as session:
        videos = [x[0] for x in get_real_all_videos(session)]
        channels = [x[0] for x in get_all_channels()]

        for video in videos:
            yt_cuck_title = video.channel
            channel_name = [c[0] for c in titles if c[1] == yt_cuck_title][0]
            for channel in channels:
                if channel.channel_name == channel_name:
                    video.channel_id = channel.id
        session.commit()
    return
