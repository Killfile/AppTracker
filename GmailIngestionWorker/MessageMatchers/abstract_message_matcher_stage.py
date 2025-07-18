import yaml
from sqlalchemy.orm import Session
from apptracker_database.models import Message

from abc import ABC, abstractmethod
from pathlib import Path


class AbstractMessageMatcherStage(ABC):
    @abstractmethod
    def process(self, message: Message, db: Session) -> tuple[Message, bool]:
        raise NotImplementedError

    def _load_yml_config(self, path:str)->dict:
        if not Path(path).exists():
            raise FileNotFoundError(f"Configuration file {path} does not exist.")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)