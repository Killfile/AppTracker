import re
import yaml
from typing import Optional, Tuple
from MessageMatchers.abstract_message_matcher_stage import AbstractMessageMatcherStage
from MessageMatchers.message_match import MessageMatch
from apptracker_database.models import Message

class ApplicationMatcher_PatternBody(AbstractMessageMatcherStage):
    def __init__(self, pattern_file: str = "application_pattern_matching.yml"):
        with open(pattern_file, 'r', encoding='utf-8') as f:
            self.patterns = yaml.safe_load(f)['application_patterns']

    def extract_application(self, text: str) -> Optional[Tuple[str, str]]:
        for pattern in self.patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip(), pattern
        return None

    def process(self, message: Message, db=None) -> Tuple[MessageMatch, bool]:
        result = self.extract_application(message.message_body)
        if result:
            app_title, pattern = result
            return (MessageMatch(message, app_title, 0, "application_enrichment", pattern), True)
        return (MessageMatch(message, "", 0, "application_enrichment", "No Match"), False)
