import youtube_audio_bot.tgrm as tgrm
import youtube_audio_bot.youtube as youtube
import youtube_audio_bot.audio as audio
import youtube_audio_bot.downloader as downloader

from flask import request
from .app import app, db
from .model import Config, YoutubeSources


@app.route("/config", methods=["POST"])
def edit_config():
    j = request.get_json()
    for key, value in j.items():
        db.session.merge(Config(key=key, value=value))
    db.session.commit()
    return "", 200


@app.route("/sources", methods=["POST"])
def add_source():
    j = request.get_json()
    db.session.add(
        YoutubeSources(
            name=j["name"], youtube_id=j["youtube_id"], is_username=j["is_username"]
        )
    )
    db.session.commit()
    return "", 200


@app.route("/process", methods=["GET"])
def process():
    tgrm.delete_old_messages()
    downloader.process_new_videos()
    return "", 200
