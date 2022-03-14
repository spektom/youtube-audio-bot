#!/bin/bash -eu

[ ! -d venv ] && ./setup.sh
if [ -z ${VIRTUAL_ENV+x} ]; then
  source venv/bin/activate
fi

. config.sh
while true; do
  TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN \
  TELEGRAM_CHANNEL_ID=$TELEGRAM_CHANNEL_ID \
  GOOGLE_API_TOKEN=$GOOGLE_API_TOKEN \
    python main.py "$@"
  sleep $REFRESH_INTERVAL_SECS
done
