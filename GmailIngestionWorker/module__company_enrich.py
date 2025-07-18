
from sqlalchemy import ClauseElement
from abstract_enrichment_module import AbstractEnrichmentModule
from MessageEnrichers.abstract_message_pattern_matcher import AbstractMessagePatternMatcher
from apptracker_database.models import Message
from apptracker_database.email_address_dao import EmailAddressDAO
from apptracker_database.message_dao import MessageDAO
from apptracker_database.email_company_link_dao import EmailCompanyLinkDAO

from sqlalchemy.orm import Session
import helper_functions as kafka_factory

from MessageMatchers.company_matcher__known_email_address import CompanyMatcher_KnownEmailAddress
from MessageMatchers.company_matcher__pattern_body import CompanyMatcher_PatternBody
from MessageMatchers.company_matcher__pattern_email import CompanyMatcher_PatternEmail
from MessageMatchers.company_matcher__pattern_subject import CompanyMatcher_PatternSubject


class CompanyNamePatternMatcher(AbstractMessagePatternMatcher):
    def __init__(self,
                 email_dao: EmailAddressDAO, message_dao: MessageDAO, link_dao: EmailCompanyLinkDAO,
                 db: Session, config_path: str = "company_pattern_matching.yml"):

        super().__init__(db, config_path)

        self.add_matcher(CompanyMatcher_KnownEmailAddress(patterns=self._config_path))
        self.add_matcher(CompanyMatcher_PatternEmail(patterns=self._config_path))
        self.add_matcher(CompanyMatcher_PatternSubject(patterns=self._config_path))
        self.add_matcher(CompanyMatcher_PatternBody(patterns=self._config_path))

        self._email_dao = email_dao
        self._message_dao = message_dao
        self._link_dao = link_dao

    def _process_matched_message(self, message: Message, matches) -> bool:
        
        self._message_dao.update(message.id, company_id=message.company_id)
        email = self._email_dao.get_by_email(message.email_address.email)
        if not email:
            raise ValueError(f"Email address {message.email_address.email} not found in database.  This should not happen.")

        mapping_source = f"{matches[0].match_type} - {matches[0].match_detail}"[:63]
        if self._link_dao.get_link(email.id, message.company_id):
            print(f"🔗 Email {email.email} already linked to company {message.company_id}. Skipping", flush=True)
            return False
        print(f"🔗 Linking email {email.email} to company {message.company_id} with source {mapping_source}", flush=True)
        self._link_dao.create_link(
            email_address_id=email.id,
            company_id=message.company_id,
            confidence_score=1.0,  # Assuming full confidence for now
            source=mapping_source,
            is_verified=True
        )
        return True


LABEL_TOPIC = "gmail-label-requests"

class CompanyEnrichmentModule(AbstractEnrichmentModule):
    def __init__(self, label_producer):
        super().__init__(label_producer)

    @property
    def message_filter(self) -> ClauseElement:
        return Message.company_id.is_(None)

    def build_pattern_matcher(self, db: Session) -> AbstractMessagePatternMatcher:
        return CompanyNamePatternMatcher(
            email_dao=EmailAddressDAO(db),
            message_dao=MessageDAO(db),
            link_dao=EmailCompanyLinkDAO(db),
            db=db
        )
    
    @property
    def label_text(self) -> str:
        return "AppTracker: Company Found"
    
    def additional_log_data(self, message: Message) -> str:
        return f"from Email: {message.email_address.email} with Company ID: {message.company_id}"   

def main():
    label_producer = kafka_factory.initialize_kafka_producer(LABEL_TOPIC)
    module = CompanyEnrichmentModule(label_producer=label_producer)
    enriched_count, considered_count = module.enrich()
    print(f"🎉🎉 Company enrichment completed successfully. Enriched {enriched_count} messages out of {considered_count} considered.", flush=True)
