from abc import ABC, abstractmethod
from collections import Counter
from pathlib import Path
import re
import sys
from typing import List
import uuid
from kafka import KafkaConsumer, KafkaProducer
import json
import os
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
from kafka import KafkaConsumer
import time
from kafka.errors import NoBrokersAvailable
from retry_decorater import retry
from gmail_message_adapter import GmailMessageAdapter
from kafka_constants import KAFKA_BOOTSTRAP_SERVERS
import helper_functions as kafka_factory

from keyword_classifier import KeywordClassifier
import base64
from functools import lru_cache
from apptracker_database.models import Message, EmailAddress
from apptracker_database.email_address_dao import EmailAddressDAO
from apptracker_database.message_dao import MessageDAO
from apptracker_database.company_dao import CompanyDAO
from apptracker_database.models import Company
from apptracker_database.database import SessionLocal
from apptracker_shared.gmail.gmail_gateway import GmailGateway 
from tuple_key_mapper import TupleKeyMapper 
from apptracker_database.dao_factory import DataOrchestrationFactory
import threading
import time
import yaml
from sqlalchemy.orm import Session

class CompanyNamePatternMatcher:
    def __init__(self, config_path: str = "company_name_patterns.yml"):
        config = self._load_config(config_path)
        self._sender_address_patterns = config["sender_address_patterns"]
        self._subject_patterns = config["subject_patterns"]
        self._body_patterns = config["body_patterns"]

    def _load_config(self, path: str) -> dict:
        if not Path(path).exists():
            raise FileNotFoundError(f"Configuration file {path} does not exist.")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
        
    def get_matches_from_message(self, message: Message) -> List[str]:
        pass
        #TODO 

class AbstractMessageEnrichmentStage(ABC):
    @abstractmethod
    def process(self, message: Message, db: Session) -> tuple[Message, bool]:
        raise NotImplementedError
    
    def _load_yml_config(self, path:str)->dict:
        if not Path(path).exists():
            raise FileNotFoundError(f"Configuration file {path} does not exist.")
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    
class KnownEmailEnrichment(AbstractMessageEnrichmentStage):
    def __init__(self, email_patterns="company_pattern_matching.yml"):
        config = self._load_yml_config(email_patterns)
        self._blacklisted_email_patterns = config["email_blacklist"]
        
    def _is_blacklisted(self, email_address)->bool:
        for value in self._blacklisted_email_patterns:
            if re.search(value, email_address):
                return True
        return False
        
    def process(self, message: Message, db: Session) -> tuple[Message, bool]:
        # Checks to see if we're done already; should never happen
        if message.company_id: 
            return (message, True)
        if self._is_blacklisted(message.email_address.email):
            return (message, False)
        if message.email_address.company_id:
            message.company_id = message.email_address.company_id
            return (message, True)
        return (message, False)
    
class PatternEmailEnrichment(AbstractMessageEnrichmentStage):
    def __init__(self, email_patterns="company_pattern_matching.yml"):
        config = self._load_yml_config(email_patterns)
        self._email_patterns = config["email_patterns"]

    def process(self, message: Message, db: Session) -> tuple[Message, bool]:
        company_matches = []
        for pattern in self._email_patterns:
            match = re.match(pattern, message.email_address.email)
            if match and match.group(1):
                company_matches.append(match.group(1))

        if not company_matches:
            return (message, False)
        
        counter = Counter(company_matches)
        most_common_company, count = counter.most_common(1)[0]

        company_dao = CompanyDAO(db)
        company = company_dao.get_company_by_name(most_common_company)
        if not company:
            company = company_dao.create_company(most_common_company)
        
        if company:
            message.company_id = company.id
            return (message, True)
        
        return (message, True)

                


        
        
        

class CompanyEnrichmentModule:
    #def __init__(self):

    def _get_message_batch(self, db) -> List[Message]:
        dao = MessageDAO(db)
        batch = dao.get_messages_with_email_addresses(limit = 100, filter_clause = Message.company_id.is_(None))
        return batch
    
    def _email_not_on_reuse_blacklist(self, email:str):
        return True #todo -- load this from some file or maybe the database.
    
    def _get_company_id_via_email_link(self, message: Message):
        company_id = None
        if self._email_not_on_reuse_blacklist(message.email_address.email):
            company_id = message.email_address.company_id
        return company_id
    
    def _get_company_name_by_pattern_match(self, message)

    def enrich(self):
        with SessionLocal() as db:
            batch = self._get_message_batch(db)
            for message in batch:
                message.company_id = self._get_company_id_via_email_link(message)

                if message.company_id:
                    continue

                company_name = None
                company_name = self._get_company_name_by_pattern_match(message)
                if company_name:
                    company = self._get_company_from_company_name(company_name, db)


            

        
            
        
                
    

    

    
