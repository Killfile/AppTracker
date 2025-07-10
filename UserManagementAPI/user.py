from apptracker_database.database import SessionLocal
from apptracker_database.models import User as DBUser
from flask_login import UserMixin

class AppUser(UserMixin):
    def __init__(self, base_user):
        self._base = base_user

    def __getattr__(self, name):
        return getattr(self._base, name)

    def get_id(self):
        return str(self._base.id)