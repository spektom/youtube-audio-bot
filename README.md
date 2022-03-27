youtube-audio-bot
==================

Delivers audio from your favorite YouTube channels to a Telegram channel.

The scheme of operation:

 * The process uses Google API key to go over favorite YouTube channels and users,
   and finds new videos posted since the last time a video was processed from that channel.
 * Audio streams of newly posted videos are downloaded using `youtube-dl` utility.
 * Downloaded audio undergo a voice enhancement process using `ffmpeg`, which equalizes spikes and decays in voices levels.
 * Processed audio stream is split into chunks with size lower than 50Mb, which is a limit for voice message in Telegram.
 * The files are delivered to the Telegram channel.


## Prerequisites

 * Linux or Windows WSL environment.
 * Python3
 * ffmpeg

To install all the dependencies on Ubuntu-like system, run:

```bash
apt install -y ffmpeg \
      python3 python3-wheel python3-venv python3-pip
```

## Configuration

Refer to [updating configuration](#updating-configuration) section below.

## Running

Use `run.sh` to run the process.
The script invokes `setup.sh` on the first run, if the Python environment is not prepared yet.

## HTTP Endpoints

### Updating configuration

The following configuration values must be set:

 * `telegram_bot_token` - Token key of the Telegram Bot that delivers audio messages.
 * `telegram_channel_id` - ID of the Telegram channel audio messages will be sent to.
 * `google_api_token` - Google API key used for searching new YouTube channel videos.

Updating configuration using API:

```bash
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"telegram_bot_token": "...", "telegram_channel_id": "...", "google_api_token": "..."}' \
     http://localhost:8056/config
```

### Adding new YouTube channel

Adding a YouTube channel:

```bash
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"name": "Живой гвоздь", "youtube_id": "UCWAIvx2yYLK_xTYD4F2mUNw", "is_username": false}' \
     http://localhost:8056/sources
```

### Adding new YouTube username:

```bash
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"name": "Сергей Пархоменко", "youtube_id": "sparkhom", "is_username": true}' \
     http://localhost:8056/sources
```
