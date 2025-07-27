import re
import yaml
from typing import Optional, Tuple
from MessageMatchers.abstract_message_matcher_stage import AbstractMessageMatcherStage
from MessageMatchers.message_match import MessageMatch
from RegExCompiler.regex_compiler import RegexCompiler
from apptracker_database.models import Message

class ApplicationMatcher_PatternBody(AbstractMessageMatcherStage):
    def __init__(self, pattern_file: str = "application_pattern_matching.yml"):
        self.regex_compiler = RegexCompiler(pattern_file)
        self.patterns = self.regex_compiler.get_patterns().get("application_patterns", [])

    def extract_application(self, text: str) -> Optional[Tuple[str, str]]:
        for pattern in self.patterns:

            match = re.search(pattern, text)
            if match:
                print(f"📌🔗Found match: {match.group(1).strip()} with pattern: {pattern}", flush=True)
                return match.group(1).strip(), pattern
        return None

    def process(self, message: Message, db=None) -> Tuple[MessageMatch, bool]:
        result = self.extract_application(message.message_body)
        if result:
            app_title, pattern = result
            return (MessageMatch(message, app_title, 0, "application_enrichment", pattern), True)
        return (MessageMatch(message, "", 0, "application_enrichment", "No Match"), False)
