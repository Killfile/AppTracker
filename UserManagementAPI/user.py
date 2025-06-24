from apptracker_database.database import SessionLocal
from apptracker_database.models import User as DBUser
from flask_login import UserMixin

class User(DBUser, UserMixin):
    @classmethod
    def get(cls, *args, **kwargs):
        with SessionLocal() as db:
            return db.query(cls).get(*args, **kwargs)
    pass