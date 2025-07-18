import re
import yaml
from typing import Optional, Tuple
from MessageMatchers.abstract_message_matcher_stage import AbstractMessageMatcherStage
from MessageMatchers.message_match import MessageMatch
from apptracker_database.models import Message

class ActionMatcher_PatternBody(AbstractMessageMatcherStage):
    def __init__(self, pattern_file: str = "action_pattern_matching.yml"):
        with open(pattern_file, 'r', encoding='utf-8') as f:
            self.patterns = yaml.safe_load(f)

    def extract_action(self, text: str) -> Optional[Tuple[str, str]]:
        for action_type, patterns in self.patterns.items():
            normalized_type = action_type.replace('_patterns', '').upper()
            for pattern in patterns:
                if re.search(pattern, text):
                    return normalized_type, pattern
        return None

    def process(self, message: Message, db=None) -> Tuple[MessageMatch, bool]:
        result = self.extract_action(message.message_body)
        if result:
            action_type, pattern = result
            return (MessageMatch(message, action_type, 0, "action_enrichment", pattern), True)
        return (MessageMatch(message, "", 0, "action_enrichment", "No Match"), False)
