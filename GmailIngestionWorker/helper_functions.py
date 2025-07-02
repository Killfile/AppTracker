import json
from kafka_constants import KAFKA_BOOTSTRAP_SERVERS
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError, NoBrokersAvailable
from kafka import KafkaConsumer, KafkaProducer
from retry_decorater import retry
import datetime

def topic_exists(topic_name, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
    """
    Checks if a Kafka topic exists.

    Parameters:
        topic_name (str): The name of the topic to check.
        bootstrap_servers (str): The Kafka bootstrap servers.

    Returns:
        bool: True if the topic exists, False otherwise.
    """
    admin = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
    existing_topics = admin.list_topics()
    return topic_name in existing_topics

def ensure_topic(topic_name, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
    if not topic_exists(topic_name, bootstrap_servers):
        try:
            admin = KafkaAdminClient(bootstrap_servers=bootstrap_servers)
            topic = NewTopic(name=topic_name, num_partitions=1, replication_factor=1)
            admin.create_topics([topic])
            print(f"Created topic: {topic_name}")
        except TopicAlreadyExistsError:
            print(f"Topic {topic_name} already exists (race condition)")
    else:
        print(f"Topic {topic_name} already exists")

def get_header_value(headers, key_name):
    """
    Extracts the value of a specific header by name from a list of headers.

    Parameters:
        headers (list): List of dicts with 'name' and 'value' keys.
        key_name (str): The name of the header to extract.

    Returns:
        str or None: The value of the header, or None if not found.
    """
    for header in headers:
        if header.get("name") == key_name:
            return header.get("value")
    return None

@retry(NoBrokersAvailable, max_retries=10, initial_delay=5, exponential=False, jitter=0)
def initialize_kafka_consumer(topic:str, name:str, group:str='email-analysis-group', enable_auto_commit=True, **kwargs) -> KafkaConsumer:
    ensure_topic(topic) 
    consumer = KafkaConsumer(
        topic,
        client_id=name,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        key_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest',
        group_id=group,
        enable_auto_commit=enable_auto_commit,
        fetch_max_wait_ms=5000,
        api_version=(3,7,0), # Run `docker exec -it kafka kafka-topics.sh --version` to get the version
        **kwargs
    )
    return consumer


@retry(NoBrokersAvailable, max_retries=10, initial_delay=5, exponential=False, jitter=0)
def initialize_kafka_consumer_with_existing_topic(topic:str, name:str, group:str='email-analysis-group', enable_auto_commit=True, **kwargs):
    if not topic_exists(topic, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
        raise ValueError(f"Topic {topic} does not exist. Please create it first.")
    consumer = KafkaConsumer(
        topic,
        client_id=name,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        key_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='earliest',
        group_id=group,
        enable_auto_commit=enable_auto_commit,
        fetch_max_wait_ms=5000,
        api_version=(3,7,0), # Run `docker exec -it kafka kafka-topics.sh --version` to get the version
        **kwargs
    )
    return consumer

class TimestampingKafkaProducer:
    def __init__(self, topic, **producer_kwargs):
        self.topic = topic
        self.producer = KafkaProducer(
            **producer_kwargs
        )

    def send(self, value: dict, key = None):
        # Enriches the value with a timestamp if not present BEFORE any serialization
        enriched = {
            **value,
            "ingested_at": value.get("ingested_at") or datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        return self.producer.send(self.topic, key=key, value=enriched)

    def flush(self):
        self.producer.flush()

    def close(self):
        self.producer.close()


@retry(NoBrokersAvailable, max_retries=10, initial_delay=5, exponential=False, jitter=0)
def initialize_kafka_producer(topic:str):
    ensure_topic(topic)
    producer = TimestampingKafkaProducer(
        topic=topic,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    return producer

@retry(NoBrokersAvailable, max_retries=10, initial_delay=5, exponential=False, jitter=0)
def initialize_kafka_producer_with_existing_topic(topic:str):
    if not topic_exists(topic, bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS):
        raise ValueError(f"Topic {topic} does not exist. Please create it first.")
    producer = TimestampingKafkaProducer(
        topic=topic,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=lambda v: json.dumps(v).encode('utf-8')
    )
    return producer
