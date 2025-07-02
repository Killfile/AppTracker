import datetime
from typing import List
from kafka import KafkaProducer
import json
import time
import os
from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError, NoBrokersAvailable
from kafka import KafkaConsumer
from apptracker_database.user_dao import UserDAO
from apptracker_database.models import User
from apptracker_database.database import SessionLocal
from email.utils import parsedate_to_datetime
from gmail_message_adapter import GmailMessageAdapter
from retry_decorater import retry
from helper_functions import ensure_topic, get_header_value
from kafka_constants import KAFKA_BOOTSTRAP_SERVERS
from helper_functions import initialize_kafka_consumer, initialize_kafka_producer

from gmail_message_history_fetcher import GmailMessageHistoryFetcher

TOPIC = 'gmail-messages'

producer = initialize_kafka_producer(TOPIC)

def main():
    with SessionLocal() as db:
        userDAO = UserDAO(db)
        all_users = userDAO.get_all_users()
        all_user_history_fetchers:List[GmailMessageHistoryFetcher] = []
        for user in all_users:
            if not user.google_access_token or not user.google_id:
                print(f"Skipping user {user.username} due to missing Google access token or ID.")
                continue
            try:
                fetcher = GmailMessageHistoryFetcher(user)
                all_user_history_fetchers.append(fetcher)
            except ValueError as e:
                print(f"Error initializing fetcher for user {user.username}: {e}")
    

    
    while True:
        for fetcher in all_user_history_fetchers:
            emails = fetcher.fetch_history_page()
            
            if not emails:
                print("No more messages to process or crawl complete.", flush=True)
                continue
            
            for email in emails:
                adapter = GmailMessageAdapter(email)
                date_value = get_header_value(email["payload"]["headers"], "Date")
                message_datetime = parsedate_to_datetime(date_value) if date_value else None
                if message_datetime is None:
                    print(f"Skipping message {email['id']} due to missing or invalid date header.")
                    continue    
                if message_datetime < datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=365):
                    fetcher.page_token = GmailMessageHistoryFetcher.CRAWL_COMPLETE
                    print(f"Halting fetcher for user {fetcher._user.username} due to message date {message_datetime} being older than 1 year.")
                    continue
                
                print(f"📨 recieved on: {date_value}")
                item = {
                    "message": email,
                    "user_id": fetcher._user.id,
                    "date_recieved": message_datetime.isoformat()
                }
                producer.send(item)
                producer.flush()
                print(".", end="", flush=True)

        time.sleep(5)

if __name__ == '__main__':
    main()
