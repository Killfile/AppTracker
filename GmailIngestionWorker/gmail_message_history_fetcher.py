from apptracker_database.models import User
from apptracker_shared.gmail.gmail_gateway import GmailGateway

from gmail_gateway_factory import GmailGatewayFactory 

class GmailMessageHistoryFetcher:
    CRAWL_COMPLETE = "CRAWL_COMPLETE"

    def __init__(self, user: User):
        self.user_id = user.id
        self.max_results = 100
        self.page_token = None

        self.gateway = GmailGatewayFactory.build(user.id)

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
