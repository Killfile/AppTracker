from enum import Enum
import re
import yaml
from pathlib import Path

from RegExCompiler.regex_compiler import RegexCompiler

class KeywordClassifications(Enum):
    HIT = 1,
    MISS = 2,
    EXCLUDE = 3
    

class KeywordClassifier:
    def __init__(self, config_path: str = "application_keywords.yml"):
        self.regex_compiler = RegexCompiler(config_path)
        
    def is_blacklisted(self, subject: str, body: str, sender: str) -> bool:
        subject_blacklist = self.regex_compiler.get_patterns().get("exclude_if_subject_contains") or {}
        email_blacklist = self.regex_compiler.get_patterns().get("email_blacklist") or {}
        for pattern in subject_blacklist.values():
            if re.search(pattern, subject):
                return True
        for pattern in email_blacklist.values():
            if re.search(pattern, sender):
                return True
        return False

    def is_application_related(self, subject: str, body: str, sender: str) -> KeywordClassifications:

        # Process exclusions first; otherwise fast-returns might be invalid
        if self.is_blacklisted(subject=subject, body=body, sender=sender):
            return KeywordClassifications.EXCLUDE

        subject_patterns = self.regex_compiler.get_patterns().get("subject_keywords") or {}
        body_patterns = self.regex_compiler.get_patterns().get("body_phrases") or {}
        sender_patterns = self.regex_compiler.get_patterns().get("sender_patterns") or {}

        #print(f"Checking against patterns: subject={subject_patterns}, body={body_patterns}, sender={sender_patterns}", flush=True)

        if any(re.search(pattern, subject) for pattern in subject_patterns.values()):
            return KeywordClassifications.HIT
        if any(re.search(pattern, body) for pattern in body_patterns.values()):
            return KeywordClassifications.HIT
        if any(re.search(pattern, sender) for pattern in sender_patterns.values()):
            return KeywordClassifications.HIT
        
        return KeywordClassifications.MISS