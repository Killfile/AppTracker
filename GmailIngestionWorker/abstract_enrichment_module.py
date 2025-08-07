from sqlalchemy import ClauseElement
from MessageEnrichers.abstract_message_pattern_matcher import AbstractMessagePatternMatcher
from gmail_gateway_factory import GmailGatewayFactory
from apptracker_database.database import SessionLocal
from apptracker_database.message_dao import MessageDAO
from apptracker_database.models import Message


from sqlalchemy.orm import Session


from abc import ABC, abstractmethod
from typing import List
import json


class AbstractEnrichmentModule(ABC):
    def __init__(self, label_producer):
        self._gmail_label_producer = label_producer

    @property
    @abstractmethod
    def label_text(self) -> str:
        raise NotImplementedError("Subclasses should implement this property to return the label text.")
    
    @property
    @abstractmethod
    def message_filter(self) -> ClauseElement:
        raise NotImplementedError("Subclasses should implement this property to return the message filter clause.")
    
    @property
    @abstractmethod
    def exhaust_filename(self) -> str:
        raise NotImplementedError("Subclasses should implement this property to return the exhaust filename.")  

    def label_message(self, gateway, user_id, label_name, message_id):
        label_id = gateway.create_or_get_label(label_name=label_name)
        message = {
            "user_id": user_id,
            "label_id": label_id,
            "message_id": message_id}
        self._gmail_label_producer.send(message)

    def additional_log_data(self, message: Message) -> str:
        return ""

    def record_enrichement(self, message: Message, label: str):
        gateway = GmailGatewayFactory.build(message.user_id)

        
        
        self.label_message(
            gateway=gateway,
            user_id=message.user_id,
            label_name=label,
            message_id=message.gmail_message_id
        )
        print(f"✉️💰 Enriched message {message.id} {self.additional_log_data(message)}", flush=True)

    def _get_message_batch(self, db, page_size = 100, page=0) -> List[Message]:
        dao = MessageDAO(db)
        batch = dao.get_messages_with_email_addresses(limit = page_size, offset=page * page_size, filter_clause = self.message_filter)
        return batch

    @abstractmethod
    def build_pattern_matcher(self, db: Session) -> AbstractMessagePatternMatcher:
        raise NotImplementedError("This method should be implemented by subclasses")

    def enrich(self) -> tuple[int, int]:
        enriched = 0
        considered = 0
        with SessionLocal() as db:

            pattern_matcher = self.build_pattern_matcher(db)
            page = 0
            while batch := self._get_message_batch(db, page_size=100, page=page):
                for message in batch:
                    considered += 1
                    success, match = pattern_matcher.process_message(message)
                    if success:
                        enriched += 1

                        self.record_enrichement(message, label=f"{self.label_text}/{match}")
                page += 1
        return enriched, considered