
from typing import Tuple, Optional
from sqlalchemy import ClauseElement, and_
from MessageMatchers.message_match import MessageMatch
from abstract_enrichment_module import AbstractEnrichmentModule
from MessageEnrichers.abstract_message_pattern_matcher import AbstractMessagePatternMatcher
from MessageMatchers.application_matcher__pattern_body import ApplicationMatcher_PatternBody
from apptracker_database.models import Message
from apptracker_database.email_address_dao import EmailAddressDAO
from apptracker_database.message_dao import MessageDAO
from apptracker_database.application_dao import ApplicationDAO

from sqlalchemy.orm import Session
import helper_functions as kafka_factory

class ApplicationPatternMatcher(AbstractMessagePatternMatcher):
    def __init__(self,
                 email_dao: EmailAddressDAO, message_dao: MessageDAO, application_dao: ApplicationDAO,
                 db: Session, config_path: str = "application_pattern_matching.yml"):

        super().__init__(db, config_path, "application_pattern_matching_exhaust.json")

        self.add_matcher(ApplicationMatcher_PatternBody(pattern_file=self._config_path))
        

        self._email_dao = email_dao
        self._message_dao = message_dao
        self._application_dao = application_dao

    def _process_matched_message(self, message: Message, matches: list[MessageMatch]) -> Tuple[bool, Optional[str]]:
        
        application = None
        candidate_applications = self._application_dao.get_applications_by_company_and_user(
            company_id=message.company_id, user_id=message.user_id, substring=matches[0].match_string
        )

        if not candidate_applications:
            application = self._application_dao.create_application(
                title=matches[0].match_string[:255],
                company_id=message.company_id,
                user_id=message.user_id,
                date_applied=message.date_received
            )
            print(f"🪄✨ Created new application: {application.title} for user {message.user_id} and company {message.company_id}")
        else:
            application = candidate_applications[0]
            print(f"🔍🎯 Found existing application: {application.title} for user {message.user_id} and company {message.company_id}")
        
        self._message_dao.update(message.id, application_id=application.id)
        return True, matches[0].match_string


LABEL_TOPIC = "gmail-label-requests"

class ApplicationEnrichmentModule(AbstractEnrichmentModule):
    def __init__(self, label_producer):
        super().__init__(label_producer)

    @property
    def message_filter(self) -> ClauseElement:
        return and_(
            Message.company_id.is_not(None),
            Message.application_id.is_(None)
        )
    
    def build_pattern_matcher(self, db: Session) -> AbstractMessagePatternMatcher:
        return ApplicationPatternMatcher(
            email_dao=EmailAddressDAO(db),
            message_dao=MessageDAO(db),
            application_dao=ApplicationDAO(db),
            db=db
        )
    
    @property
    def label_text(self) -> str:
        return "AppTracker/Application"

    def additional_log_data(self, message: Message) -> str:
        return f"from Email: {message.email_address.email} with Application ID: {message.application_id}"   

def main():
    label_producer = kafka_factory.initialize_kafka_producer(LABEL_TOPIC)
    module = ApplicationEnrichmentModule(label_producer=label_producer)
    enriched_count, considered_count = module.enrich()
    print(f"🎉🎉 Application enrichment completed successfully. Enriched {enriched_count} messages out of {considered_count} considered.", flush=True)
