from functools import lru_cache
from apptracker_database.user_dao import UserDAO
from apptracker_database.database import SessionLocal
from apptracker_shared.gmail.gmail_gateway import GmailGateway 

class GmailGatewayFactory:
    def __init__(self):
        raise RuntimeError("UserGatewayFactory is a singleton and should not be instantiated directly. Use user_gateway_factory(user_id) instead.")
    
    @staticmethod
    @lru_cache(maxsize=128)
    def build(user_id):
        print(f"⚒️⚒️Building GmailGateway for user ID {user_id}", flush=True)
        with SessionLocal() as db:
            userDAO = UserDAO(db)
            user = userDAO.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found.")
        gateway = GmailGateway(access_token=user.google_access_token, refresh_token=user.google_refresh_token, user_id=user.google_id)
        return gateway