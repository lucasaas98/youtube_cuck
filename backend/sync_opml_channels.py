"""One-off sync: add OPML channels missing from the channel registry.

The RSS refresh reads the OPML file while the subscriptions page reads
the channel table, so channels only present in the OPML (e.g. seeded
long ago) were invisible. Insert them, then run backfill_channels.py
to fetch their avatars/descriptions:

    docker exec yt_backend python sync_opml_channels.py
    docker exec yt_backend python backfill_channels.py
"""

from time import time

import opml
from sqlalchemy import select

from backend.engine import session_scope
from backend.env_vars import DATA_FOLDER
from backend.models import Channel


def sync():
    nested = opml.parse(open(f"{DATA_FOLDER}/subscription_manager"))[0]
    opml_channels = {}
    for entry in nested:
        channel_id = entry.xmlUrl.split("=")[1]
        opml_channels[channel_id] = entry.title

    with session_scope() as session:
        existing = {
            row.channel_id for row in session.execute(select(Channel)).scalars()
        }
        missing = [cid for cid in opml_channels if cid not in existing]
        print(
            f"OPML: {len(opml_channels)}, registry: {len(existing)}, "
            f"missing: {len(missing)}",
            flush=True,
        )

        for i, channel_id in enumerate(sorted(missing), 1):
            session.add(
                Channel(
                    channel_id=channel_id,
                    channel_url=(f"https://www.youtube.com/channel/{channel_id}"),
                    channel_name=opml_channels[channel_id],
                    keep=False,
                    inserted_at=int(time()),
                )
            )
            print(
                f"[{i}/{len(missing)}] added {opml_channels[channel_id]}",
                flush=True,
            )
        session.commit()
        print("done", flush=True)


if __name__ == "__main__":
    sync()
