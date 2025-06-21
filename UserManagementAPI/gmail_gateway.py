from typing import List, Optional
from pydantic import BaseModel
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

class GmailMessage(BaseModel):
    id: str
    threadId: str
    snippet: Optional[str]
    historyId: Optional[str]
    internalDate: Optional[str]
    labelIds: Optional[List[str]]
    payload: Optional[dict]
    sizeEstimate: Optional[int]

class GmailListMessagesResponse(BaseModel):
    messages: Optional[List[GmailMessage]]
    nextPageToken: Optional[str]
    resultSizeEstimate: Optional[int]

class GmailGateway:
    def __init__(self, access_token: str, user_id: str = 'me'):
        self.user_id = user_id
        creds = Credentials(token=access_token)
        
        self.service = build('gmail', 'v1', credentials=creds)

    def list_messages(self, max_results: int = 10, page_token: Optional[str] = None) -> GmailListMessagesResponse:
        
        
        params = {
            'userId': self.user_id,
            'maxResults': max_results
        }
        if page_token:
            params['pageToken'] = str(page_token)
        print(f"GmailGateway.list_messages: gmail.users().messages().list({params})", flush=True)
        result = self.service.users().messages().list(**params).execute()
        messages = []
        for msg in result.get('messages', []):
            msg_detail = self.get_message(msg['id'])
            messages.append(msg_detail)
        return GmailListMessagesResponse(messages=messages, nextPageToken=result.get('nextPageToken'), resultSizeEstimate=result.get('resultSizeEstimate'))

    def get_message(self, message_id: str) -> GmailMessage:
        print(f"GmailGateway.get_message: gmail.users().messages().get(userId={self.user_id}, id={message_id})", flush=True)
        msg = self.service.users().messages().get(userId=self.user_id, id=message_id).execute()
        return GmailMessage(**msg)
