import os
import time
import youtube_audio_bot.tgrm as tgrm
import youtube_audio_bot.youtube as youtube
import youtube_audio_bot.audio as audio

from datetime import datetime, timedelta, timezone
from flask import request, jsonify
from .app import app, db
from .model import Channel


def process_video(video_id, publish_date):
    r = youtube.download_audio(video_id)
    if r is None:
        return False
    audio_file, author, title, duration_secs = r
    audio_parts = audio.split_convert_to_mp3(
        audio_file, duration_secs, tgrm.AUDIO_FILE_SIZE_LIMIT
    )
    tgrm.send_audio_files(video_id, author, title, publish_date, audio_parts)
    os.remove(audio_file)
    for f, _ in audio_parts:
        if f != audio_file:
            os.remove(f)
    return True


def process_new_videos():
    for channel in Channel.query.all():
        channel_ids = []
        if channel.is_username:
            channel_ids.extend(youtube.list_user_channels(channel.youtube_id))
        else:
            channel_ids.append(channel.youtube_id)
        for channel_id in channel_ids:
            if channel.last_checked is not None:
                from_date = channel.last_checked.replace(
                    tzinfo=timezone.utc
                ) + timedelta(seconds=1)
            else:
                from_date = datetime.now().replace(tzinfo=timezone.utc) - timedelta(
                    days=1
                )
            new_videos = youtube.list_channel_videos(
                channel.name, channel_id, from_date
            )
            for video_id, video_date in new_videos:
                if process_video(video_id, video_date):
                    channel.last_checked = video_date
                    db.session.commit()
            time.sleep(10)


@app.route("/channels", methods=["POST"])
def add_channel():
    j = request.get_json()
    db.session.add(
        Channel(
            name=j["name"], youtube_id=j["youtube_id"], is_username=j["is_username"]
        )
    )
    db.session.commit()
    return "", 200


@app.route("/process", methods=["GET"])
def process():
    process_new_videos()
    return "", 200
