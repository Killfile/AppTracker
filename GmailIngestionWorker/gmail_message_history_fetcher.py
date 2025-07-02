from apptracker_database.user_dao import UserDAO
from apptracker_database.models import User
from apptracker_shared.gmail.gmail_gateway import GmailGateway 

class GmailMessageHistoryFetcher:
    CRAWL_COMPLETE = "CRAWL_COMPLETE"

    def __init__(self, user: User):
        self._user:User = user
      
        if not user.google_access_token or not user.google_id:
            raise ValueError(f"No Google access token and/or google_id found. Refresh login for " + user.username)

        self.max_results = 100
        self.page_token = None

        self.gateway = GmailGateway(self._user.google_access_token, self._user.google_refresh_token, user_id=self._user.google_id)

    def fetch_history_page(self) -> list:
        if self.page_token == GmailMessageHistoryFetcher.CRAWL_COMPLETE:
            return []
        
        message_block = self.gateway.list_messages(
            max_results=self.max_results,
            page_token=self.page_token
        )

        try:
            self.page_token = message_block.nextPageToken
        except AttributeError:
            # If nextPageToken is not present, we assume we have reached the end of the crawl
            self.page_token = GmailMessageHistoryFetcher.CRAWL_COMPLETE
            print(f"GmailMessageHistoryFetcher.fetch_history_page: Fetched {len(message_block.messages) if message_block.messages else 0} messages with page token: {self.page_token}.", flush=True)
            print(f"Message block: {message_block.model_dump()}", flush=True)

        
        return (message_block.model_dump())["messages"]
