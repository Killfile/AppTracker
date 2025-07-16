from typing import List

from apptracker_database.models import Message
from apptracker_database.email_address_dao import EmailAddressDAO
from apptracker_database.message_dao import MessageDAO
from apptracker_database.email_company_link_dao import EmailCompanyLinkDAO
from apptracker_database.company_dao import CompanyDAO

from apptracker_database.database import SessionLocal
from sqlalchemy.orm import Session
from gmail_gateway_factory import GmailGatewayFactory
import helper_functions as kafka_factory


from MessageEnrichments.company_enrichment__known_email_address import CompanyEnrichment_KnownEmailAddress
from MessageEnrichments.abstract_message_enrichment_stage import AbstractMessageEnrichmentStage
from MessageEnrichments.company_enrichment__pattern_email import CompanyEnrichment_PatternEmail
from MessageEnrichments.company_enrichment__pattern_subject import CompanyEnrichment_PatternSubject
from MessageEnrichments.company_enrichment__pattern_body import CompanyEnrichment_PatternBody
from MessageEnrichments.message_match import MessageMatch

LABEL_TOPIC = "gmail-label-requests"

class CompanyNamePatternMatcher:
    def __init__(self, config_path: str = "company_pattern_matching.yml", db: Session = None):
        self._config_path = config_path
        self._db = db
        self._matchers: list[AbstractMessageEnrichmentStage] = [
            CompanyEnrichment_KnownEmailAddress(patterns=self._config_path),
            CompanyEnrichment_PatternEmail(patterns=self._config_path),
            CompanyEnrichment_PatternBody(patterns=self._config_path),
            CompanyEnrichment_PatternSubject(patterns=self._config_path),
        ]
        
    def get_matches_from_message(self, message: Message) -> List[MessageMatch]:
        for matcher in self._matchers:
            matches, done = matcher.process(message, self._db)
            if done:
                return [matches]
        return []

class CompanyEnrichmentModule:
    def __init__(self, label_producer):
        self._gmail_label_producer = label_producer

    def label_message(self, gateway, user_id, label_name, message_id):
        label_id = gateway.create_or_get_label(label_name=label_name)
        message = {
            "user_id": user_id,
            "label_id": label_id,
            "message_id": message_id}
        self._gmail_label_producer.send(message)

    def _get_message_batch(self, db, page_size = 100, page=0) -> List[Message]:

        dao = MessageDAO(db)
        batch = dao.get_messages_with_email_addresses(limit = page_size, offset=page * page_size, filter_clause = Message.company_id.is_(None))
        return batch

    def enrich(self) -> tuple[int, int]:
        enriched = 0
        considered = 0
        with SessionLocal() as db:
            pattern_matcher = CompanyNamePatternMatcher(db=db)
            message_dao = MessageDAO(db)
            page = 0
            while batch := self._get_message_batch(db, page_size=100, page=page):
                for message in batch:
                    considered += 1
                    matches = pattern_matcher.get_matches_from_message(message)
                    if not matches:
                        continue
                    message = matches[0].message
                    if not message:
                        continue
                    message_dao.update(message.id, company_id=message.company_id)
                    email = EmailAddressDAO(db).get_by_email(message.email_address.email)
                    if not email:
                        raise ValueError(f"Email address {message.email_address.email} not found in database.  This should not happen.")
                    email_company_link_dao = EmailCompanyLinkDAO(db)
                    mapping_source = f"{matches[0].match_type} - {matches[0].match_detail}"[:63]
                    if email_company_link_dao.get_link(email.id, message.company_id):
                        print(f"🔗 Email {email.email} already linked to company {message.company_id}. Skipping", flush=True)
                        continue
                    print(f"🔗 Linking email {email.email} to company {message.company_id} with source {mapping_source}", flush=True)
                    email_company_link_dao.create_link(
                        email_address_id=email.id,
                        company_id=message.company_id,
                        confidence_score=1.0,  # Assuming full confidence for now
                        source=mapping_source,
                        is_verified=True
                    )
                    gateway = GmailGatewayFactory.build(message.user_id)
                    self.label_message(
                        gateway=gateway,
                        user_id=message.user_id,
                        label_name="AppTracker: Company Found",
                        message_id=message.gmail_message_id
                    )
                    print(f"✉️💰 Enriched message {message.id} with company {message.company_id} from email {message.email_address.email}", flush=True)
                    enriched += 1
                page += 1
        return enriched, considered

def main():
    label_producer = kafka_factory.initialize_kafka_producer(LABEL_TOPIC)
    module = CompanyEnrichmentModule(label_producer=label_producer)
    enriched_count, considered_count = module.enrich()
    print(f"🎉🎉 Company enrichment completed successfully. Enriched {enriched_count} messages out of {considered_count} considered.", flush=True)




            

        
            
        
                
    

    

    
