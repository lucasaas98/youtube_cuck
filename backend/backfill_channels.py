"""One-off backfill: fetch avatar and description for existing channels.

Run inside the backend container after deploying:
    docker exec yt_backend python backfill_channels.py
"""

import yt_dlp
from sqlalchemy import select

from backend.engine import session_scope
from backend.models import Channel
from backend.repo import download_channel_avatar
from backend.utils import pick_channel_avatar


def extract_channel_info(channel_id):
    url = f"https://www.youtube.com/channel/{channel_id}/about"
    opts = {"quiet": True, "no_warnings": True, "extract_flat": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        return ydl.extract_info(url, download=False) or {}


def backfill():
    with session_scope() as session:
        channels = (
            session.execute(
                select(Channel).where(
                    (Channel.avatar_path.is_(None)) | (Channel.description.is_(None))
                )
            )
            .scalars()
            .all()
        )
        total = len(channels)
        print(f"Channels to backfill: {total}", flush=True)

        for i, channel in enumerate(channels, 1):
            label = channel.channel_name or channel.channel_id
            try:
                info = extract_channel_info(channel.channel_id)
                avatar_url = pick_channel_avatar(info)
                description = info.get("description") or ""
                updated = []

                if avatar_url and not channel.avatar_path:
                    path = download_channel_avatar(avatar_url, channel.channel_id)
                    if path:
                        channel.avatar_path = path
                        updated.append("avatar")

                if description and not channel.description:
                    channel.description = description
                    updated.append("description")

                session.commit()
                print(
                    f"[{i}/{total}] {label}: {', '.join(updated) or 'skipped'}",
                    flush=True,
                )
            except Exception as error:
                session.rollback()
                print(f"[{i}/{total}] {label}: FAILED {error}", flush=True)


if __name__ == "__main__":
    backfill()
