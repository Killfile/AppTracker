import json
import time
from helper_functions import initialize_kafka_consumer, initialize_kafka_producer


import json
import time
import heapq
from datetime import datetime
from dataclasses import dataclass, field
from typing import List



DELAY_WINDOW_SECONDS = 120  # configurable delay window

@dataclass(order=True)
class BufferedMessage:
    release_at: float
    key: str = field(compare=False)
    value: dict = field(compare=False)

class TimeShifterWorker:
    def __init__(self, consumer, producer, producer_topic, delay_seconds=60):
        self.consumer = consumer
        self.producer = producer

        self._prodcer_topic = producer_topic
        self.delay_seconds = delay_seconds
        self.buffer: List[BufferedMessage] = []

    def add_to_buffer(self, key: str, value: dict):
        now = time.time()
        # Either use ingested timestamp or default to now
        msg_ts = value.get("ingested_at")
        base_time = (
            datetime.fromisoformat(msg_ts).timestamp()
            if msg_ts else now
        )
        release_at = base_time + self.delay_seconds
        heapq.heappush(self.buffer, BufferedMessage(release_at, key, value))

    def flush_ready(self):
        now = time.time()
        while self.buffer and self.buffer[0].release_at <= now:
            buffered = heapq.heappop(self.buffer)
            self.producer.send( 
                key=buffered.key,
                value=buffered.value
            )
            print(f"⌛⏩ for key={buffered.key} at {datetime.now()}")

    def run(self):
        print("Time Shifter Worker started.")
        for msg in self.consumer:
            key = msg.key
            value = msg.value
            self.add_to_buffer(key, value)
            self.flush_ready()
            time.sleep(0.1)  # quick nap to reduce CPU thrash

# --- Usage ---
if __name__ == "__main__":

    CONSUMER_TOPIC = 'gmail-keyword-miss'
    PRODUCER_TOPIC = 'gmail-keyword-miss-delayed'

    keyword_miss_consumer = initialize_kafka_consumer(CONSUMER_TOPIC, name="timeshift-worker")
    producer = initialize_kafka_producer(PRODUCER_TOPIC)

    worker = TimeShifterWorker(
        consumer=keyword_miss_consumer,
        producer=producer,
        producer_topic=PRODUCER_TOPIC,
        delay_seconds=DELAY_WINDOW_SECONDS
    )
    worker.run()
