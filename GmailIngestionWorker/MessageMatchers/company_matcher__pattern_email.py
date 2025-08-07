from MessageMatchers.abstract_message_matcher_stage import AbstractMessageMatcherStage
from MessageMatchers.message_match import MessageMatch
from RegExCompiler.regex_compiler import RegexCompiler
from apptracker_database.models import Message
from apptracker_database.company_dao import CompanyDAO

from sqlalchemy.orm import Session


import re


class CompanyMatcher_PatternEmail(AbstractMessageMatcherStage):
    def __init__(self, patterns="company_pattern_matching.yml"):
        self.regex_compiler = RegexCompiler(patterns)
        self._email_patterns = self.regex_compiler.get_patterns().get("email_patterns", {})

    def process(self, message: Message, db: Session) -> tuple[MessageMatch, bool]:
        matches = {}
        company_matches = []
        for pattern in self._email_patterns.values():
            match = re.match(pattern, message.email_address.email)
            try:
                if match and match.group(1):
                    if match.group(1) in matches.keys():
                        matches[match.group(1)].append(pattern)
                    else:
                        matches[match.group(1)] = [pattern]
            except IndexError:
                print(f"💥💀💥Pattern '{pattern}' did not match any group in email: {message.email_address.email}")
                # If the pattern does not have a group, we skip it
                continue

        if not matches:
            return (MessageMatch(message, "", None, "email_pattern", "No matching patterns"), False)

        most_common_company = max(matches, key=lambda k: len(matches[k]))

        company_dao = CompanyDAO(db)
        company = company_dao.get_company_by_name(most_common_company)
        if not company:
            company = company_dao.create_company(most_common_company)

        if company:
            message.company_id = company.id
            return (MessageMatch(message, company.name, company.id, "email_pattern", matches[most_common_company]), True)

        return (MessageMatch(message, "", None, "email_pattern", "Company not found or created"), False)