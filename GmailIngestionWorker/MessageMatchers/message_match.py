from apptracker_database.models import Message


class MessageMatch:
    def __init__(self, message: Message, match_string: str, match_id: int, match_type: str, match_detail: str):
        self.message = message
        self.match_string = match_string
        self.match_id = match_id
        self.match_type = match_type
        self.match_detail = match_detail