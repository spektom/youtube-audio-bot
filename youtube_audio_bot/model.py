from .app import app, db


class Channel(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.Text, nullable=False)
    youtube_id = db.Column(db.Text, nullable=False, unique=True)
    is_username = db.Column(db.Boolean, nullable=False, default=False)
    last_checked = db.Column(db.DateTime)


class SentMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    channel_id = db.Column(db.Integer)
    message_id = db.Column(db.Integer)
    sent_on = db.Column(db.DateTime)


def init_db():
    db.create_all()
