from kafka import KafkaConsumer
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError
import time
from kafka.errors import NoBrokersAvailable
from gmail_gateway_factory import GmailGatewayFactory
from retry_decorater import retry
from gmail_message_adapter import GmailMessageAdapter
from kafka_constants import KAFKA_BOOTSTRAP_SERVERS
import helper_functions as kafka_factory

from keyword_classifier import KeywordClassifier, KeywordClassifications

CONSUMER_TOPIC = 'gmail-messages'
KEYWORD_MATCH_TOPIC = 'gmail-keyword-match'
KEYWORD_MISS_TOPIC = 'gmail-keyword-miss'
DOMAIN_MAPPING_TOPIC = "user-domain-mapping"
DEAD_LETTER_QUEUE = "keyword_DLQ"
LABEL_TOPIC = "gmail-label-requests"

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
gmail_label_producer = kafka_factory.initialize_kafka_producer(LABEL_TOPIC)

consumer = kafka_factory.initialize_kafka_consumer(CONSUMER_TOPIC, name="keyword-classifier-worker")

class KeywordClassifierWorker:
    def __init__(self, consumer: KafkaConsumer, domain_mapping_producer: kafka_factory.TimestampingKafkaProducer, keyword_match_producer: kafka_factory.TimestampingKafkaProducer, keyword_miss_producer: kafka_factory.TimestampingKafkaProducer, dlq_producer: kafka_factory.TimestampingKafkaProducer, gmail_label_producer: kafka_factory.TimestampingKafkaProducer):
        self.classifier = KeywordClassifier()
        self.consumer = consumer
        self.domain_mapping_producer = domain_mapping_producer
        self.keyword_match_producer = keyword_match_producer
        self.keyword_miss_producer = keyword_miss_producer
        self.gmail_label_producer = gmail_label_producer
        self.dlq_producer = dlq_producer
    
    def label_message(self, gateway, user_id, label_name, message_id):
        label_id = gateway.create_or_get_label(label_name=label_name)
        message = {
            "user_id": user_id,
            "label_id": label_id,
            "message_id": message_id}
        self.gmail_label_producer.send(message)

    def run(self):
        for message in self.consumer:
            inner = message.value

            adapter = GmailMessageAdapter(inner["message"])

            sender = adapter.from_address
            subject = adapter.subject
            body = adapter.body
            
            user_id = inner["user_id"]
            gateway = GmailGatewayFactory.build(user_id)

            classification = self.classifier.is_application_related(subject, body, sender)

            if classification == KeywordClassifications.HIT:
                self.label_message(gateway, user_id, "AppTracker: Application Related", adapter.gmail_message_id)
                self.keyword_match_producer.send(inner)
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
                    self.domain_mapping_producer.send(key=key, value=value)
            elif classification == KeywordClassifications.EXCLUDE:
                self.dlq_producer.send(inner)
                print(f'🔑☠️: {adapter.gmail_message_id}; current time is {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}', flush=True)
            elif classification == KeywordClassifications.MISS:
                self.keyword_miss_producer.send(inner)
                print(f'🔑❌: {adapter.gmail_message_id}; current time is {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}', flush=True)
            else:
                raise ValueError(f"Encountered a keyword classification of {classification} which should not be possible.")

def label_message(gateway, user_id, label_name, message_id):
    label_id = gateway.create_or_get_label(label_name=label_name)
    message = {
        "user_id": user_id,
        "label_id": label_id,
        "message_id": message_id}
    gmail_label_producer.send(message)
    

def main():
    print('EmailAnalysisWorker started. Waiting for messages...')
    worker = KeywordClassifierWorker(
        consumer=consumer,
        domain_mapping_producer=domain_mapping_producer,
        keyword_match_producer=keyword_match_producer,
        keyword_miss_producer=keyword_miss_producer,
        dlq_producer=dlq_producer,
        gmail_label_producer=gmail_label_producer
    )

    worker.run()
    print('EmailAnalysisWorker finished processing messages.')

if __name__ == '__main__':
    main()
