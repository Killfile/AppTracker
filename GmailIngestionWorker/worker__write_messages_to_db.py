import sys
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
from apptracker_database.database import SessionLocal
from apptracker_shared.gmail.gmail_gateway import GmailGateway 
from tuple_key_mapper import TupleKeyMapper 
from apptracker_database.dao_factory import DataOrchestrationFactory
import threading
import time

class MessageDBWorker:
    def __init__(self, consumer: KafkaConsumer) -> None:
        self._consumer = consumer
    
    def run(self):
        for message in self._consumer:
            value = message.value
            email = GmailMessageAdapter(value["message"])
                
           
            with SessionLocal() as db:
                factory = DataOrchestrationFactory(db)
                orchestrator = factory.build([Message, EmailAddress])
                
                db_email = EmailAddress(
                    email = email.from_address)

                db_message = Message(
                    subject = email.subject,
                    date_received = email.datestamp,
                    message_body = email.body,
                    gmail_message_id = email.gmail_message_id,
                    user_id = value["user_id"])
                
                orchestrator.add(message=db_message, email_address=db_email)
            print(f"✉️💾 Message saved to database.")
        

    
if __name__ == "__main__":
    topic = sys.argv[1]

    consumer = kafka_factory.initialize_kafka_consumer(topic, "persistance worker for "+topic)

    worker = MessageDBWorker(consumer=consumer)
    worker.run()