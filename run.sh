#!/bin/bash -eu

schedule_url_poll() {
  set +e
  sleep 5
  while true
  do
    curl -sSf $1 > /dev/null
    sleep $2
  done
}

cleanup() {
  pkill -P $$ >/dev/null
}

trap cleanup EXIT

[ ! -d venv ] && ./setup.sh
if [ -z ${VIRTUAL_ENV+x} ]; then
  source venv/bin/activate
fi

. config.sh

schedule_url_poll http://localhost:$HTTP_PORT/process $REFRESH_INTERVAL_SECS &

env TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN \
  TELEGRAM_CHANNEL_ID=$TELEGRAM_CHANNEL_ID \
  GOOGLE_API_TOKEN=$GOOGLE_API_TOKEN \
  FLASK_APP=youtube_audio_bot.app FLASK_RUN_PORT=$HTTP_PORT \
  flask run
