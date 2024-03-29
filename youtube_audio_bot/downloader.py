import logging
import os
import youtube_audio_bot.tgrm as tgrm
import youtube_audio_bot.youtube as youtube
import youtube_audio_bot.audio as audio

from .app import db
from .model import YoutubeSources, ProcessedVideos


def process_video(video_id, publish_date):
    if (
        ProcessedVideos.query.filter(ProcessedVideos.video_id == video_id).first()
        is not None
    ):
        logging.debug(f"skipping already processed video '{video_id}'")
        return False
    r = youtube.download_audio(video_id)
    if r is None:
        return False
    audio_file, author, title, duration_secs = r
    audio_parts = audio.split_convert_to_ogg(
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
        new_videos = youtube.list_source_videos(source)
        for video_id, video_date in new_videos:
            if process_video(video_id, video_date):
                source.last_checked = video_date
                db.session.commit()
