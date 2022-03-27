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

HTTP_PORT=8056
REFRESH_INTERVAL_SECS=3600

schedule_url_poll http://localhost:$HTTP_PORT/process $REFRESH_INTERVAL_SECS &

env \
  FLASK_APP=youtube_audio_bot.app \
  FLASK_RUN_PORT=$HTTP_PORT \
  flask run
