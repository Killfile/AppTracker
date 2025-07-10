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
from apptracker_database.user_dao import UserDAO
from apptracker_database.database import SessionLocal
from apptracker_shared.gmail.gmail_gateway import GmailGateway 
from tuple_key_mapper import TupleKeyMapper 
import threading
import time


DOMAIN_MAPPING_TOPIC = "user-domain-mapping"
KEYWORD_MISS_DELAYED_TOPIC = 'gmail-keyword-miss-delayed'
DOMAIN_INTEREST_TOPIC = "gmail-domain-interest"

class DomainInterestCache:
    def __init__(self, topic, refresh_interval=60):
        print(f"🚀 init domain interest cache.",flush=True)
        self.topic = topic
        self.refresh_interval = refresh_interval
        self._cache = set()
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._refresh_loop, daemon=True)

    def start(self):
        print("🚦Calling start on domain interest cache.",flush=True)
        self._rebuild_cache()
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        self._thread.join()

    def contains(self, key):
        return key in self._cache

    def _refresh_loop(self):
        while not self._stop_event.is_set():
            self._rebuild_cache()
            time.sleep(self.refresh_interval)

    def _rebuild_cache(self):
        print("💰♻️ Refreshing domain interest cache...",flush=True)
        try:
            consumer = kafka_factory.initialize_kafka_consumer_with_existing_topic(self.topic, 
                name="domain-interest-cache",
                enable_auto_commit=False,
                group=f"cache-{uuid.uuid4()}",
                consumer_timeout_ms=5000
            )
        except ValueError as e:
            print(f"Value Error: {e}")
            return

        consumer.poll(timeout_ms=0)

        for partition in consumer.assignment():
            consumer.seek_to_beginning(partition)

        keys = set()
        for msg in consumer:
            keys.add(msg.key)
        print(f"💰#️⃣ - Cache count now {len(keys)}")
        consumer.close()
        if len(keys) > 0:
            self._cache = keys


class DomainInterestWorker:
    def __init__ (self, cache: DomainInterestCache, keyword_miss_consumer: KafkaConsumer, domain_interest_producer: kafka_factory.TimestampingKafkaProducer):
        self._keyword_miss_consumer = keyword_miss_consumer
        self._domain_interest_producer = domain_interest_producer
        self._cache = cache
        self._gateway = {}

    def _get_gateway(self, user_id: str):
        gateway = self._gateway.get(user_id)
        if not gateway:
            with SessionLocal() as db:
                userDAO = UserDAO(db)
                user = userDAO.get_user_by_id(user_id)
            if not user:
                raise ValueError(f"User with ID {user_id} not found.")
            gateway = GmailGateway(access_token=user.google_access_token, refresh_token=user.google_refresh_token, user_id=user.google_id)
            self._gateway[user_id] = gateway
        
        return gateway

    def run(self):
        for msg in self._keyword_miss_consumer:
            value = msg.value
            email = GmailMessageAdapter(value["message"])
            user_id = value["user_id"]
            domain = email.domain

            key = TupleKeyMapper.map_tuple_to_key((user_id, domain))

            if not isinstance(value, dict):
                print(f"❌ Invalid value type: {type(value)}. Expected dict.",flush=True)
                continue

            if self._cache.contains(key):
                print(f"🔑 Message {email.gmail_message_id} from domain {email.from_address} flagged for followup for user: {user_id}",flush=True)
                gateway = self._get_gateway(user_id)
                label_id = gateway.create_or_get_label(label_name="AppTracker: Domain Flagged")
                gateway.apply_label_to_message(message_id=email.gmail_message_id, label_id=label_id)
                self._domain_interest_producer.send(value)
           

if __name__ == "__main__":
    DOMAIN_INTEREST_TOPIC = "gmail-domain-interest"
    
    cache = DomainInterestCache(DOMAIN_MAPPING_TOPIC)
    cache.start()

    miss_consumer = kafka_factory.initialize_kafka_consumer(KEYWORD_MISS_DELAYED_TOPIC, name="domain-interest-miss-consumer")
    interest_producer = kafka_factory.initialize_kafka_producer(DOMAIN_INTEREST_TOPIC)

    worker = DomainInterestWorker(cache=cache, keyword_miss_consumer=miss_consumer, domain_interest_producer=interest_producer)
    worker.run()
        