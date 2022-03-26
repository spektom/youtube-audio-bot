import logging
import os
import requests
import youtube_dl
import backoff
import youtube_audio_bot.audio as audio

from datetime import datetime, timezone

GOOGLE_API_TOKEN = os.getenv("GOOGLE_API_TOKEN")


@backoff.on_exception(backoff.expo, Exception)
def download_audio(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    logging.info(f"downloading audio from '{url}'")
    tmpfile = f".audio/{video_id}"
    try:
        downloader = youtube_dl.YoutubeDL(
            {"format": "bestaudio/best", "outtmpl": tmpfile, "quiet": True}
        )
        info = downloader.extract_info(url)
    except youtube_dl.utils.DownloadError as e:
        if "requested format not available" in str(e):
            logging.warning(str(e))
            return None
        raise e
    author = info["uploader"]
    title = info["title"]
    duration = info["duration"]
    # Check that most of the file was downloaded correctly
    if duration == 0 or audio.get_duration(tmpfile) / float(duration) < 0.8:
        os.remove(tmpfile)
        raise Exception("downloaded file is too small")
    logging.info(f"saved '{tmpfile}', title='{title}', duration={duration}")
    return (tmpfile, author, title, duration)


def list_user_channels(user_name):
    logging.info(f"listing channels for user '{user_name}'")
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/channels",
        params={
            "part": "contentDetails",
            "maxResults": 5,
            "forUsername": user_name,
            "key": GOOGLE_API_TOKEN,
        },
    )
    r.raise_for_status()
    j = r.json()
    return [item["id"] for item in j["items"]]


def list_channel_videos(channel_name, channel_id, published_after):
    published_after = published_after.strftime("%Y-%m-%dT%H:%M:%S") + "Z"
    logging.info(
        f"searching videos on '{channel_name}', published after {published_after}"
    )
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "channelId": channel_id,
            "part": "snippet",
            "type": "video",
            "maxResults": 30,
            "order": "date",
            "publishedAfter": published_after,
            "key": GOOGLE_API_TOKEN,
        },
    )
    r.raise_for_status()
    j = r.json()
    results = []
    for item in j["items"]:
        if item["snippet"]["liveBroadcastContent"] == "upcoming":
            continue
        if "videoId" not in item["id"]:
            continue
        video_id = item["id"]["videoId"]
        video_date = datetime.strptime(
            item["snippet"]["publishTime"], "%Y-%m-%dT%H:%M:%S%z"
        ).astimezone(timezone.utc)
        logging.info(f"found new video '{video_id}' published at {video_date}")
        results.append((video_id, video_date))
    logging.info(f"found {len(results)} new videos")
    return sorted(results, key=lambda v: v[1])
