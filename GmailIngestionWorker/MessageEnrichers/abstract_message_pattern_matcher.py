from MessageMatchers.abstract_message_matcher_stage import AbstractMessageMatcherStage
from MessageMatchers.message_match import MessageMatch
from apptracker_database.models import Message


from sqlalchemy.orm import Session


from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
import json


class AbstractMessagePatternMatcher(ABC):
    def __init__(self, db: Session, config_path: str, exhaust_path: str = None):
        self._db = db
        self._config_path = config_path
        self._exhaust_path = exhaust_path
        self._matchers: list[AbstractMessageMatcherStage] = []

    def add_matcher(self, matcher: AbstractMessageMatcherStage):
        self._matchers.append(matcher)

    def get_matches_from_message(self, message: Message) -> List[MessageMatch]:
        for matcher in self._matchers:
            matches, done = matcher.process(message, self._db)
            if done:
                return [matches]
        return []

    @abstractmethod
    def _process_matched_message(self, message: Message, matches: List[MessageMatch]) -> Tuple[bool, Optional[str]]:
        raise NotImplementedError("Subclasses should implement this method to process matched messages.")

    def process_message(self, message: Message) -> Tuple[bool, Optional[str]]:
        matches = self.get_matches_from_message(message)
        if not matches:
            return False, None
        
        message = matches[0].message
        if not message:
            return False, None
        
        # Matching exhaust belongs here
        if self._exhaust_path:
            with open(self._exhaust_path, "a", encoding="utf-8") as f:
                json.dump(matches[0].as_dict(), f, default=str)
                f.write("\n")

        return self._process_matched_message(message, matches)