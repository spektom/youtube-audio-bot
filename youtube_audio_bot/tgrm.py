import logging
import os
import sys
import telegram
import time
import backoff
import asyncio

from datetime import datetime, timedelta
from .app import db
from .config import get_conf
from .model import TelegramMessages
from telethon.sync import TelegramClient, events

AUDIO_FILE_SIZE_LIMIT = 48000000


def create_bot():
    return telegram.Bot(token=get_conf("telegram_bot_token"))


@backoff.on_exception(backoff.expo, Exception)
def send_audio_file(audio_file, duration, author, title):
    logging.info(
        f"sending '{audio_file}', title='{title}', duration={timedelta(seconds=duration)}"
    )
    chat_id = get_conf("telegram_channel_id")
    with open(audio_file, "rb") as f:
        try:
            bot = create_bot()
            return bot.send_audio(
                chat_id=chat_id,
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


def delete_old_messages(days_back=7):
    sent_ago = datetime.utcnow() - timedelta(days=days_back)
    logging.info(f"deleting Telegram messages sent before {sent_ago}")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    with TelegramClient(
        "youtube-audio-bot",
        get_conf("telegram_api_id"),
        get_conf("telegram_api_hash"),
        loop=loop,
    ) as client:
        channel = client.get_entity(int(get_conf("telegram_channel_id")))
        ids = []
        for message in client.iter_messages(channel):
            if message.date.timestamp() < sent_ago.timestamp():
                ids.append(message.id)
        client.delete_messages(entity=channel, message_ids=ids)
