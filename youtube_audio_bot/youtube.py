import logging
import feedparser
import os
import requests
import youtube_dl
import backoff
import youtube_audio_bot.audio as audio

from datetime import datetime, timezone, timedelta

feedparser.USER_AGENT = (
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:78.0) Gecko/20100101 Firefox/78.0"
)


def extract_video(url, target_file, simulate):
    dl_opts = {
        "format": "bestaudio/best",
        "outtmpl": target_file,
        "quiet": True,
        "simulate": simulate,
    }
    downloader = youtube_dl.YoutubeDL(dl_opts)
    return downloader.extract_info(url)


@backoff.on_exception(backoff.expo, Exception, max_tries=8)
def download_audio(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    tmpfile = f".audio/{video_id}"
    try:
        logging.info(f"fetching info about '{url}'")
        info = extract_video(url, tmpfile, simulate=True)
        if info["is_live"]:
            logging.info(f"skipping live streaming video")
            return None
        author = info["uploader"]
        title = info["title"]
        duration = info["duration"]
        logging.info(f"downloading '{url}', title='{title}', duration={duration}")
        info = extract_video(url, tmpfile, simulate=False)
    except youtube_dl.utils.DownloadError as e:
        for allowed_error in [
            "confirm your age",
            "live event will begin",
            "requested format not available",
        ]:
            if allowed_error in str(e):
                return None
        raise e
    # Check that most of the file was downloaded correctly
    actual_duration = audio.get_duration(tmpfile)
    if duration == 0 or actual_duration / float(duration) < 0.8:
        os.remove(tmpfile)
        raise Exception(
            "downloaded file is too small (expected={duration}, actual={actual_duration})"
        )
    logging.info(f"saved '{tmpfile}', title='{title}', duration={duration}")
    return (tmpfile, author, title, duration)


def list_source_videos(source):
    published_after = (
        source.last_checked.astimezone(timezone.utc) + timedelta(seconds=1)
        if source.last_checked is not None
        else datetime.utcnow().astimezone(timezone.utc) - timedelta(days=1)
    )
    logging.info(f"listing videos on '{source.name}' published after {published_after}")
    arg = "user" if source.is_username else "channel_id"
    feed = feedparser.parse(
        f"https://www.youtube.com/feeds/videos.xml?{arg}={source.youtube_id}"
    )
    results = []
    for item in feed.entries:
        video_id = item["yt_videoid"]
        update_time = datetime.fromisoformat(item["updated"])
        publish_time = datetime.fromisoformat(item["published"])
        if update_time <= published_after:
            continue
        logging.info(f"found new video '{video_id}' published at {publish_time}")
        results.append((video_id, publish_time))
    logging.info(f"found {len(results)} videos")
    return sorted(results, key=lambda r: r[1])
