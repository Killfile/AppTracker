from kafka import KafkaConsumer
import time
from gmail_gateway_factory import GmailGatewayFactory
from gmail_message_adapter import GmailMessageAdapter
from kafka_constants import KAFKA_BOOTSTRAP_SERVERS
import helper_functions as kafka_factory
from RegExCompiler.regex_compiler import RegexCompiler
import re

CONSUMER_TOPIC = 'gmail-messages'
HR_PLATFORMS_TOPIC_SEED = 'hr-platforms'
GENERAL_INGESTION_TOPIC = 'general-ingestion'
LABEL_TOPIC = 'gmail-label-requests'

class HRPlatformClassifierWorker:
    def __init__(self, consumer: KafkaConsumer, platforms_producers: dict, general_ingestion_producer, gmail_label_producer):
        self.consumer = consumer
        self.platforms_producers = platforms_producers
        self.general_ingestion_producer = general_ingestion_producer
        self.gmail_label_producer = gmail_label_producer
        self.patterns = self._load_patterns()

    def _load_patterns(self):
        compiler = RegexCompiler('hr_platforms.yml')
        patterns = compiler.get_patterns()
        return patterns.get('sender_patterns', [])

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
            user_id = inner["user_id"]
            gateway = GmailGatewayFactory.build(user_id)
            matched = False
            for key, pattern in self.patterns.items():
                if pattern and sender and re.search(pattern, sender):
                    self.label_message(gateway, user_id, f"AppTracker/HR Platform/{key}", adapter.gmail_message_id)
                    self.platforms_producers[key].send(inner)
                    print(f'🏢✅: {adapter.gmail_message_id} matched HR platform; {sender}; {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}', flush=True)
                    matched = True
                    break
            if not matched:
                self.general_ingestion_producer.send(inner)
                print(f'🏢❌: {adapter.gmail_message_id} sent to general ingestion; {sender}; {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())}', flush=True)

def main():
    print('HRPlatformClassifierWorker started. Waiting for messages...')

    # Initialize Kafka producers and consumer
    hr_platforms_producer = kafka_factory.initialize_kafka_producer(HR_PLATFORMS_TOPIC_SEED)
    general_ingestion_producer = kafka_factory.initialize_kafka_producer(GENERAL_INGESTION_TOPIC)
    gmail_label_producer = kafka_factory.initialize_kafka_producer(LABEL_TOPIC)
    consumer = kafka_factory.initialize_kafka_consumer(CONSUMER_TOPIC, name="hr-platform-worker")

    platforms_producers = {}
    regex_compiler = RegexCompiler('hr_platforms.yml')
    patterns = regex_compiler.get_patterns().get('sender_patterns', {})
    for key, value in patterns.items():
        platforms_producers[key] = kafka_factory.initialize_kafka_producer(f"{HR_PLATFORMS_TOPIC_SEED}__{key}")

    worker = HRPlatformClassifierWorker(
        consumer=consumer,
        platforms_producers=platforms_producers,
        general_ingestion_producer=general_ingestion_producer,
        gmail_label_producer=gmail_label_producer
    )
    worker.run()
    print('HRPlatformClassifierWorker finished processing messages.')

if __name__ == '__main__':
    main()
