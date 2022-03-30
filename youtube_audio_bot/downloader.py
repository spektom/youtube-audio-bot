import logging
import os
import youtube_audio_bot.tgrm as tgrm
import youtube_audio_bot.youtube as youtube
import youtube_audio_bot.audio as audio

from datetime import datetime, timedelta, timezone
from .app import db
from .model import YoutubeSources, ProcessedVideos


def process_video(video_id, publish_date):
    if (
        ProcessedVideos.query.filter(ProcessedVideos.video_id == video_id).first()
        is not None
    ):
        logging.info(f"skipping already processed video '{video_id}'")
        return False
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
    db.session.add(ProcessedVideos(video_id=video_id))
    return True


def process_new_videos():
    for source in YoutubeSources.query.all():
        channel_ids = []
        if source.is_username:
            channel_ids.extend(youtube.list_user_channels(source.youtube_id))
        else:
            channel_ids.append(source.youtube_id)
        for channel_id in channel_ids:
            if source.last_checked is not None:
                from_date = source.last_checked.astimezone(timezone.utc) + timedelta(
                    seconds=1
                )
            else:
                from_date = datetime.utcnow().astimezone(timezone.utc) - timedelta(
                    days=1
                )
            new_videos = youtube.list_channel_videos(source.name, channel_id, from_date)
            for video_id, video_date in new_videos:
                if process_video(video_id, video_date):
                    source.last_checked = video_date
                    db.session.commit()
