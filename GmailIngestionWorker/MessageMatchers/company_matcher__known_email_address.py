from MessageMatchers.abstract_message_matcher_stage import AbstractMessageMatcherStage
from MessageMatchers.message_match import MessageMatch
from apptracker_database.models import Message
from apptracker_database.email_company_link_dao import EmailCompanyLinkDAO

from sqlalchemy.orm import Session
from sqlalchemy.orm import Session


import re


class CompanyMatcher_KnownEmailAddress(AbstractMessageMatcherStage):
    def __init__(self, patterns="company_pattern_matching.yml"):
        config = self._load_yml_config(patterns)
        self._blacklisted_email_patterns = config["email_blacklist"]

    def _is_blacklisted(self, email_address)->bool:
        for value in self._blacklisted_email_patterns:
            if re.search(value, email_address):
                return True
        return False

    def process(self, message: Message, db: Session) -> tuple[MessageMatch, bool]:
        # Checks to see if we're done already; should never happen
        if message.company_id:
            return (MessageMatch(message, "", message.company_id, "known_email", "Pre-Mapped"), True)
        if self._is_blacklisted(message.email_address.email):
            return (MessageMatch(message, "", None, "known_email", "BLACKLIST"), False)
        email_company_link_dao = EmailCompanyLinkDAO(db)
        links = email_company_link_dao.list_links_for_email(message.email_address.id)
        if links:
            message.company_id = links[0].company_id
            return (MessageMatch(message, "", message.company_id, "known_email", f"{links[0].company_id} - {len(links)} options"), True)
        return (MessageMatch(message, "", None, "unknown_email", "unkown"), False)