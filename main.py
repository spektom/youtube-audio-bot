#!/usr/bin/env python3

import json
import logging
import os
import requests
import subprocess
import sys
import telegram
import time
import youtube_dl
import backoff

from datetime import datetime, timedelta, timezone

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
GOOGLE_API_TOKEN = os.getenv("GOOGLE_API_TOKEN")
TELEGRAM_FILE_SIZE_LIMIT = 48000000


def get_audio_duration(audio_file):
    p = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            audio_file,
        ],
        capture_output=True,
    )
    return float(p.stdout) if p.returncode == 0 else 0


def audio_convert_enhance(input_file, offset, size_limit, output_file):
    logging.info(f"processing '{input_file}', offset={offset}")
    # Convert to MP3 and normalize voice volume
    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-v",
            "error",
            "-i",
            input_file,
            "-af",
            f"compand=0|0:1|1:-90/-900|-70/-70|-30/-9|0/-3:6:0:0:0",
            "-acodec",
            "mp3",
            "-ss",
            str(offset),
            "-fs",
            str(size_limit),
            "-y",
            output_file,
        ]
    )


def split_audio(audio_file, duration_secs):
    if os.path.getsize(audio_file) < TELEGRAM_FILE_SIZE_LIMIT:
        return [(audio_file, duration_secs)]
    parts = []
    part_idx = 0
    offset = 0
    logging.info(f"splitting '{audio_file}', duration={duration_secs}")
    while offset < duration_secs:
        part_file = f"{audio_file}-{part_idx}.mp3"
        audio_convert_enhance(audio_file, offset, TELEGRAM_FILE_SIZE_LIMIT, part_file)
        part_len = get_audio_duration(part_file)
        if part_len == 0:
            os.remove(part_file)
            break
        logging.info(f"created '{part_file}', duration={part_len}")
        parts.append((part_file, part_len))
        offset += part_len
        part_idx += 1
    return parts


@backoff.on_exception(backoff.expo, Exception)
def send_file_to_telegram(audio_file, duration, author, title):
    logging.info(f"sending '{audio_file}', title='{title}', duration={duration}")
    with open(audio_file, "rb") as f:
        try:
            bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
            bot.send_audio(
                chat_id=TELEGRAM_CHANNEL_ID,
                audio=f,
                duration=duration,
                performer=author,
                title=title,
                caption=title,
            )
        except telegram.error.RetryAfter as r:
            logging.warning(f"retrying after {r.retry_after} secs")
            time.sleep(r.retry_after)
            raise r


def send_to_telegram(video_id, author, title, publish_date, audio_parts):
    for part_num, (audio_file, duration) in enumerate(audio_parts, 1):
        full_title = title
        if not any(char.isdigit() for char in title):
            full_title += " " + publish_date.strftime("%d.%m")
        if len(audio_parts) > 1:
            full_title += f" part {part_num}"
        full_title += f"\nOriginal: https://youtu.be/{video_id}"
        send_file_to_telegram(audio_file, duration, author, full_title)
        if len(audio_parts) > 1:
            time.sleep(20)


@backoff.on_exception(backoff.expo, Exception)
def youtube_download_audio(video_id):
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
    if duration == 0 or get_audio_duration(tmpfile) / float(duration) < 0.8:
        os.remove(tmpfile)
        raise Exception("downloaded file is too small")
    logging.info(f"saved '{tmpfile}', title='{title}', duration={duration}")
    return (tmpfile, author, title, duration)


def youtube_list_user_channels(user_name):
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


def youtube_list_channel_videos(channel_name, channel_id, published_after):
    logging.info(
        f"searching videos on '{channel_name}', published after {published_after.strftime('%Y/%m/%d')}"
    )
    r = requests.get(
        "https://www.googleapis.com/youtube/v3/search",
        params={
            "channelId": channel_id,
            "part": "snippet",
            "type": "video",
            "maxResults": 30,
            "order": "date",
            "publishedAfter": published_after.isoformat(),
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
        )
        results.append((video_id, video_date))
    logging.info(f"found {len(results)} new videos")
    return sorted(results, key=lambda v: v[1])


def process_video(video_id, publish_date):
    r = youtube_download_audio(video_id)
    if r is None:
        return False
    audio_file, author, title, duration_secs = r
    audio_parts = split_audio(audio_file, duration_secs)
    send_to_telegram(video_id, author, title, publish_date, audio_parts)
    os.remove(audio_file)
    for f, _ in audio_parts:
        os.remove(f)
    return True


def process_channels(channels):
    for channel in channels["channels"]:
        channel_ids = []
        if "channel_id" in channel:
            channel_ids.append(channel["channel_id"])
        else:
            channel_ids.extend(youtube_list_user_channels(channel["user_name"]))
        for channel_id in channel_ids:
            if "last_seen" in channel:
                from_date = datetime.fromisoformat(channel["last_seen"]) + timedelta(
                    seconds=1
                )
            else:
                from_date = datetime.now().replace(tzinfo=timezone.utc) - timedelta(
                    days=1
                )
            new_videos = youtube_list_channel_videos(
                channel["name"], channel_id, from_date
            )
            for video_id, video_date in new_videos:
                if process_video(video_id, video_date):
                    channel["last_seen"] = video_date.isoformat()
                    write_channels(channels)
            time.sleep(10)


def read_channels():
    with open("channels.json", "r") as f:
        return json.load(f)


def write_channels(channels):
    with open("channels.json", "w", encoding="utf-8") as f:
        return json.dump(channels, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(module)s: %(message)s"
    )
    process_channels(read_channels())
