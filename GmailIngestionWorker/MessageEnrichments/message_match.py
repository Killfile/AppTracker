from apptracker_database.models import Message


class MessageMatch:
    def __init__(self, message: Message, company_name: str, company_id: int, match_type: str, match_detail: str):
        self.message = message
        self.company_name = company_name
        self.company_id = company_id
        self.match_type = match_type
        self.match_detail = match_detail