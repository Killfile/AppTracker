import json
import time
from gmail_gateway_factory import GmailGatewayFactory
from helper_functions import initialize_kafka_consumer, initialize_kafka_producer


import json
import time
import heapq
from datetime import datetime
from dataclasses import dataclass, field
from typing import List

MAX_BUFFER_DELAY = 120  # configurable delay window

@dataclass(order=True)
class BufferedLabelRequest:
    user_id: str = field(compare=False)
    label_id: str = field(compare=False)
    message_id: str = field(compare=False)
    queue_position: int = field(compare=True)
    enqueued_at: float = field(default_factory=time.monotonic, compare=False)

class GmailLabelingWorker:
    def __init__(self, consumer, max_interval=60, max_buffer_size=100):
        self.consumer = consumer
        self.max_interval = max_interval
        self.max_buffer_size = max_buffer_size

        self.buffer: dict[str,List[BufferedLabelRequest]] = {}

    def add_to_buffer(self, user_id: str, label_id: str, message_id: str):
        now = time.time()

        if user_id not in self.buffer.keys():
            self.buffer[user_id] = []

        heapq.heappush(self.buffer[user_id], BufferedLabelRequest(
            user_id=user_id,
            label_id=label_id,
            message_id=message_id,
            queue_position=len(self.buffer[user_id]),
            enqueued_at=now
        ))
        print(f"📥 Added to buffer: {message_id} for user {user_id}", flush=True)

    def _flush_user_buffer_if_ready(self, user_id: str):
        # if the enqueued_at is older than now + MAX_BUFFER_DELAY,or the buffer is too large, use batch_label_messages_with_retry to bulk-apply each distinct label
        now = time.time()
        if user_id not in self.buffer or not self.buffer[user_id]:
            return
        buffered_requests = self.buffer[user_id]
        if not buffered_requests:
            return
        if (now - buffered_requests[0].enqueued_at > MAX_BUFFER_DELAY) or len(buffered_requests) >= self.max_buffer_size:
            service = GmailGatewayFactory.build(user_id)
            
            # Group message_ids by label_id
            label_groups = {}
            for req in buffered_requests:
                label_groups.setdefault(req.label_id, []).append(req.message_id)
            
            for label_id, message_ids in label_groups.items():
                print(f"💪 Batch labeling {len(message_ids)} messages for user {service.user_id} with label {label_id}")
                service.batch_label_messages_with_retry(
                    user_id=service.user_id,
                    label_id=label_id,
                    message_ids=message_ids
                )
            self.buffer[user_id] = []  # clear buffer after processing


    def check_buffers(self):
        for user_id in list(self.buffer.keys()):
            self._flush_user_buffer_if_ready(user_id)
            if not self.buffer[user_id]:
                del self.buffer[user_id]
                print(f"✅ Finished processing buffer for user {user_id}")

    def run(self):
        print("🚀🚀 Gmail Labeling Worker started.", flush=True)
        try:
            while True:
                flushed = False
                try:
                    msg = next(self.consumer)
                    value = msg.value
                    self.add_to_buffer(user_id=value["user_id"], label_id=value["label_id"], message_id=value["message_id"])
                    flushed = True
                except StopIteration:
                    pass  # consumer timed out, no message this cycle
                except Exception as e:
                    print(f"⚠️ Consumer error: {e}", flush=True)

                self.check_buffers()
                if not flushed and not self.buffer:
                    time.sleep(0.5)  # back off when idle
                else:
                    time.sleep(0.1)
        except KeyboardInterrupt:
            print("🚦 Gracefully shutting down worker.", flush=True)

# --- Usage ---
if __name__ == "__main__":

    CONSUMER_TOPIC = 'gmail-label-requests'
   

    gmail_label_consumer = initialize_kafka_consumer(CONSUMER_TOPIC, name="gmail-labeling-consumer")


    worker = GmailLabelingWorker(
        consumer=gmail_label_consumer,
        max_interval=MAX_BUFFER_DELAY,
        max_buffer_size=25
    )
    worker.run()
