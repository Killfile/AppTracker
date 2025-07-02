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

from keyword_classifier import KeywordClassifier, KeywordClassifications
import base64
from functools import lru_cache
from apptracker_database.user_dao import UserDAO
from apptracker_database.database import SessionLocal
from apptracker_shared.gmail.gmail_gateway import GmailGateway 

CONSUMER_TOPIC = 'gmail-messages'
KEYWORD_MATCH_TOPIC = 'gmail-keyword-match'
KEYWORD_MISS_TOPIC = 'gmail-keyword-miss'
DOMAIN_MAPPING_TOPIC = "user-domain-mapping"
DEAD_LETTER_QUEUE = "keyword_DLQ"

@retry(NoBrokersAvailable, max_retries=10, initial_delay=5, exponential=False, jitter=0)
def create_compact_topic(topic_name, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
    """
    Creates a compacted Kafka topic if it does not already exist.
    
    Parameters:
        topic_name (str): The name of the topic to create.
        bootstrap_servers (str): The Kafka bootstrap servers.
    """

    admin = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
    existing_topics = admin.list_topics()

    try:
        topic_config = {
            'cleanup.policy': 'compact',
            "segment.ms": "604800000", # 7 days
            "min.cleanable.dirty.ratio": "0.01",
            "delete.retention.ms": "86400000", # 1 day
            }
        topic = NewTopic(name=topic_name, num_partitions=3, replication_factor=1, topic_configs=topic_config)
        admin.create_topics([topic])
        print(f"Created compacted topic: {topic_name}")
        return topic
    except TopicAlreadyExistsError:
        print(f"Topic {topic_name} already exists")

def create_dlq(topic_name, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
    admin = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
    existing_topics = admin.list_topics()

    try:
        topic_config = {
            'cleanup.policy': 'delete',
            "retention.ms": "3600000", # 1 hour
            "segment.ms": "60000" # 1 minute
            }
        topic = NewTopic(name=topic_name, num_partitions=3, replication_factor=1, topic_configs=topic_config)
        admin.create_topics([topic])
        print(f"Created compacted topic: {topic_name}")
        return topic
    except TopicAlreadyExistsError:
        print(f"Topic {topic_name} already exists")

create_compact_topic(DOMAIN_MAPPING_TOPIC)
create_dlq(DEAD_LETTER_QUEUE)

domain_mapping_producer = kafka_factory.initialize_kafka_producer_with_existing_topic(DOMAIN_MAPPING_TOPIC)
keyword_match_producer = kafka_factory.initialize_kafka_producer(KEYWORD_MATCH_TOPIC)
keyword_miss_producer = kafka_factory.initialize_kafka_producer(KEYWORD_MISS_TOPIC)
dlq_producer = kafka_factory.initialize_kafka_producer_with_existing_topic(DEAD_LETTER_QUEUE)

consumer = kafka_factory.initialize_kafka_consumer(CONSUMER_TOPIC, name="keyword-classifier-worker")

@lru_cache(maxsize=128)
def get_gateway_by_user_id(user_id):
    with SessionLocal() as db:
        userDAO = UserDAO(db)
        user = userDAO.get_user_by_id(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found.")
    gateway = GmailGateway(access_token=user.google_access_token, refresh_token=user.google_refresh_token, user_id=user.google_id)
    return gateway

def main():
    print('EmailAnalysisWorker started. Waiting for messages...')
    classifier = KeywordClassifier()
    for message in consumer:
        inner = message.value


        adapter = GmailMessageAdapter(inner["message"])

        sender = adapter.from_address
        subject = adapter.subject
        body = adapter.body
        
        user_id = inner["user_id"]
        gateway = get_gateway_by_user_id(user_id)

        classification = classifier.is_application_related(subject, body, sender)

        if classification == KeywordClassifications.HIT:
            label_id = gateway.create_or_get_label(label_name="AppTracker: Application Related")
            gateway.apply_label_to_message(message_id=adapter.gmail_message_id, label_id=label_id)
            keyword_match_producer.send(inner)
            print(f'🔑✅: {adapter.gmail_message_id}; current time is {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}', flush=True)
            
            domain = adapter.domain
            if domain:
                key = f"{user_id}:{domain}"
                value = {
                    "user_id": user_id,
                    "domain": domain,
                    "gmail_message_id": adapter.gmail_message_id,
                    "timestamp": time.time()
                }
                domain_mapping_producer.send(key=key, value=value)
        elif classification == KeywordClassifications.EXCLUDE:
            dlq_producer.send(inner)
            print(f'🔑☠️: {adapter.gmail_message_id}; current time is {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}', flush=True)
        elif classification == KeywordClassifications.MISS:
            keyword_miss_producer.send(inner)
            print(f'🔑❌: {adapter.gmail_message_id}; current time is {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}', flush=True)
        else:
            raise ValueError(f"Encountered a keyword classification of {classification} which should not be possible.")

        

if __name__ == '__main__':
    main()
