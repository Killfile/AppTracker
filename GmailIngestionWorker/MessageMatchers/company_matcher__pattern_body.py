from MessageMatchers.abstract_message_matcher_stage import AbstractMessageMatcherStage
from MessageMatchers.message_match import MessageMatch
from apptracker_database.models import Message
from apptracker_database.company_dao import CompanyDAO

from sqlalchemy.orm import Session


import re


class CompanyMatcher_PatternBody(AbstractMessageMatcherStage):
    def __init__(self, patterns="company_pattern_matching.yml"):
        config = self._load_yml_config(patterns)
        self._body_patterns = config["body_patterns"]

    def process(self, message: Message, db: Session) -> tuple[MessageMatch, bool]:
        for pattern in self._body_patterns:
            match = re.search(pattern, str(message.message_body))
            if match and match.group(1):
                company_name = match.group(1)
                company_dao = CompanyDAO(db)
                company = company_dao.get_company_by_name(company_name)
                if not company:
                    company = company_dao.create_company(company_name)
                if company:
                    message.company_id = company.id
                    return (MessageMatch(message, company.name, company.id, "body_pattern", pattern), True)
        return (MessageMatch(message, "", None, "body unmatched", ""), False)