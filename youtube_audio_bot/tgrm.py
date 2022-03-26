import logging
import os
import sys
import telegram
import time
import backoff

from datetime import datetime
from .app import db
from .model import TelegramMessages

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")
AUDIO_FILE_SIZE_LIMIT = 48000000


@backoff.on_exception(backoff.expo, Exception)
def send_audio_file(audio_file, duration, author, title):
    logging.info(f"sending '{audio_file}', title='{title}', duration={duration}")
    with open(audio_file, "rb") as f:
        try:
            bot = telegram.Bot(token=TELEGRAM_BOT_TOKEN)
            return bot.send_audio(
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


def format_title(video_id, title, publish_date, part_num, total_parts):
    if not any(char.isdigit() for char in title):
        title += " " + publish_date.strftime("%d.%m.%y")
    if total_parts > 1:
        title += f" часть {part_num}"
    title += f"\nоригинал: https://youtu.be/{video_id}"
    return title


def send_audio_files(
    video_id, author, title, publish_date, audio_parts, delay_between_parts_sec=20
):
    for part_num, (audio_file, duration) in enumerate(audio_parts, 1):
        formatted_title = format_title(
            video_id, title, publish_date, part_num, len(audio_parts)
        )
        message = send_audio_file(audio_file, duration, author, formatted_title)
        db.session.add(
            TelegramMessages(
                channel_id=message.chat.id,
                message_id=message.message_id,
                sent_on=datetime.utcnow(),
            )
        )
        db.session.commit()
        if len(audio_parts) > 1:
            time.sleep(delay_between_parts_sec)
