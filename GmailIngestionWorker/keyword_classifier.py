from enum import Enum
import yaml
from pathlib import Path

class KeywordClassifications(Enum):
    HIT = 1,
    MISS = 2,
    EXCLUDE = 3
    

class KeywordClassifier:
    def __init__(self, config_path: str = "application_keywords.yml"):
        self.config = self._load_config(config_path)

    def _load_config(self, path: str) -> dict:
        if not Path(path).exists():
            raise FileNotFoundError(f"Configuration file {path} does not exist.")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
        
    def is_blacklisted(self, subject: str, body: str, sender: str) -> bool:
        subject_lc = subject.lower()
        body_lc = body.lower()

        if any(excl in subject_lc for excl in self.config["application_detection"]["exclude_if_subject_contains"]):
            return True
        
        return False

    def is_application_related(self, subject: str, body: str, sender: str) -> KeywordClassifications:
        subject_lc = subject.lower()
        body_lc = body.lower()

        # Process exclusions first; otherwise fast-returns might be invalid
        if self.is_blacklisted(subject=subject, body=body, sender=sender):
            return KeywordClassifications.EXCLUDE
        
        if any(kw in subject_lc for kw in self.config["application_detection"]["subject_keywords"]):
            return KeywordClassifications.HIT
        if any(phrase in body_lc for phrase in self.config["application_detection"]["body_phrases"]):
            return KeywordClassifications.HIT
        if any(pat.strip('*') in sender for pat in self.config["application_detection"]["sender_patterns"]):
            return KeywordClassifications.HIT
        
        return KeywordClassifications.MISS