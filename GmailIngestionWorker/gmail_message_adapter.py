import base64
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional, Dict, Any, List

class GmailMessageAdapter:
    DECODED_BODY_KEY = "apptracker_decoded_body"
    """
    Lightweight adapter for Gmail API message dicts, providing access to common email fields.
    """
    def __init__(self, message: Dict[str, Any]):
        self.message = message
        self.payload = message.get("payload", {})
        self.headers = self.payload.get("headers", [])

    def _get_header(self, name: str) -> Optional[str]:
        for header in self.headers:
            if header.get("name", "").lower() == name.lower():
                return header.get("value")
        return None
    
    @property
    def gmail_message_id(self) -> str:
        """
        Returns the unique Gmail message ID.
        """
        return self.message.get("id", "")

    @property
    def to(self) -> Optional[str]:
        return self._get_header("To")

    @property
    def from_address(self) -> Optional[str]:
        return self._get_header("From")
    
    @property
    def domain(self) -> Optional[str]:
        """
        Extracts the domain from the 'From' address.
        """
        from_address = self.from_address
        if from_address:
            return from_address.split('@')[-1].lower().rstrip(">")
        return None

    @property
    def reply_to(self) -> Optional[str]:
        return self._get_header("Reply-To")
    
    @property
    def date(self) -> Optional[str]:
        return self._get_header("Date")
    
    @property
    def datestamp(self) -> Optional[datetime]:
        if self.date:
            return parsedate_to_datetime(self.date)
        else:
            return None

    @property
    def subject(self) -> Optional[str]:
        return self._get_header("Subject")

    @property
    def body(self) -> str:
        """
        Returns the decoded body text (prefers text/plain, falls back to text/html if needed).
        Handles base64 decoding and multipart structures.
        """
        def decode_body(body_dict: Dict[str, Any]) -> str:
            data = body_dict.get("data")
            if data:
                # Gmail API uses URL-safe base64 encoding
                decoded = base64.urlsafe_b64decode(data + '===').decode("utf-8", errors="ignore")
                return decoded
            return ""

        
        if self.message.get(self.DECODED_BODY_KEY):
            return self.message[self.DECODED_BODY_KEY]

        # If multipart, search for text/plain first, then text/html
        parts: List[Dict[str, Any]] = self.payload.get("parts", [])
        if parts:
            for mime in ("text/plain", "text/html"):
                for part in parts:
                    if part.get("mimeType") == mime:
                        self.message[self.DECODED_BODY_KEY] = decode_body(part.get("body", {}))
                        return self.message[self.DECODED_BODY_KEY]
        # If not multipart, or no matching part, try the main body
        self.message[self.DECODED_BODY_KEY] = decode_body(self.payload.get("body", {}))
        return self.message[self.DECODED_BODY_KEY]
