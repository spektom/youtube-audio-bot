youtube-audio-bot
==================

Delivers audio from your favorite YouTube channels to a Telegram channel.

The scheme of operation:

 * The process uses Google API key to go over all YouTube channels and users listed in `channels.json` file,
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

The following parameters must be set in `config.sh` file:

 * `TELEGRAM_BOT_TOKEN` - Token key of the Telegram Bot that delivers audio messages.
 * `TELEGRAM_CHANNEL_ID` - ID of the Telegram channel audio messages will be sent to.
 * `GOOGLE_API_TOKEN` - Google API key used for searching new YouTube channel videos.
 * `REFRESH_INTERVAL_SECS` - Script run frequency in seconds.
 * `HTTP_PORT` - HTTP port on which the Web service will be listening.

## Running

Use `run.sh` to run the process.
The script invokes `setup.sh` on the first run, if the Python environment is not prepared yet.

## HTTP Endpoints

### Adding new YouTube channel

Adding a YouTube channel:

```bash
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"name": "Живой гвоздь", "youtube_id": "UCWAIvx2yYLK_xTYD4F2mUNw", "is_username": false}' \
     http://localhost:$HTTP_PORT/channels
```

Adding a YouTube username:

```bash
curl -X POST \
     -H "Content-Type: application/json" \
     -d '{"name": "Сергей Пархоменко", "youtube_id": "sparkhom", "is_username": true}' \
     http://localhost:$HTTP_PORT/channels
```
