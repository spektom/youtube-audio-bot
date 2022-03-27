from .app import db
from .model import Config


def get_conf(key):
    conf = Config.query.filter_by(key=key).first()
    if conf is None:
        raise Exception(f"configuration '{key}' is missing!")
    return conf.value
