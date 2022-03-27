import logging

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from pathlib import Path

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(module)s: %(message)s"
)

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///{}/database.db".format(
    Path(__file__).parent.parent.absolute()
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"timeout": 15}}

db = SQLAlchemy(app)

from .model import init_db
from .api import *

init_db()
